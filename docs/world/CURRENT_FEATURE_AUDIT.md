# Kiểm kê tính năng hiện tại

Ngày kiểm tra: 17/10/2026. Mốc nghiên cứu ban đầu: [AI Roleplay Research 2026](../research/ai_role_play_research_2026.md).

## Phạm vi và mức bằng chứng

Đối chiếu workspace hiện tại, không phải bản đã deploy. Nhiều thay đổi chưa commit. Sau yêu cầu tiếp theo “học theo để nâng cấp AI chat thường”, đã áp dụng các thay đổi nhỏ mô tả trong [báo cáo nâng cấp](../ROLEPLAY_RESEARCH_UPGRADE.md); bảng dưới phản ánh trạng thái sau thay đổi. World chỉ được kiểm tra, không sửa runtime trong đợt này.

IMPLEMENTED nghĩa là luồng trong phạm vi nêu có bằng chứng code và kiểm thử tích hợp với DB thật cô lập; LLM/TTS dùng mock khi cần. Không có nghĩa chất lượng model, throughput, trải nghiệm thực tế hoặc deployment đã được chứng nhận. PARTIAL nghĩa là có hoạt động nhưng chưa giải quyết đầy đủ bài toán. NOT FOUND nghĩa là không tìm thấy trên đường chạy đã truy vết. “Không tìm thấy” không phải khẳng định tuyệt đối toàn bộ repository không có bất kỳ đoạn code liên quan.

S = chat thường; W = Moonfall Academy đang được giao diện mặc định sử dụng. Legacy World được ghi riêng.

