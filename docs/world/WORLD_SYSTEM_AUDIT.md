# Audit hệ thống Roleplay và World

Ngày 17/10/2026. Baseline bắt buộc đã đọc đầy đủ: [nghiên cứu 2026](../research/ai_role_play_research_2026.md). [Kiểm kê](CURRENT_FEATURE_AUDIT.md), [so sánh nguồn](COMPETITIVE_GAP.md), [bài toán/giải pháp](PROBLEM_SOLUTION_MATRIX.md), [kế hoạch](IMPLEMENTATION_PLAN.md).

## 1. Executive summary

**Chưa tương đương toàn bộ các sản phẩm tham khảo.** Chat thường đã có nhiều lớp thực: persona, history, Memory, lore CMS/phòng, relationships, source-bound recap, router, JEV, SSE và TTS. World có gameplay scripted lưu bền nhưng chưa nối trơn tru chat tự do với quest; việc có nhiều module không chứng minh đã có world simulation.

Audit ban đầu không sửa runtime. Theo yêu cầu tiếp theo của user, đã nâng cấp riêng recall/router/lore cho chat thường; chi tiết thay đổi và kiểm thử ở [báo cáo nâng cấp](../ROLEPLAY_RESEARCH_UPGRADE.md). Không đổi World/GPU.

## 2. Những gì tồn tại

React 19/TypeScript/Vite; Python FastAPI; SQLAlchemy, mặc định SQLite; bearer session hash và admin HTTP Basic. User/Character/Room/Message riêng; roleplay engine/gateway, background extraction, TTS/cache và asset APIs. World mới lưu aggregate trong AppSetting, CMS khác namespace; legacy World vẫn có routes.

DATABASE_URL không có nghĩa đã tương thích PostgreSQL hoàn chỉnh: connect_args check_same_thread và migrations còn SQLite-specific. Không có bằng chứng đang dùng MongoDB.

## 3. Những gì thật sự hoạt động

Lore CRUD → scope → keyword → budget → prompt; pin/sửa/xóa memory → retrieve → assemble; relationship fields → prompt; local/JEV speaker selection; World choice/gift/visit → state/CAS → reload/UI; owner isolation và original-chat snapshot invariants. Kiểm thử dùng DB cô lập, provider mock khi cần. Provider thật chưa được nghiệm thu.

## 4. Những phần chỉ một phần

Memory có lưu bền nhưng lexical, không phải semantic trí nhớ như con người. Recap được tạo theo yêu cầu, không tự consolidation. Scene S nhập tay 3 trường. Canon là instruction. Relation S phần lớn regex/tăng familiarity; W có rule gifts/choices nhưng say không cập nhật. World daily hook là lazy trigger.

## 5. Các khả năng dễ bị tưởng đã hoàn thiện

- “Event graph” hiện là events có nguồn với cạnh listed_after, không causal graph.
- “Planner” hiện là hook mỗi 4 lượt, không autonomous agent.
- “Long-term World memory” bị cắt còn 120 quan sát, scene 60 dòng.
- “AI hiểu nhiệm vụ” chưa đủ: context W không có inventory/completed/current event.
- “Thay đổi quan hệ ảnh hưởng diễn biến” chỉ một phần: delta thật, reply authored accuse/reconcile giống nhau.
- “Secret riêng của nhân vật” hiện template theo index, có thể thay khi reorder.
- “Checkpoint/dice/3 ending” có ở legacy, không thể cộng cho Academy default.
- Không kết luận mission mất sau refresh: kiểm thử cho thấy persistence thực sự hoạt động.
- Không kết luận relationship chỉ là điểm trang trí: nó thực sự được truyền vào context.

## 6. Những phần thiếu

Persona-specific memory; semantic lore/recall tùy ý; consolidation chống mâu thuẫn; discovered_by per-user secret; causal event graph; stable story-role cast; per-event delivery; comprehensive prompt token budget; realtime calls/STT; ordinary character-pair relationship loop; collaborative human room; self-service World creator/marketplace hoàn chỉnh.

## 7. Đối thủ đã xác minh đến đâu?

Character.AI: source xác nhận shared keyword Lorebook, editable Facts/pins/Memory Usage và nén background; Books/Comics/Series là format thật được mô tả. Animate và creator series tools còn có ngôn ngữ roadmap ở nguồn đọc được.

