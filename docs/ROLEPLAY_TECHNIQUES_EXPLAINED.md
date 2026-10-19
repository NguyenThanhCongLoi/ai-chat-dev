# Kỹ thuật đang dùng trong chat thường: thuật toán, tác dụng và giới hạn

Ngày 17/10/2026. Dựa trên code workspace, không suy ra thuật toán nội bộ của nhà cung cấp. Áp dụng cho **chat đơn lẫn nhóm**, trừ các mục ghi rõ chỉ dành cho nhóm. [Bộ prompt/lore 11 nhân vật](roleplay/CHARACTER_CMS_COPY.md).

## 1. Bốn lớp dữ liệu khác nhau

| Lớp | Lưu gì | Người nhập/cập nhật | Lợi ích |
|---|---|---|---|
| CharacterSpec/prompt | Identity, personality, speech, boundaries, goals, examples | Admin/người tạo nhân vật | Giữ cá tính riêng |
| Lorebook CMS | Kiến thức gốc dùng lại, target, keyword, phạm vi biết | Admin | Canon thống nhất giữa các bản dùng nhân vật |
| Lore/scene phòng | Tình huống và luật riêng location/time/objective | Owner phòng | Giữ bối cảnh của riêng user |
| Memory/episode | Trải nghiệm, sở thích, lời hứa và bản tóm tắt có nguồn | Heuristic/LLM theo consent; user ghim/sửa | Nhớ điều quan trọng qua lịch sử dài |

Lorebook không phải thuật toán huấn luyện lại model. Đây là **retrieval + ghép context khi chạy**. Cập nhật DB không thay weights của LLM. Không cần nhập lore chỉ để lặp toàn bộ prompt.

## 2. Pipeline thực sự

ChatView → auth/ownership/moderation → lưu user message → chọn speaker → engine.assemble từng speaker → gọi gateway → stream/format → lưu Message/log/relationship → extraction/background → lần sau retrieve.

Trong chat đơn, speaker là nhân vật duy nhất; mọi lớp memory/lore/scene vẫn được assemble. Trong nhóm, assemble riêng người được chọn. Model sinh ngôn ngữ, các thuật toán phía ứng dụng chọn dữ liệu và giới hạn tác động.

Code: character_chat/api/roleplay_chat.py; engine.py.

## 3. Lore retrieval: ACL trước keyword, rồi priority và budget

### Thuật toán hiện có

1. Kiểm user sở hữu Room.
2. Xác định nguồn nhân vật: character:<id>, preset:<type>, nguồn public clone hợp lệ tối đa 8 liên kết; chống vòng lặp bằng tập seen.
3. Lấy lore phòng + lore CMS enabled/target phù hợp.
4. **Lọc scope trước relevance:** public/rumor; private/witnessed theo knowers; discovered phòng chỉ khi unlocked.
5. NFD Unicode + casefold + bỏ dấu, đổi đ→d.
6. Quét câu hiện tại + tối đa 4 message gần nhất.
7. Match từng keyword/alias. Ngôn ngữ dùng khoảng trắng: regex ranh giới từ; CJK/Hangul và các dải SEA hỗ trợ substring.
8. Entry đủ điều kiện khi always hoặc có ít nhất một keyword match.
9. Sắp xếp lexicographic: **canon giảm dần → priority giảm dần → số keyword match giảm dần → ID**.
10. Greedy packing entry nguyên vẹn theo kích thước JSON, ngân sách **4500 ký tự** chung CMS/phòng. Entry quá lớn không bị cắt nửa; có thể bỏ qua để entry nhỏ tiếp theo còn vừa.
11. Ghép lore đã chọn vào prompt, ghi IDs/revision/source/budget vào PromptTrace.

### Lợi ích

Đỡ nhồi kiến thức không liên quan; sửa canon tại CMS áp dụng lượt chuẩn bị tiếp theo; “art” không bị kích hoạt bởi “heart”; actor không được cấp entry riêng của người khác.

