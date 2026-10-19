> Cập nhật tiếp ngày 16/10/2026: đã có recap AI theo yêu cầu, góc nhìn riêng, chuỗi sự kiện có nguồn và initiative theo luật. Xem [bản cập nhật episode](ROLEPLAY_EPISODE_UPDATE.md); trạng thái bên dưới mô tả bản trước.

# Chat Bot AI thường — nâng cấp theo báo cáo Roleplay

Ngày 16/10/2026. Các tính năng dưới đây nằm ngay trong phòng chat thường, không cần vào Worlds.

## 1. Trải nghiệm mặc định

- Chat như trước. Không cần khai báo scene, lore hoặc mở editor để bắt đầu.
- Mỗi tin nhắn đã lưu có nút Ghim: một lần để nhớ, bấm lại để bỏ ghim. API dùng định danh ổn định để tránh tạo bản ghi trùng khi gửi lại.
- Mở Ký ức & cốt truyện khi muốn kiểm soát. Ba mục chính: Ký ức, Bối cảnh, Nhật ký.
- Ký ức hiển thị để đọc; chọn Sửa mới hiện ô nhập. Ghim/bỏ ghim và xem nguồn nằm cạnh nội dung.
- Cài đặt tự ghi nhớ, ngân sách context và giải thích kỹ thuật nằm trong Tùy chọn ghi nhớ.
- Bối cảnh có địa điểm, thời điểm và mục tiêu. Lore & bí mật nằm trong Nâng cao; keyword/alias và canon cũng thu gọn.
- Nhật ký gom mốc quan hệ và trích đoạn hội thoại. Không tạo sự kiện giả nếu chưa có dữ liệu.

Áp dụng hướng kiểm soát ký ức và lore trong tài liệu nghiên cứu, không sao chép giao diện hoặc source của nền tảng khác.

## 2. Các nâng cấp ảnh hưởng trực tiếp tới câu trả lời

### Memory Inspector / Memory Control

Xem memory riêng của nhân vật, chung phòng và USER_GLOBAL đúng phạm vi. Có nguồn tin nhắn, confidence, ghim, sửa, xóa. Phân biệt:
- Dự kiến được chọn: truy hồi theo tin user gần nhất, chưa phải cam kết model đã sử dụng.
- Đã dùng ở lượt trước: ID có trong PromptTrace; không có nghĩa model đã tuân theo hoàn hảo.

Memory được chọn tối đa 12 ứng viên; payload thực tế giới hạn 3200 ký tự JSON. Ký ức ghim được ưu tiên theo retrieval hiện có. Không cắt giữa entry; trace chỉ ghi các entry thực sự đưa vào prompt. Đây không phải giới hạn token chính xác.

Nút ghim tin nhắn lưu trích dẫn có người nói và source ID; dài thì lấy tối đa 1000 ký tự. Tin của AI có confidence thấp hơn tin user, không được xem lời AI là sự thật đã xác minh. Chat một người lưu CHARACTER_PRIVATE; nhóm mặc định ROOM_SHARED. Bỏ ghim không xóa memory; muốn xóa dùng bảng ký ức.

### Scene State

Scene của phòng lưu location/time/objective, đưa vào assemble ở lượt tiếp theo. Chưa tự suy diễn địa điểm mới từ mọi câu chat hoặc tự đánh dấu mục tiêu hoàn thành. Không thay persona/cách nói của character card.

### Lorebook + Knowledge Boundary

Entry có title/text, keyword/alias, priority, canon, always và scope:
- public: mọi AI trong phòng biết, không phải public Internet.
- private: đúng một thành viên.
- witnessed: danh sách thành viên được biết.
- rumor: tin đồn; không được đánh dấu canon.
- discovered: chưa đưa vào prompt đến khi người dùng bật Đã khám phá.

Lọc scope trước khi match từ khóa; chuẩn hóa chữ hoa/thường, dấu tiếng Việt và đ/ d, quét query + 4 tin gần nhất. Giới hạn payload lore 4500 ký tự; ưu tiên canon/priority/relevance. Chưa có vector model, entity graph hoặc recursion. Nội dung được đánh dấu reference data, không được nâng thành system instruction.

Giới hạn: lịch sử nhóm vốn được chia sẻ cho các thành viên. Nếu một bí mật đã nói ra trong lịch sử chung, đặt lore private sau đó không thể khiến nhân vật quên đoạn chat ấy. Đây là boundary cho lore/memory có scope, chưa phải cơ chế gán audience cho từng tin nhắn hay mô phỏng ai có mặt từng thời điểm.

### Canon Lock

Prompt yêu cầu giữ canon, coi rumor chưa xác minh và hỏi lại nếu có mâu thuẫn. Không tuyên bố đây là bảo đảm hình thức rằng LLM không thể nói sai. Canon không được vượt qua kiểm duyệt hoặc thay persona.

### Relationship Timeline

Hiện tối đa 50 RelationshipEvent của nhân vật trong phòng, có nguồn, confidence và deltas nếu đã lưu. Dữ liệu đến từ pipeline phân tích quan hệ hiện có; không có event khi pipeline chưa ghi thành công. Confidence là tín hiệu ước lượng, không phải cảm xúc thật của AI.

