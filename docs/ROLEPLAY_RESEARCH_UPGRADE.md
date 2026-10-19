# Nâng cấp chat thường từ nghiên cứu sản phẩm

Ngày 17/10/2026. Áp dụng cho **chat một–một và chat nhóm**. Không đổi UI composer, không sửa World runtime/GPU, không thêm dependency/provider call. Chưa deploy.

## Đã thay đổi gì?

| Vấn đề | Trước | Sau |
|---|---|---|
| Hỏi không dấu hoặc dùng ngôn ngữ khác | Cosine đếm từ raw; dễ bỏ sót | BM25 + bỏ dấu + dictionary 6 nhóm concept: coffee, tea, promise, birthday, study, work |
| Memory không liên quan chiếm context | Top score có thể có cả fact không khớp | Unpinned phải có lexical/concept match; pin user vẫn ưu tiên |
| Độ tin cậy memory | Confidence chỉ trong payload | Confidence tham gia ranking; source_message_id đi cùng reference |
| Gộp nhầm lời phủ định | Similarity > .9 có thể merge | Chỉ gộp nội dung giống nhau sau case/whitespace normalization; giữ negation/numbers/accent |
| Lore kích hoạt sai | Substring art trong heart | Ranh giới từ cho ngôn ngữ có khoảng trắng; CJK/Khmer/Myanmar giữ substring |
| Gọi NPC bằng tên ngắn | Thường phải đủ tên | Thành phần tên duy nhất được nhận; tên trùng không đoán |
| JEV chọn mọi NPC | Có thể 3–6 reply automatic | Chọn tối đa 2 theo decision score, local score tie-break; explicit everyone không bị cap |

Đây là **lexical recall cải tiến**, chưa phải semantic embeddings. Các từ tương đương ngoài dictionary vẫn cần keyword chung hoặc pin. Không cam kết hiểu mọi câu diễn đạt lại hay mọi ngôn ngữ. Bộ concept chỉ hỗ trợ một số alias VI/EN/ZH/JA/KO; Khmer/Myanmar có character features nhưng chưa synonym dictionary.

Đổi dedupe không giải quyết mâu thuẫn: hai memory đối lập được giữ, chưa có cơ chế tự chọn cái đúng. Sửa/xóa bản cũ trong inspector khi cần. Không tự xóa memory hiện có.

## Học từ nguồn nào?