### Giới hạn

Không semantic search; alias phải nhập. Always cũng có thể không vừa ngân sách. Canon chỉ ưu tiên và chỉ dẫn LLM, không là bộ chứng minh output đúng. ACL entry không thể thu hồi bí mật đã có trong description/history. Riêng theo character không phải riêng theo user hay unlock bí mật theo tiến trình.

Code: roleplay_lorebook.character_keys/entries_for; roleplay_continuity.visible_entries/context; roleplay_recall.phrase_match; engine.assemble.

## 4. Memory recall: BM25 + tín hiệu chất lượng

### Bước 1: quyền truy cập

Chỉ lấy memory của user, sau đó lọc USER_GLOBAL, CHARACTER_PRIVATE đúng actor hoặc ROOM_SHARED đúng room. Không chạy rank trên toàn memory của mọi người rồi mới lọc.

### Bước 2: tạo đặc trưng

- NFD/casefold/bỏ dấu; regex lấy word; bỏ một danh sách stopword VI/EN hữu hạn.
- Thêm character bigram cho một số chữ không phân tách bằng khoảng trắng.
- Thêm token concept từ dictionary 6 nhóm: coffee/tea/promise/birthday/study/work, một số alias VI/EN/ZH/JA/KO.
- Đây là lexical feature expansion, **không phải embedding hoặc neural semantic understanding**.

### Bước 3: BM25

Với mỗi term t xuất hiện trong query và memory d:

```text
idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))

BM25(q,d) = Σ idf(t) × tf(t,d) × (k1 + 1)
                 / [tf(t,d) + k1 × (1 - b + b × |d| / avgdl)]

k1 = 1.2; b = 0.75
B = BM25 / max(BM25 của các candidate được phép)
```

Đếm từ trong feature list, gồm concept/bigram, không phải token theo tokenizer của LLM. Không có kết quả match thì B=0.

### Bước 4: weighted ranking

```text
T = 1 / (1 + age_days / 30)
R = 0.55 B + 0.16 I + 0.09 T + 0.06 E + 0.08 C + 0.06 P

I = importance
E = 1 nếu type event/preference/llm_extracted, ngược lại 0
C = confidence clamp trong [0,1]
P = pinned (0/1)
```

Thực tế code biểu diễn E bằng emotional=.12 rồi nhân .5. Nếu timestamp lỗi, T=.5.

**Pinned được tách lên trước**, không chỉ được cộng .06. Unpinned phải có B>0. Assemble xin tối đa 12 candidates, sau đó greedy pack trong **3200 ký tự JSON**, kèm scope/confidence/kind/source_message_id.

### Lợi ích

Có cơ hội nhớ “cà phê” khi user hỏi “coffee” hoặc “ca phe”; memory gần chủ đề, quan trọng và đáng tin được ưu tiên; pin giữ điều user chủ động chọn. Không lấp đầy context bằng fact không liên quan chỉ vì còn chỗ.

### Giới hạn

Dictionary nhỏ; không hiểu paraphrase bất kỳ, không tự xác minh sự thật hoặc giải mâu thuẫn. Bị giới hạn char budget; pin rất nhiều có thể chiếm phần lớn chỗ. Truy vấn vẫn đọc tập memory user rồi lọc Python; chưa benchmark kho lớn hoặc vector index.

Code: roleplay_recall.terms/rank_scores; retrieval.retrieve_memories; roleplay_continuity.memory_pack.

## 5. Memory extraction và deduplication

### Trích xuất heuristic

services/roleplay_context.extract_memory:

- Auto-memory của phòng phải bật.
- Text dài ít nhất 20 ký tự, có đại từ VI/EN và từ tín hiệu hữu hạn.
- Phân loại preference/event/fact bằng regex.
- Lưu tối đa 500 ký tự user text, source_message_id; confidence .7; importance .75 hoặc .6.
- Một nhân vật: CHARACTER_PRIVATE; nhiều nhân vật trong phòng: ROOM_SHARED.

