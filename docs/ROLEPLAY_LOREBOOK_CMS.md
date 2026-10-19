# CMS Lorebook — chat Roleplay thường

## Mở ở đâu?

CMS chính → **Lorebook · Chat thường**, hoặc **Nhân vật → Lorebook** cạnh nhân vật cần sửa.

URL: /roleplay/lorebook/admin. Không phụ thuộc WORLD_DEMO_ENABLED.
Xác thực: tài khoản admin HTTP Basic của CMS hiện có; đăng nhập user thường không đủ quyền.

## Tạo một mục

1. Bấm Thêm lore.
2. Điền tiêu đề và nội dung (150/1500 ký tự).
3. Gán ít nhất một nhân vật, tối đa 50.
4. Chọn phạm vi:
   - Chung: mọi nhân vật được gán có thể biết.
   - Riêng: chỉ một nhân vật trong nhóm được gán biết.
   - Người biết: chỉ các nhân vật được đánh dấu biết.
   - Tin đồn: thông tin chưa xác minh, không được đánh dấu canon.
5. Điền tối đa 12 từ khóa/tên gọi khác, hoặc chọn luôn đưa vào.
6. Chọn ưu tiên 0–10; bật/tắt và lưu.

Ví dụ: tiêu đề “Tháp phía bắc”; nội dung “Selene thường nghiên cứu các bản đồ sao trong thư phòng ở tháp phía bắc.”; gán nhân vật Selene; từ khóa “tháp phía bắc, north tower, bản đồ sao”; canon nếu đây là dữ kiện gốc đã chốt.

## Hiệu lực

Áp dụng khi backend chuẩn bị lượt chat tiếp theo, không viết lại tin nhắn cũ. Cập nhật/tắt/xóa không cần tạo lại phòng hoặc deploy lại code. Lượt đang xử lý có thể đã chụp context trước lúc admin lưu.

CMS không sửa prompt tính cách hay lore phòng do user viết. User không có API sửa lore gốc này. Hai nguồn được lọc, xếp hạng chung trong ngân sách 4500 ký tự. Canon → ưu tiên → mức khớp từ khóa; không nhét mọi mục vào mọi lượt. Canon là hướng dẫn giữ nhất quán, không phải bảo đảm LLM luôn đúng. Khi mâu thuẫn, prompt yêu cầu hỏi lại thay vì âm thầm sửa sự thật.

## Nhân vật và phạm vi

- Gán theo ID, không đoán bằng tên hoặc avatar.
- Nhân vật hệ thống: preset:<type>; bản dùng trong phòng được nhận diện từ nguồn preset.
- Nhân vật lưu trong DB: character:<id>.
- Bản sao nhân vật public kế thừa qua character_clone_source khi nguồn còn public, tối đa 8 liên kết.
- Custom card có preset_type nhưng creation_type custom không được giả làm preset.
- Bản sao cũ không có liên kết nguồn đáng tin cậy cần admin gán trực tiếp; không dùng suy đoán tên/ảnh.
- “Riêng” là riêng theo nhân vật/nguồn được gán, không phải bí mật của một user. Thông tin riêng của user phải ở memory/lore phòng.

## Bảo mật và lưu trữ

- Kiểm quyền admin; validate trường, recipients, từ khóa, boolean và canon/tin đồn.
- Chạy kiểm duyệt nội dung hiện có; nếu JEV moderation bật thì dùng JEV. Không thêm model/GPU mới.
- CAS revision chống ghi đè khi hai người sửa; khi 409 cần tải và chọn lại mục mới nhất.
- AppSetting roleplay_lorebook:<uuid> lưu từng mục; audit chỉ lưu ID/action/revision/thời gian tại roleplay_lorebook_audit:<uuid>.
- Không ghi dữ liệu World, CharacterSpec, Room, Message, Memory hay Relationship.
- Lọc identity/recipients trước relevance; prompt chỉ nhận mục được phép, không nhận toàn bộ kho.
- Chưa có trình unlock bí mật CMS theo nhiệm vụ hoặc giao diện nhóm nhiều lorebook. Bí mật mở theo tiến trình riêng vẫn dùng lore trong phòng.
- Giới hạn demo 1000 mục; storage hiện quét namespace rồi lọc, chưa phải thiết kế truy vấn tối ưu cho kho rất lớn.

## API và code

GET/POST /v1/admin/roleplay-lorebook; PUT/DELETE /v1/admin/roleplay-lorebook/{id}, DELETE yêu cầu revision query.
Frontend: frontend/src/admin/RoleplayLorebook.tsx.
Backend: character_chat/api/roleplay_lorebook.py.
Runtime retrieval: character_chat/roleplay_lorebook.py → roleplay_continuity.context → engine.assemble.

## Kiểm tra

tests/test_roleplay_lorebook.py bao gồm quyền admin, hiệu lực prompt, room-lore không bị sửa, private ACL, update/disable/delete, stale revision, preset/public clone, spoofing, moderation failure, context budget và độc lập World.

Kết quả kiểm tra 16/10/2026: 47 tests chọn lọc đạt (lorebook, continuity, API contract và World isolation). Build frontend đạt. Edge với DB riêng kiểm tra tạo/gán/private recipient/lưu/reload/tắt/xóa và lối vào CMS khi World bị tắt. Ảnh: artifacts/roleplay-lorebook/27f67af7/cms.png. Chưa deploy hoặc gọi provider thật.