SpicyChat: keyword activation 4 message, khoảng 2 lượt, khoảng 20% context; semantic memory do hãng công bố, không biết internal ranker.

SillyTavern: keyword/vector World Info, context scope/budget/insertion; natural/manual/list/pooled routing, talkativeness; shared group history không phải knowledge secrecy.

ISEKAI: nguồn hãng mô tả cast/shared story memory/dice/VN/voice/music; không có bằng chứng thuật toán privacy/ranking. AI Town/Generative Agents là kiến trúc/source/paper để học; không so performance với sản phẩm thương mại. Kindroid chưa tải được nội dung docs nên giữ UNKNOWN. Links và matrix trong COMPETITIVE_GAP.

## 8. Những vấn đề người dùng đang gặp

Nhân vật quên, trả lời chung chung, lore kích hoạt sai, nhóm nhiều người nói cùng lúc, không rõ nhiệm vụ tiếp theo, lựa chọn ít hậu quả, khó biết lore phải nhập ở đâu. Chưa có dữ liệu user study để khẳng định tỷ lệ lỗi hay retention.

## 9. Cơ chế tham khảo giải quyết vấn đề

Externalize facts/notes → selective retrieval; lore authored → keyword/vector activation; card-per-speaker → giữ identity; rule-governed state → narrative bám gameplay; event log → memory/recap; scheduler có hạn mức → cảm giác sống. Không cần sao chép model/dependencies/GPU.

## 10. Hệ thống mình đang giải quyết như thế nào?

S: user input → moderation → router → assemble(persona/scene/lore/memory/relationship/recap) → gateway/SSE → Message → extraction/background → lần sau recall. W: owner aggregate → rules hoặc direct model dialogue → CAS → projection. Hai trải nghiệm khác nhau; W chưa hưởng đầy đủ ordinary engine.

## 11. Các khoảng trống quan trọng nhất

P0 W: thiếu gameplay state trong prompt, cast-index secrets, boundary giữa unlock và discovery.
P0 S: negation dedup đã sửa; cần source revision/contradiction lifecycle và full context budget.
P1 S: lexical paraphrase coverage, recap scheduling, attributed relationship events.
P1 W: archive, meaningful branch feedback, cached voice, relevant hints.

## 12. Kiến trúc đề xuất

Giữ UI/state World và S tách biệt như yêu cầu user. Chia sẻ **pure services**: character identity snapshot, scoped context envelope, token budget, gateway adapter, voice/cache. World adapter bổ sung allowed gameplay facts/actions; S adapter bổ sung private-room history. Không đưa memory World sang chat thường ngầm.

Aggregate JSON đủ cho demo nhưng scan prefix rồi lọc owner và ghi lại cả JSON không thích hợp khẳng định scale 5000 CCU. Future schema typed + owner index + event log + migration có version; durable jobs cho recap cần đảm bảo.

## 13. Chi phí runtime

- Recall/lore/mention/local scoring mới: 0 call provider/GPU thêm; CPU tăng theo số memory được phép.
- Speaker count k thì response generation khoảng k lần; explicit all cần hiện rõ chi phí ở product requirements.
- JEV classification có mạng/cache; không sinh câu trả lời hay tóm tắt thay LLM.
- JEV emotion bật: background nhánh đó không tạo memory_summary/reflection LLM.
- Recap hiện 1 JSON call khi user yêu cầu; giữ cache/fingerprint.
- W say serial tối đa 2 calls, không SSE; lỗi/CAS sau inference có thể mất lượt nhưng vẫn phát sinh phí.
- W voice replay hiện không có cache bền.
- Không có benchmark RPM/TTFT/tokens/sec trong audit này; không đưa số suy đoán.

## 14. UX và immersion

Academy có SVG cảnh, map địa điểm, portrait cast, quest CTA, journal drawers, animation và ending modal: gần narrative demo hơn dashboard CRUD. Tuy nhiên nhiều sidebar/tab và thuật ngữ memory/secret có thể làm người mới khó hiểu.

Chưa đo mốc 3 giây với user thật. Đề xuất kiểm thử 5 người desktop: mở World → chỉ hành động khả dụng → làm nhiệm vụ đầu không nhờ người hướng dẫn. Hints theo bước, CTA một hành động rõ, vật phẩm liên quan ngay trong scene. Giữ technical inspector trong phần mở thêm.