### Nhật ký phiên

Tối đa 10 trích đoạn gần đây có người nói, có tải TXT riêng. Chưa phải recap trừu tượng do AI sinh, chưa có episode library hoặc tự pin recap.

## 3. Quyền và persistence

- Mọi endpoint kiểm tra room ownership, actor phải là RoomMember cho inspect/timeline.
- Không trả full system prompt hoặc API credentials.
- Source quote chỉ trả khi nguồn thuộc room của chính user; tham chiếu sai sang user khác bị ẩn.
- Config private room lưu AppSetting roleplay_continuity:<room_id>, có revision/CAS và trả 409 khi sửa từ bản cũ.
- Xóa room dọn config. Xóa character dọn recipients và bỏ lore private/witnessed không còn người nhận.
- Tắt use_memory ngừng đưa Memory và private reflections vào prompt; lịch sử chat, quan hệ, scene/lore vẫn giữ.
- Tắt auto_memory ngừng trích xuất memory bằng heuristic và ghi memory/reflection mới từ background analysis. Phân tích mood/quan hệ hiện có vẫn chạy; không đồng nghĩa tắt toàn bộ background calls.
- Chưa tách theo nhiều persona của cùng user.
- Không ALTER schema, không tải weights, không thêm inference GPU.
- Quy trình chỉnh lore/memory sử dụng guard nội dung hiện có; chưa mở publication của lore phòng ra Internet.

## 4. Module

- character_chat/roleplay_continuity.py: scope/relevance/budget/config.
- character_chat/api/roleplay_continuity.py: CRUD, inspector, timeline, excerpts và message pin.
- character_chat/engine.py: đưa scene/lore/memory vào prompt và metadata trace.
- background.py và services/roleplay_context.py: tôn trọng lựa chọn auto_memory.
- frontend/src/roleplay/RoleplayContinuity.tsx: bảng ba mục và nâng cao.
- frontend/src/roleplay/RememberMessage.tsx: pin/unpin trực tiếp, một request trạng thái dùng chung cho cả phòng.
- frontend/src/locales/: bổ sung nhãn cho sáu ngôn ngữ ngoài VI. Build xác nhận catalog đầy đủ; chưa có nghiệm thu dịch thuật bởi người bản ngữ.

## 5. Phạm vi đối chiếu 17 ý tưởng

Đã nâng trực tiếp cho chat thường trong đợt này: 11.1 memory inspector/control; 11.2 timeline dữ liệu quan hệ; 11.4 scene thủ công; 11.5 boundary lore/memory; 11.9 canon prompt. 11.7 có bước nền là nhật ký trích đoạn, chưa phải recap AI.

Chưa triển khai mới: 11.3 graph; 11.6 initiative planner; 11.8 checkpoint cho chat thường; 11.10 dynamic cast; 11.12 multi-agent director; 11.15 persona scopes; 11.16 marketplace; 11.17 cộng tác nhiều người thật. 11.11 router và 11.14 nhạc/SFX giữ chức năng đã có. Không triển khai sinh media GPU theo yêu cầu loại trừ.

## 6. Chạy

Deploy app chính bằng python -m modal deploy modal_app.py. Bản CPU selfhost cũng nhận tính năng vì không phụ thuộc Modal. Chưa tự deploy hay push từ phiên sửa này.


## 7. Kiểm chứng và giới hạn

- TypeScript/Vite build đạt. Catalog 612 chuỗi có bản dịch ở sáu ngôn ngữ ngoài VI.
- Bộ hồi quy 91 kiểm tra đạt (prompt/language, group, transport, selfhost, reset cảm xúc, background analysis và continuity); sau khi thêm thao tác pin, 14 kiểm tra continuity/API contract đạt.
- Edge desktop: mở phòng từ sidebar chính; ghim tin nhắn; đọc memory/source; lưu scene; tạo private canon cho một thành viên; mở timeline/journal; tắt use_memory; reload xác nhận persistence.
- Dữ liệu browser test hoàn toàn riêng. Dịch giới thiệu nhân vật được mock; không gọi model/provider thật.
- Screenshot: artifacts/roleplay-continuity/fe4ebf5a/memory.png.
- Test background cũ được sửa fixture để tạo Room thực sự, phù hợp điều kiện consent theo phòng; không nới kiểm tra ownership để cho phép room mồ côi.
- Chưa nghiệm thu chất lượng câu trả lời với provider thật, tải nhiều người, hay triển khai Modal từ phiên này.

### Endpoint mới

GET/PUT /v1/roleplay/rooms/{room_id}/continuity
GET /v1/roleplay/rooms/{room_id}/pins
POST /v1/roleplay/rooms/{room_id}/remember
GET /v1/roleplay/rooms/{room_id}/inspect?character_id=...
GET /v1/roleplay/rooms/{room_id}/timeline?character_id=...
GET /v1/roleplay/rooms/{room_id}/recap

Config có revision để chống ghi đè; pin dùng ID xác định từ user/message/actor, tránh bản ghi trùng. Marker ghim chỉ cho các trích dẫn được ghim bằng tính năng này; ghim một memory trừu tượng trong inspector vẫn là thao tác riêng.
