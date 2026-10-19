# Bài toán → cơ chế → khoảng trống

Ngày 17/10/2026. Đọc cùng [kiểm kê](CURRENT_FEATURE_AUDIT.md) và [nguồn cạnh tranh](COMPETITIVE_GAP.md). Chi phí là số lần gọi bổ sung dự kiến, không phải giá tiền hay benchmark.

| Problem | User symptom | Existing solution | Current system | Gap | Recommended solution |
|---|---|---|---|---|---|
| Quên điều quan trọng | Nhắc lại sở thích mà nhân vật không nhớ | [Character.AI Memory](https://blog.character.ai/memory/) | Memory thật + recall BM25, pin | Chưa semantic/consolidation | Recall có nguồn + đánh giá paraphrase rồi thêm embeddings tùy chọn |
| Lore lấn cá tính | Nhân vật kể hết tiểu sử thay vì trả lời | [SpicyChat Lorebook](https://docs.spicychat.ai/product-guides/lorebook) | ACL/keyword/priority/4500 ký tự | Budget chưa là token toàn prompt | Token budget theo model, reserved persona/reply |
| Cùng lore bị viết lại nhiều lần | Các nhân vật mâu thuẫn cùng sự kiện | [Character.AI shared lore](https://blog.character.ai/lorebook/) | CMS entry target nhiều actor | Chưa version pack/import | Giữ entry chung, thêm preview per-character trước publish |
| Lộ điều nhân vật không biết | Mystery mất ý nghĩa | [ST character filters](https://docs.sillytavern.app/usage/core-concepts/worldinfo/) là filter, không bằng chứng full secrecy | Memory/lore ACL, World witnesses | Transcripts/secret discovery còn thiếu | Một knowledge-envelope áp dụng mọi nguồn |
| Cả nhóm đồng thanh | Tốn tiền, lẫn vai | [ST Natural/Manual](https://docs.sillytavern.app/usage/core-concepts/groupchats/) | Local scoring/JEV, nay cap 2 | Chưa talkativeness/scene-aware đầy đủ | Deterministic first; decision only khi mơ hồ |
| Tính cách giống nhau | AI nào cũng thành trợ lý | [ST card swap](https://docs.sillytavern.app/usage/core-concepts/groupchats/) | Persona/voice lock riêng | Chưa evaluation trên model thật | Identity regression set + bounded prompt |
| Quan hệ tăng vô nghĩa | Chat vài câu đã quá thân | Không suy thuật toán điểm số của đối thủ | Stage + clamp + familiarity mỗi lượt | Chưa event attribution/chống farm | Delta dựa sự kiện được nguồn xác nhận, cooldown |
| Không biết làm gì | Bỏ World sau khi mở | [Books](https://blog.character.ai/cai-books/), [ISEKAI](https://www.isekaizero.ai/about) | Missions/map CTA | Chat không hiểu state đủ | Inject quest/inventory; offer action có xác nhận |
| Lựa chọn không có hậu quả | Bấm khác nhau nhưng truyện như nhau | [ISEKAI authored story](https://www.isekaizero.ai/blog/zeta-ai-review) | Delta/2 epilogue; quest tuyến tính | Trả lời reconcile/accuse giống nhau | Cảnh hậu quả riêng + gate có thể kiểm tra |
| Bí mật đổi theo người chơi chọn cast | Nhân vật đổi quá khứ bất ngờ | Không có bằng chứng cơ chế đối thủ tương đương | Secret template theo index | Sai identity invariants | Bind story role theo actor ID khi tạo |
| History bị cắt | NPC quên chuyện sau nhiều ngày | [Generative Agents](https://arxiv.org/abs/2304.03442) | W 120 event; S bounded window + memory | Không có archive/recap W | Append event + episodic summary có provenance |
| Mất cảm giác thế giới sống | Trở lại không có chuyện gì mới | [AI Town](https://github.com/a16z-infra/ai-town/blob/main/ARCHITECTURE.md) simulation | Lazy daily authored hook | Không activity/cooldown/quiet-hours | Event-driven return policy, không agents 24/7 |
| Voice tách trải nghiệm | Nghe lại tốn thời gian/tiền | [ISEKAI voice](https://www.isekaizero.ai/about) | S cache; W same text/no cache | Adapter trùng, W replay tạo lại | Shared TTS cache service, scoped message IDs |
| Music không theo cảnh | Thiếu cảm giác địa điểm | [ISEKAI music](https://www.isekaizero.ai/about) chỉ chứng minh soundtrack | Shared playlist, duck | Chưa scene tags | Static scene→playlist mapping, opt-in |
| Muốn chơi với bạn thật | Không mời được người khác | Không đánh đồng group AI với multiplayer | Room một owner | Chưa membership/consent | Tách dự án P2; owner/member roles, ACL, rate limits |
| Nhiều vai cùng tài khoản | Quan hệ từ vai cũ lẫn vai mới | [ST persona lore](https://docs.sillytavern.app/usage/core-concepts/worldinfo/) | user_id/character_id | Không persona dimension | Persona ID migration + explicit switch, không ngầm trộn |
| Creator đưa lore lên | Không có chỗ authoring/publication đầy đủ | [Character.AI Lorebook](https://blog.character.ai/lorebook/) | CMS admin; cộng đồng tạm tắt | Thiếu review UI/packs | Hoàn thiện moderation/review trước marketplace |

## Hồ sơ giải pháp

### 1. Memory đáng tin cho chat đơn lẫn nhóm — P0

**USER PROBLEM:** nhân vật phủ nhận lời hứa/sở thích cũ. **WHY:** mất niềm tin quan hệ, buộc user nhắc lại. **REFERENCE:** Memory UX Character.AI; retrieval trong Generative Agents (nguồn ở bảng).

**HOW THEY SOLVE IT:** facts/pin/context management hoặc memory retrieval, không suy đoán implementation thương mại. **OURS:** Memory lưu bền, extraction heuristic và optional background LLM, pin, BM25 + alias hữu hạn, importance/recency/confidence. **GAP:** vẫn không hiểu paraphrase bất kỳ, mâu thuẫn chưa versioned.

**RECOMMENDED/TECHNICAL:** giữ private ACL trước retrieval; retrieval trace; source attribution; revision/supersedes thay vì tự xóa fact trái ngược; embedding chỉ sau bộ đo recall. **COST:** bản hiện tại CPU, 0 call mới; future embedding 1 lần/fact và query cache; recap theo mốc. **SUCCESS:** không leak trong bộ ACL; recall@5 trên tập paraphrase có nhãn; số lần user sửa memory/100 turn giảm. Chỉ đặt mục tiêu sau baseline, chưa có số đo thực tế.

### 2. Canon đúng người, đúng lúc — P0

**PROBLEM/WHY:** lore quá dài làm model lẫn vai; lore bí mật đến sai actor làm hỏng truyện. **REFERENCE:** keyword budget SpicyChat, source/filter/insertion SillyTavern. **OURS:** target/knowers, keywords, canon/priority, 4500 ký tự; chat đơn đi cùng luồng. **GAP:** chưa token model-aware, chưa disclosure per-player.

**SOLUTION/TECHNICAL:** typed entry + target + visibility + source + revision; ACL trước rank; preview prompt cho actor; byte/char không được ghi là token. **COST:** CPU và DB, không thêm LLM mỗi lượt. **PRIORITY:** P0 boundaries; P1 preview/token accounting. **SUCCESS:** zero forbidden-entry in prompt ở exhaustive scope tests; quota không vượt context; lượt hỏi lore đúng tăng trong eval.

### 3. Group tự nhiên, ít chi phí — P0/P1

**PROBLEM/WHY:** mọi bot trả lời làm hội thoại cơ học và phí nhân số actor. **REFERENCE:** SillyTavern natural/manual và card swap. **OURS:** full/unique short mention, follow-up, topic relevance, fairness, JEV cap 2. **GAP:** relationship/talkativeness/scene involvement chưa đầy đủ.

**SOLUTION/TECHNICAL:** direct mention/manual luôn ưu tiên; local rank và cooldown; remote classification chỉ khi chưa rõ; max 1–2 automatic, explicit everyone là ngoại lệ. Không quyết định response text bằng router. **COST:** local 0 call; JEV configured tối đa 1 routing decision/lượt hiện tại. **SUCCESS:** direct mention đúng 100% ở bộ test; tỷ lệ người nói không liên quan và số output token/lượt nhóm giảm; đo naturalness bằng đánh giá người dùng.

### 4. Hậu quả khiến World đáng chơi — P0 riêng World

**PROBLEM/WHY:** nói “đưa vật phẩm” mà chỉ chat được, nhiệm vụ không đổi. **REFERENCE:** ISEKAI/Books là guided narrative; không suy backend họ. **OURS:** backend state thật nhưng say không nối action. **GAP:** prompt thiếu state quan trọng; cast-index secret không bền.

**SOLUTION/TECHNICAL:** bản đồ action hữu hạn; AI chỉ đề nghị action ID, server validate inventory/location/unlock, user xác nhận; durable outcome event; ổn định story-role assignment. **COST:** không cần director model riêng cho mỗi token; classify theo yêu cầu hoặc cùng response JSON. **SUCCESS:** hội thoại hướng dẫn đúng next valid action; action trái quyền không đổi DB; reorder không đổi secret; ending khác biệt theo branch.

### 5. Cảm giác sống khi quay lại — P1

**PROBLEM/WHY:** user quay lại không có điểm nối để bắt chuyện. **REFERENCE:** AI Town và Generative Agents cho simulation; không coi đó là thiết kế rẻ mặc định. Kindroid claim chưa xác minh nên chưa dùng làm dependency.

**OURS:** hook mỗi 4 lượt S, daily authored W. **GAP:** không là backlog unresolved threads và policy opt-in. **SOLUTION/TECHNICAL:** user opt-in, genuine last_activity, due thread, cap/ngày, quiet hours/timezone, relevance, no-op; lazy on-open trước khi làm push. **COST:** authored 0 call; cá nhân hóa tối đa 1 call khi đủ điều kiện, idempotency chống lặp. **SUCCESS:** return→meaningful reply conversion; tắt notification/spam report không tăng.

### 6. Quan hệ và scene nhất quán — P1

**PROBLEM:** user bày tỏ tức giận về công việc nhưng NPC tưởng đang bị ghét; địa điểm thay đổi tùy câu sinh. **WHY:** intimacy không được xây dựng, world thiếu vật lý ổn định. **REFERENCE:** memory/context và shared-state patterns, không có cơ sở chấm hệ điểm quan hệ độc quyền của đối thủ.

**OURS:** structured delta/clamp + emotion inertia; scene 3 trường; W có location/pair relations. **GAP:** chưa attributed events đầy đủ, chưa presence lịch sử trong room S. **SOLUTION:** proposed event với target IDs + nguồn → business rules → delta; scene explicit owner hoặc action xác nhận; snapshot per turn. **COST:** rule evaluator CPU; reuse JEV user classification, không gọi LLM mỗi biểu cảm. **SUCCESS:** anger-at-work không giảm trust NPC; replay không nhân delta; room/persona khác không thừa kế sai.

### 7. Media và creator — P2

**PROBLEM:** nghe lại gọi TTS nhiều lần; muốn viết lore nhưng không biết nhập đâu. **WHY:** latency/phí và thao tác khó làm giảm immersion. **REFERENCE:** ISEKAI voice/music, Character.AI authoring. **OURS:** voice same reply text, shared music, CMS lore S; W authoring còn hẹp. **GAP:** W TTS cache, creator packs, multiplayer đều chưa đủ.

**SOLUTION:** cache theo message/version/voice/model; guide CMS và preview; admin review rõ trước mở public. **COST:** cache hit 0 inference; miss 1 TTS call. **SUCCESS:** repeat playback không gọi provider; admin đổi lore ảnh hưởng lượt tiếp theo; publication chưa approved không public. Không thêm comic/video/GPU trong scope hiện tại.