Chat thường giữ composer quen thuộc; lore/memory là context ẩn, không bắt user đi flow gameplay.

## 15. Retention loop

| Bước | Kết quả | Bằng chứng/thiếu |
|---|---|---|
| Open world | WORKING | List/create/load private instance |
| See changed | PARTIAL | Daily hook không phản ánh hoạt động offline thật |
| Get goal | WORKING | Authored missions/map CTA |
| Enter scene | WORKING | Visit + presence + locked validation |
| Interact | PARTIAL | Chat và choices cùng UI nhưng chưa chung gameplay meaning |
| Make decision | WORKING | Choice rules/CAS |
| World changes | PARTIAL | Flags/relations có; scene text phản ứng chưa đủ |
| Reward/discovery | WORKING | Inventory/unlock/ending |
| New open thread | PARTIAL | Invitation/ngày, thiếu chapter kế tiếp có thể chơi |
| Return later | PARTIAL | Persistence có; lý do quay lại chưa được đo |

## 16. P0

Boundary/provenance; prompt W có state được phép; stable actor-role secrets; no false completion; source-linked memory; token budget; test single/group/regression trước deploy. S đã sửa fuzzy negation dedup, mention alias và automatic cap.

## 17. P1

Memory evaluation/optional semantic retrieval, bounded recap tự động có consent, relation-event attribution, World branch feedback, contextual hints, TTS replay cache, activity-based return hook, prompt preview CMS.

## 18. Chưa đáng xây ngay

Agents suy nghĩ 24/7, director gọi thêm mỗi turn, tự spawn cast không kiểm soát, comic/video/ảnh GPU mới, marketplace/payment trước core, migration toàn DB chỉ vì competitor dùng công nghệ khác. Không cần mọi feature nghiên cứu để giải tốt chat thường.

## 19. Khác biệt thực tế

TTS/basic group: EXPECTED. Lore editor: EXPECTED/COMPETITIVE tùy usability. Long-term recall đáng tin: COMPETITIVE nhưng hiện mới BASIC. Knowledge visibility đúng mọi nguồn: có thể DIFFERENTIATED sau kiểm chứng. Pair relationship có hậu quả: tiềm năng, chưa chứng minh moat.

World+state+relationship+memory+voice chỉ là POTENTIAL MOAT nếu có nội dung và chất lượng duy trì qua thời gian; hiện chưa có dữ liệu thị trường để tuyên bố khác biệt độc quyền.

## 20. Roadmap và kết luận theo bài toán

| Bài toán | Đã giải? | Kết luận |
|---|---|---|
| Chat đơn dùng lore/memory đúng character | YES trong integration với mock model | CMS save → prompt lượt kế tiếp; memory/scene/relationship không đòi chat nhóm |
| Nhớ lâu mọi cách diễn đạt | PARTIALLY | Memory bền, keyword/BM25; semantic recall chưa đủ |
| Group không mọi bot trả lời | YES với policy hiện tại | 1–2 tự động; user gọi tất cả là ngoại lệ |
| Tính cách ổn định mọi tình huống | PARTIALLY | Có identity lock, chưa eval model thật |
| NPC không biết điều không chứng kiến | PARTIALLY | Lore/memory ACL tốt hơn raw history; W secrets và room membership còn gap |
| Chat tiến triển quest tự nhiên | NO ở W say hiện tại | Chỉ choice/gift rules đổi gameplay state |
| Thế giới sống ngoài phiên | NO theo nghĩa simulation | Có lazy authored hook; không có scheduler autonomous |
| Admin tự chỉnh toàn bộ story | NO | Hiện chỉ instruction/public lore/model |
| S và W cách ly dữ liệu | YES ở invariants được test | Không đồng nghĩa cách ly CPU/quota/pool hay toàn bộ bảo mật sản phẩm |

Ưu tiên 3 hệ thống: **recall có nguồn**, **scoped context thống nhất**, **rule-driven action có hậu quả**. Bổ sung router và event-driven recap khi đo chứng minh cần. Kế hoạch file/API/migration được mô tả riêng; không sửa World trong đợt này.