Đây là lưu một đoạn phát biểu, không đảm bảo đã chuẩn hóa thành một fact đúng.

### Trích xuất LLM sau reply

background.analyze_turn có thể gọi JSON TurnAnalysis, tối đa 700 output tokens; lưu memory khi memory_worthy, confidence>=.68 và summary không rỗng. Reflection chỉ khi significance>=.62, confidence>=.6, nội dung đủ và không trùng cosine>.86 trong 12 reflection gần nhất.

**Khi JEV emotion bật**, nhánh đó dùng classification và đặt memory_worthy=False, không sinh prose reflection/summary bằng LLM. Heuristic extraction vẫn là đường riêng. Vì vậy “bật JEV” không đồng nghĩa vẫn có semantic memory extraction như nhánh LLM.

### Dedupe đã nâng cấp

Chỉ gộp memory khi content giống nhau sau casefold và chuẩn hóa whitespace. Không dùng cosine>.9 để gộp nữa, tránh biến “thích trà” và “không thích trà” thành một. Phạm vi dedupe luôn cùng user/visibility/character/room.

**Lợi ích:** provenance và ít gộp sai phủ định. **Giới hạn:** duplicate diễn đạt lại vẫn có thể tồn tại; memory đối lập chưa được supersede tự động. BackgroundTasks không là durable queue; hiện việc lấy reply mới nhất của phòng có rủi ro attribution khi lượt chồng nhau.

## 6. Persona và voice lock: layered prompt composition

engine.assemble đưa vào persona JSON, system prompt riêng, speech, scenario, examples, relationship/state, memory/lore, recent history và post-history voice/language lock. Recent context lấy tối đa 24 messages; một số phần bị cắt theo ký tự.

Không fine-tune riêng 11 model. Một model có thể đóng nhiều persona vì mỗi lượt dùng context riêng. Trong nhóm, peer dialogue được trích như lời người khác và có speaker lock; không cho phép model tự viết thay toàn bộ cast.

**Lợi ích:** Nguyễn Vũ vẫn dè dặt; Merr vẫn tinh nghịch; Selene vẫn tò mò theo cách riêng dù cùng trả lời một chủ đề. **Giới hạn:** prompt conditioning không đảm bảo tuyệt đối; core fields hiện có đoạn cắt, chưa token budget thống nhất toàn prompt.

## 7. Speaker router: rules + cosine/topic + fairness + optional JEV

Chỉ áp dụng nhóm. Chat đơn không cần trả thêm phí quyết định người nói.

### Quy tắc ưu tiên

Mention đầy đủ hoặc thành phần tên không trùng → manual selected mode → explicit everyone/pair → follow-up với người vừa nói → rank local. @mention được ưu tiên như policy hiện có. Tên mơ hồ không đoán.

### Local scoring

```text
score = .5 lexical_cosine(query, profile)
      + .5 topic_fit
      + personality_affinity
      + .07 / (1 + recent_speaker_count)
      - .045 nếu là speaker gần nhất

topic_fit = số topic chung / max(1, số topic query)
personality_affinity:
  + .18 × empathy nếu chủ đề comfort
  + .12 × humor nếu chủ đề fun
```

Topic dictionary hỗ trợ một số từ thuộc các ngôn ngữ UI; profile features cache LRU 512. Fairness dùng 6 turn gần nhất trong history tối đa 60 messages.

Thông thường 1 speaker. Pair tự phát cần 2 lượt context, điểm người thứ hai>=.18, chênh lệch<.28, góc nhìn khác và không có pair trong 2 turn gần. User yêu cầu pair có thể vượt cooldown.

### JEV/decision khi cấu hình

Explicit selection và follow-up bỏ qua decision call. JEV chấm candidate speaker A/B, chọn probability>=.65, adapter cap tối đa **2 automatic speakers**; score cao hơn đi trước, local score tie-break. Lỗi/không có speaker tin cậy dùng local fallback. Explicit everyone vẫn có thể gọi cả nhóm.