| Feature | Status | Frontend | Backend | DB | AI logic | Actually works? | Notes |
|---|---|---|---|---|---|---|---|
| Đăng nhập, quyền phòng | IMPLEMENTED | Login, token | services/authentication.py; owner checks | UserAccount/UserSession/Room | Không cần AI | Có trong test quyền truy cập | PBKDF2, token hash; DEMO_AUTH phải cấu hình theo môi trường |
| Cá tính nhân vật S | PARTIAL | Character editor, ChatView | engine.assemble; character compiler | Character.spec, StyleExample | Persona + voice lock + ví dụ | Có inject; độ nhất quán model chưa đo | Prompt không bảo đảm model luôn diễn đúng vai |
| Hội thoại và SSE S | IMPLEMENTED | ChatView, API stream | api/roleplay_chat.py | Message, AIRequestLog | Assemble → gateway → lưu reply | Luồng code thật, provider mock | Chưa đo tốc độ provider thật; không quy mọi độ trễ cho JEV |
| Memory dài hạn S | PARTIAL | RememberMessage, inspector | retrieval; extract_memory; background | Memory | Trích xuất heuristic/LLM; BM25 + confidence | Có lưu và dùng lại qua assemble | Không phải semantic embeddings; chưa consolidation/giải quyết mâu thuẫn |
| Ghim/sửa/xóa memory | IMPLEMENTED | RememberMessage, continuity panel | memory_routes; api/roleplay_continuity | Memory, source_message_id | Prompt đọc bản đã sửa theo quyền | Test source/ownership/pin | Xóa nguồn chưa đồng nghĩa mọi memory dẫn xuất đều được xóa |
| Memory theo persona người dùng | NOT FOUND | Chưa có chọn persona độc lập trên luồng này | Khóa hiện là user/character/room | Không có persona_id trên Memory | Chưa tách vai | Không | UserProfile không tương đương nhiều persona |
| Episodic recap S | PARTIAL | EpisodeNotes | POST/GET/PUT/DELETE episode | AppSetting roleplay_episode:* | 1 lần JSON theo yêu cầu, source fingerprint | Cache/invalidation/inject có test | Không tự nén liên tục; tối đa cửa sổ 60 message |
| Event Graph S | PARTIAL | Episode notes | roleplay_episode.graph | JSON events/source IDs | Cạnh listed_after | Có danh sách nguồn | Không phải graph nhân quả Person–Item–Event |
| Initiative S | PARTIAL | Không đổi composer | roleplay_episode.prompt_context | Đọc recap/scene | Hook tùy chọn mỗi 4 lượt | Có ảnh hưởng prompt | Không tự nhắn khi user offline; không phải planner đầy đủ |
| Lorebook CMS S | IMPLEMENTED | admin/RoleplayLorebook.tsx | api/roleplay_lorebook; entries_for | AppSetting roleplay_lorebook:* | ACL → keyword → priority → budget → assemble | CRUD đến prompt có test | Chỉ core entry editor, không phải marketplace lore |
| Lore riêng phòng S | IMPLEMENTED | RoleplayContinuity | api/roleplay_continuity | AppSetting roleplay_continuity:* | 5 scope, unlocked, canon | Có test lọc trước retrieval | Unlock discovered do owner đặt; không phải quest engine |
| Hybrid semantic lore | NOT FOUND | Keywords có thể nhập nhiều alias | Không embedding ranker cho lore | Chưa vector index | Keyword theo ranh giới từ | Không có semantic | Chống trùng chuỗi con đã nâng cấp; không đổi tên thành semantic |
| Canon lock | PARTIAL | Canon toggle | Ranking ưu tiên canon | Lore JSON | Chỉ dẫn không ghi đè canon | Có inject | Không có validator sự thật đủ để bảo đảm output |
| Inspector/context trace | PARTIAL | Inspector | inspect, PromptTrace | PromptTrace/Memory | IDs, nguồn, char budgets | Có test riêng tư | Chưa tổng token budget cho toàn bộ prompt |
| Chọn người nói nhóm S | IMPLEMENTED | Chat nhóm; speaker mode | group_routing; JEV optional | RoomMember/Message; log meta | Mention → follow-up → relevance/fairness; decision cap 2 | Test 2/5 nhân vật, mention, timeout | Chưa xét toàn bộ scene/relationship/unresolved thread |
| Tính cách riêng từng speaker | PARTIAL | Từng message có speaker | Assemble riêng; group turn plan | Character, Message | Speaker lock, trích lời người khác | Có đường chạy thật | Chưa đánh giá tranh luận tự nhiên hay chống lẫn vai trên model thật |
| Knowledge boundary S | PARTIAL | Lore scope, memory inspector | ACL memory/lore trước prompt | Visibility/knowers | Public/private/witnessed/rumor/discovered | Lọc entry có test | Shared history cả phòng; chưa membership/witness theo từng thời điểm |
| Quan hệ user ↔ nhân vật S | PARTIAL | Relationship info | update_relationship/evaluate_state | Relationship/CharacterState/Event | Delta giới hạn + stage/expression inject | Có lưu và ảnh hưởng prompt | Regex VI/EN, familiarity tăng theo lượt; event analysis không phải evaluator hoàn chỉnh |
| Quan hệ nhân vật ↔ nhân vật S | NOT FOUND | Nhóm chat chưa có điều khiển riêng | Có cột other_character_id nhưng luồng chính lọc None | Relationship có khả năng lưu | Chưa đường cập nhật đủ | Không chứng minh | Có schema không tính là feature |
| Scene S | PARTIAL | Nhập location/time/objective | continuity.context → assemble | AppSetting | Duy trì scene đã nhập | Có test | Không tự theo dõi outfits, actor presence, ambient |
| Emotion/JEV S và assistant | PARTIAL | Key CMS/env | jev; moderation; detect_user_affect | Config key encrypted; mood logs | Classification, local fallback cho emotion | Mock contract đạt | JEV emotion bật thì background không tạo semantic recap/reflection LLM |
| Ngôn ngữ + suggestion fallback | IMPLEMENTED | UI language/suggestions | speech_language; engine fallback; JEV | UserProfile + cache ngắn | Local/JEV detect; fallback có ngôn ngữ | Có regression test | Không gọi JEV trên từng chunk output |
| TTS S | PARTIAL | Play/stream speech | services/speech; incremental_voice | MessageSpeech/Parts/Runs | Đọc cùng reply text | Cache/run thật; provider chưa nghiệm thu | Không tương đương realtime call/STT |
| BGM/biểu cảm S | PARTIAL | MusicAudio, ảnh có sẵn | Music/asset APIs | Music/ExpressionAsset | Chọn playback, emotion metadata | Code thật; không test mới browser | Không chứng minh soundscape theo scene |
| Sinh ảnh/video/comic mới | NOT FOUND | Không có pipeline mới trong scope | Worker ảnh/GPU cũ vẫn tồn tại | Asset cũ | Không thêm trong đợt này | Không tính vào nâng cấp | Giữ giới hạn không bổ sung GPU |
| Marketplace/publish cộng đồng | PARTIAL | Public user tạm ẩn | publication_review; gate env | Publication + review setting | Admin review API | Gate/review có test | Thiếu review UI; default cộng đồng tắt |
| Nhiều người thật cùng phòng | NOT FOUND | Không invite/shared composer | Room một owner | RoomMember hiện là AI character | Không | Không | Nhiều AI không phải multiplayer |
| World riêng theo user | IMPLEMENTED | AcademyApp tạo/chọn thế giới | api/ai_world | AppSetting ai_world:* owner/revision | Prompt riêng World | Owner/CAS/replay có test | Một aggregate JSON; không tối ưu nhiều server |
| Map và nhân vật W | IMPLEMENTED | Map, portrait, chuyển địa điểm | academy.positions/present/visit | Positions trong aggregate | Present lọc speaker/context | Mỗi NPC một vị trí có test | Actor đầu có thể tự theo đến phòng trống |
| Memory W | PARTIAL | Timeline/journal | observe/context | Aggregate memories/scenes | Witness → 10 memory + 12 dialogue | Có test witness | Chỉ giữ 120 observation, 60 dòng/scene; chưa dài hạn đầy đủ |
| Quest W | IMPLEMENTED | Missions/choices/map CTA | academy.advance | completed/unlocked/inventory | Backend rule, lời thoại authored | 3 quest, 2 ending có test | Chưa có thắng/thua hay procedural quest trong Academy |
| Chat tự do thúc đẩy quest W | BROKEN | Có composer cạnh task | say → direct_completion | Lưu text, không đổi mission | Context thiếu inventory/completed/current event | Hội thoại chạy nhưng không hoàn thành lời hứa gameplay | Bấm lựa chọn mới đổi state; xác nhận bằng trace code và probe |
| Secrets W | NEEDS REDESIGN | Bond panel hiện secret | secrets/projection | Điều kiện trust/completed | Chỉ inject secret mở | Gate cơ bản có test | Secret gắn index cast; đổi thứ tự đổi lịch sử; unlock chưa discovered_by |
| Quan hệ W | PARTIAL | User bond + pair labels | bond, reconcile/accuse/gift | Structured relationships | Context inject own/pair | Có delta và persistence | Chat tự do không cập nhật; hai lựa chọn đối lập có reply scripted giống nhau |
| Event/timeline W | PARTIAL | Journal + banner | event/observe | Events + timeline JSON | Authored trigger | Có lưu, reload được | Nhiều event đổi trong 1 action, banner chỉ thấy cuối; timeline bị cắt 120 |
| Return hook W | PARTIAL | Invitation/day | GET lazy sau 24h | last_seen/day | Authored, không gọi LLM offline | Test 1 lần/ngày | Không là scheduler offline; last_seen chưa cập nhật mỗi hoạt động |
| World narrator/director AI | PARTIAL | Narration + AI cast | Advance authored; say adapter | Aggregate | Nhân vật trả lời tuần tự; không director | Demo hoạt động | Không multi-agent planning/pacing engine |
| TTS/BGM W | PARTIAL | WorldMusic + đọc từng line | World speech; shared voice selection | TTS W không cache bền | Cùng text; playlist chung | Mock/isolation tests; browser cũ | Playback lại có thể gọi provider lại; không scene soundscape |
| World CMS | PARTIAL | AcademyAdmin | /v1/admin/ai-world | ai_world_config | Model/TTS/instruction/public lore | Save/isolation có test | Không chỉnh quest/secret/trigger qua CMS |
| Checkpoint/dice/Lastlight legacy | DUPLICATED | Frontend cũ đã gỡ ngày 17/10 | world_engine/chapter/lastlight, /v1/worlds | world_campaign:* | Luật cũ và adapter riêng | Test cũ tồn tại | Không cộng dồn thành khả năng Academy hiện tại |
| UI immersion W | PARTIAL | SVG landscape, transition, drawers, ending dialog | API thật | Reload progress | Không GPU | Có code và kiểm thử browser từ đợt trước | Chưa đo “biết làm gì sau 3 giây” với người dùng thật |