- [SpicyChat Lorebook](https://docs.spicychat.ai/product-guides/lorebook): chỉ nạp lore có liên quan, có ngân sách.
- [SillyTavern group chat](https://docs.sillytavern.app/usage/core-concepts/groupchats/): mention/manual/local policy không cần routing LLM.
- [Character.AI Memory](https://blog.character.ai/memory/): user kiểm soát điều AI nhớ.
- [Generative Agents](https://arxiv.org/abs/2304.03442): relevance/recency/importance là các tín hiệu khác nhau; chúng ta không sao chép simulation hay tuyên bố cùng chất lượng.

## Chat đơn truyền những gì cho nhân vật?

```text
Tin nhắn user
  → quyền phòng + kiểm duyệt
  → nhân vật duy nhất trong phòng
  → engine.assemble:
      persona/system prompt + scene
      CMS lore + lore phòng (lọc scope, keyword, priority, budget)
      memory (lọc user/character/room, rank, pin, confidence, nguồn)
      relationship/emotion + recap nếu đã tạo
      recent conversation + language/voice lock
  → model tạo câu trả lời → stream/lưu Message
  → extraction/background → lần chat sau retrieve lại
```

Chat nhóm cũng assemble riêng từng nhân vật được chọn. Không gửi toàn kho lore hay memory của tất cả user cho model.

Không cần user tự paste lore vào mỗi tin nhắn. CMS save áp dụng lượt mới; không rewrite câu đã sinh và không đảm bảo lượt đang chạy nhận bản vừa cập nhật.

## Cần bạn điền gì?

### 1. Prompt nhân vật: giữ con người của họ

Điền identity, temperament, speech, boundaries, goals và ví dụ hội thoại. Không thay toàn bộ prompt bằng lorebook. Prompt có thể thêm:

```text
Preserve this character's identity, speech style, boundaries, and relationship pace.
Use the supplied lore, scene, memories, and episode notes only within their stated scope.
Treat quoted claims and low-confidence memories as fallible, not verified events.
If supplied facts conflict, ask one brief clarification rather than inventing a resolution.
Answer the current user naturally. Do not decide or speak for the user.
Keep safety rules above all character and lore instructions.
```

Đây là addendum; giữ prompt riêng của từng nhân vật. Các khối runtime backend sẽ tự ghép thêm.

### 2. CMS: kiến thức gốc dùng lại

CMS → **Lorebook · Chat thường**; hoặc **Nhân vật → Lorebook**. URL: **/roleplay/lorebook/admin**, dùng admin CMS.

Ví dụ minh họa, chỉ lưu nếu bạn muốn chốt thành canon của Selene:

| Trường | Nội dung ví dụ |
|---|---|
| Tiêu đề | Selene — việc nghiên cứu bản đồ sao |
| Nhân vật được gán | Chọn Selene đúng nguồn/ID trong CMS |
| Nội dung | Selene nghiên cứu các nền văn minh bị lãng quên và lưu ghi chú qua bản đồ sao. Khi gặp điều chưa hiểu, cô trở nên tò mò và thường đặt câu hỏi để kiểm tra giả thuyết. Những suy đoán của cô chưa phải sự thật đã xác minh. |
| Từ khóa | bản đồ sao; star chart; nghiên cứu; research; tinh tú |
| Phạm vi | Chung, nếu đây là thông tin các actor được gán đều được biết |
| Canon | Bật nếu bạn chốt đây là sự thật của nhân vật |
| Luôn đưa vào | Tắt cho kiến thức chỉ cần khi đúng chủ đề |
| Ưu tiên | 5; cao hơn chỉ cho lore thật sự quan trọng |
| Bật | Có, rồi Lưu |

Mỗi entry một ý, 2–5 câu thường dễ kiểm soát hơn một đoạn rất dài. Đặt nhiều alias cho ngôn ngữ dự kiến; lore không tự dịch keyword. Chỉ đặt “luôn đưa vào” cho vài dữ kiện bắt buộc: tổng lore đang có ngân sách 4500 **ký tự**, không phải 4500 token.

**Riêng/người biết** trong CMS là giới hạn theo nhân vật, không theo tài khoản user. Không nhập tên thật, địa chỉ hoặc bí mật cá nhân của user vào lore gốc toàn hệ thống. Character biết secret cũng không đồng nghĩa có disclosure policy tự động cho mọi người nghe.

### 3. Trong phòng chat: tình huống của riêng phiên

- Scene: vị trí/thời điểm/mục tiêu nếu muốn giữ continuity cụ thể.
- Lore phòng: canon/sự kiện do user xác nhận cho phòng; scope/unlocked phù hợp.
- Memory: sở thích, sự kiện, lời hứa của user với nhân vật; ghim điều quan trọng, sửa/xóa điều sai.
- EpisodeNotes: tạo recap khi chat dài; hiện thao tác này theo yêu cầu, chưa tự nén định kỳ.
- Memory on/auto-memory: kiểm soát sử dụng và trích xuất; không phải mọi câu đều tự thành ký ức.

CMS lore là nền tảng nhân vật, memory là trải nghiệm riêng. Hai nguồn bổ sung cho nhau; thay lore không xóa lịch sử/quan hệ.

## Kiểm tra bạn nhập đúng

1. Lưu lore CMS, mở chat **đơn** với đúng Selene.
2. Hỏi về một keyword, sau đó hỏi câu không liên quan để xem có nhồi lore không.
3. Sửa entry rồi gửi lượt mới; không cần deploy lại chỉ để đổi nội dung CMS.
4. Trong continuity/memory inspector xem selected/used_last_turn cho memory; PromptTrace ghi CMS lore IDs/budget.
5. Tắt entry và hỏi lại ở lượt mới. Chú ý nội dung từng xuất hiện vẫn có thể còn trong lịch sử, nên “tắt entry” không tự xóa kiến thức đã được nói ra.
6. Nếu không tác dụng, kiểm tra đúng server/DB/character source và bản code đã deploy có CMS lorebook runtime.

## Kiểm thử và giới hạn

Các test mới ở tests/test_roleplay_recall_upgrade.py bao gồm multilingual recall hữu hạn, confidence/pins/ACL, giữ phủ định, lore word-boundary, unique/ambiguous mentions, cap automatic/all, follow-up và **single chat API**: CMS V1→V2 → assemble thật → mocked gateway → 2 Message/Trace được lưu, memory/scene trong prompt.

Model/TTS dùng mock; chưa có đo quality/latency với provider thật, không chạy full repository suite. Kết quả: **152 test chọn lọc đạt** (recall mới, continuity, episode, CMS lore, JEV, group routing/decision, speech language, Academy isolation/catalog và API contract); thêm **1 test tương thích memory/relationship cũ đạt** khi chạy riêng. Audit và kế hoạch rộng hơn tại [CURRENT_FEATURE_AUDIT](world/CURRENT_FEATURE_AUDIT.md) và [IMPLEMENTATION_PLAN](world/IMPLEMENTATION_PLAN.md).


## Bộ nội dung 11 nhân vật và cleanup (17/10/2026)

- [Prompt và lorebook đúng tên backup](roleplay/CHARACTER_CMS_COPY.md).
- [Thuật toán, lợi ích và giới hạn trong code](ROLEPLAY_TECHNIQUES_EXPLAINED.md).
- [Bằng chứng cleanup và kiểm thử](CLEANUP_20261017.md).