**Lợi ích:** bớt đồng thanh, bớt duplicate token, gọi “Selene” không phải luôn đủ “Selene Moonbrook”. **Giới hạn:** chưa đủ scene involvement, talkativeness, relationship-aware planning; classifier không viết dialogue. Không biến group AI thành phòng nhiều người thật.

Code: group_routing.py; group_decision.py; jev.select_speakers.

## 8. Relationship: rule deltas, clamp và stage

Quan hệ S khóa user × character; routine chính dùng other_character_id=None.

Familiarity:

```text
F_next = min(1, F + .0035 + .0065 × (1-F))
```

Trust/affinity/respect/tension cập nhật bằng regex phát hiện personal/positive/repair/negative rồi clamp [0,1]. Ví dụ trust tăng .009 nếu personal, ngược lại .003; repair cộng .008; negative trừ .02. Affinity tăng .009 nếu positive hoặc .0025, repair cộng .009, negative trừ .018.

Stage dùng mốc familiarity .06/.16/.32/.52/.75. engine.assemble truyền stage và scores; relationship_expression đổi mức openness/warmth/shorthand, giữ core identity.

**Lợi ích:** có trạng thái bền, không chỉ “model tự kể đã yêu”. **Giới hạn:** các delta này là heuristic thiết kế, chưa được hiệu chuẩn bằng user study; familiarity theo lượt không chứng minh lòng tin. JEV/LLM relationship events chưa là hệ proposed_delta→validated_event toàn diện. Pair character↔character ở World không có nghĩa chat thường đã có đủ.

## 9. Emotion: classification + inertia/decay

JEV emotion nếu có confidence>=.65; khi không dùng được thì regex VI/EN. Character state không nhất thiết giống user mood: user buồn có thể khiến NPC concerned.

Cập nhật mood bằng EMA:

```text
mood_new = .58 × mood_old + .42 × mood_target
intensity_new = .5 × intensity_old + .5 × intensity_target
```

Hurt/sulk có quán tính, không biến mất ngay qua một tin neutral. Offline intensity decay sau 12h/48h; energy hồi theo thời gian và giảm theo độ dài tin.

**Lợi ích:** biểu cảm bớt đổi đột ngột, nhân vật quan tâm phù hợp hơn. **Giới hạn:** không là chẩn đoán tâm lý; regex/decision có thể sai; không bảo đảm áp dụng đúng đối tượng mọi nhóm.

## 10. Episodic recap: structured output + provenance + hash invalidation

User yêu cầu tạo recap; lấy tối đa 60 message, chọn nguyên message trong 16000 ký tự source budget; một JSON generation ra summary/perspective/events. Pydantic kiểm kiểu/độ dài; source_ids phải thuộc tập đã gửi.

SHA-256 fingerprint từ id/sender/character/text phát hiện nguồn bị sửa/xóa; cache recap khi không đổi. Recheck owner/consent/roster/source trước commit; CAS chống ghi đè đồng thời. Snapshot từng room/character, không đưa private lore/memory người khác vào summarizer.

**Lợi ích:** ghi chú episode có thể kiểm nguồn, giảm gọi lại và tránh dùng recap cũ sau sửa source. **Giới hạn:** validate ID không chứng minh lời tóm tắt đúng; recap chưa tự chạy định kỳ; graph hiện chỉ listed_after, không causal graph.

## 11. Initiative và scene

Scene S do owner nhập location/time/objective; truyền như dữ kiện tham chiếu, không tự hoàn thành objective.

Initiative: đếm user turns, nếu turn%4==0, query<=1200 và không có pause intent thì thêm một optional callback/gentle question. Không có thêm call LLM riêng.