## Luồng đã truy vết

### Chat thường

ChatView → /v1/rooms/{id}/messages hoặc /messages/stream → owner/membership/moderation → plan_room → engine.assemble từng speaker → Memory/room lore/CMS lore/relationship/scene/recap → gateway → Message và log → extraction + BackgroundTasks → lần sau retrieve lại.

Không xem BackgroundTasks là durable queue. Background analysis hiện lấy các reply mới nhất của phòng thay vì reply gắn chính xác user message; có rủi ro ghép nhầm khi hai lượt chạy đồng thời.

### World mặc định

AcademyApp → /v1/ai-world/{id}/act → owner + revision + request_id → advance cho choice/gift/visit hoặc say adapter → ghi aggregate JSON → projection → UI. Say không đi qua engine.assemble của chat thường. Shared persona/voice/model registry không đồng nghĩa đã dùng chung memory/recap/router.

## Kiểm chứng mới

- 85 test nền đạt trước nâng cấp.
- 97 test chọn lọc đạt sau thêm 12 tình huống recall/router/lore.
- Bộ regression mở rộng cuối: **152 passed**; thêm test memory/relationship cũ chạy riêng: **1 passed**. Xem [báo cáo nâng cấp](../ROLEPLAY_RESEARCH_UPGRADE.md).
- Probe academy.context xác nhận chỉ có world/day/language/location/memories/secrets/relationships/conversation; thiếu structured quest/inventory/event.
- Probe đảo thứ tự cast xác nhận secret text thay đổi.
- Probe 130 observe xác nhận còn 120 memory/timeline; event đầu còn lại có source 10.
- Không gọi provider trả phí, không deploy, không kiểm thử full suite hoặc khẳng định chất lượng sản phẩm ngang đối thủ.