**Lợi ích:** có cơ hội nối chuyện mà không buộc user chọn menu. **Giới hạn:** không gửi offline, không suy nghĩ 24/7, chưa unresolved-thread planner; scene nhập tay không tự theo dõi chuyển phòng/vật phẩm.

## 12. JEV moderation, language và suggestion fallback

App gọi TypeSafe qua HTTPS /v1/systemone, structured choices và probability validation. Token chỉ gửi endpoint chính thức; không follow redirect. Cache SHA-256 keyed payload+key, TTL 30 giây, bounded cache; semaphore 8; timeout có giới hạn. Đây là cache kết quả phân loại, không là memory của nhân vật.

Moderation có allow/block/review; uncertain/unavailable không tự cho qua nhánh require_safe. Emotion/routing có local fallback riêng, không dùng nguyên policy fail-closed của moderation cho mọi tác vụ.

Language có remote classification khi bật và local detection; static suggestion fallback chọn ngôn ngữ tương ứng khi suggest timeout. Metadata output language gắn cùng stream; detect_speech_language chạy CPU và **không gọi JEV từng chunk**.

**Lợi ích:** giảm prose-LLM classification và tránh stream bị chặn vì detector mạng lặp lại. **Giới hạn:** provider model internals không có trong repo, không tuyên bố JEV dùng thuật toán ML cụ thể. Decision API không thay generation LLM và không tự sinh lore/recap.

## 13. Document knowledge: chunking + lexical cosine

retrieval.chunks chia theo 750 từ, overlap 80; không theo tokenizer. Query/candidate dùng normalized word-count vectors, cosine dot product. Lọc giới hạn page/chapter và ready room documents; lấy tối đa 4 chunk, threshold>.02 trừ câu hỏi explicit về document; text mỗi chunk<=1800 ký tự.

**Lợi ích:** truy xuất phần tài liệu liên quan, tránh đưa cả file vào context. **Giới hạn:** đây cũng chưa vector semantic RAG; field embedding trong schema không chứng minh đang được dùng. Chunk boundaries không phải semantic paragraph splitting.

## 14. Voice, BGM và độ trễ

TTS đọc cùng text đã lưu của message; speech signature/cache/run/parts tránh tạo một cuộc trò chuyện độc lập. BGM dùng audio engine/playlist cache, volume và lifecycle trên browser. Những việc đó không huấn luyện AI và không cần GPU server để phát media đã có.

SSE giữ phản hồi tăng dần; language detector output không gọi network theo chunk. Không có benchmark cho phép khẳng định tốc độ tăng X%; provider và UI playback vẫn cần đo riêng. TTS/voice ID thật chưa nghiệm thu trong các test dùng mock.

## 15. Revision/CAS và bảo mật state

Update lore/scene/episode dùng revision/value compare trước ghi; stale edit nhận 409; một số luồng kiểm lại source/consent sau external I/O. Auth ownership trước đọc private context. Cache/call cap giới hạn chi phí; không thay thế rate limit hoặc production load test.

**Lợi ích:** giảm ghi đè khi hai tab sửa đồng thời và giảm leak giữa user/actor. **Giới hạn:** SQL/JSON scans chưa tối ưu kho rất lớn; namespace tách World/chat không cách ly CPU, DB pool hay quota vật lý.

## 16. Những gì vẫn chưa có

- Semantic recall/lore đầy đủ, learned embedding ranker và contradiction-resolution tự động.
- Persona-specific memory nhiều vai cho một user.
- Causal Event Graph và Multi-agent Director hoàn chỉnh.
- Autonomous offline proactive agent, marketplace World và phòng nhiều người thật.
- Canon lock bảo đảm output, secret discovery policy xuyên mọi nguồn.
- GPU/image/video/comic generation mới trong đợt này.

Các điểm này không thể đạt chỉ bằng việc dán thêm một prompt. [Audit đầy đủ](world/WORLD_SYSTEM_AUDIT.md) và [kế hoạch](world/IMPLEMENTATION_PLAN.md) phân biệt phần đã có/đang thiếu.
