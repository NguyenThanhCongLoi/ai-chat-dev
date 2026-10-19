# Ranh giới World và chat thường

## Trải nghiệm

World là module riêng. Chat thường giữ giao diện, cách gửi tin, bộ nhớ, prompt, quan hệ và luồng voice hiện có. Đổi hoặc xóa một World không sửa phòng chat thường. Không tự chuyển cơ chế nhiệm vụ, bản đồ hay lựa chọn của World sang chat thường.

## Dùng chung có chủ đích

- Tài khoản và kiểm tra quyền hiện có.
- ID nhân vật, tính cách/prompt gốc, ảnh và cấu hình giọng gốc; World chỉ đọc qua catalog.
- Registry model/provider và credentials: dùng lại kết nối API, không sao chép key sang frontend.
- SQLAlchemy/database và cơ chế backup chung. Dữ liệu World nằm ở namespace riêng, không phải database vật lý riêng.
- Chính sách kiểm duyệt chung.

Sửa nhân vật gốc, ảnh, giọng hoặc provider/key dùng chung ở CMS chính có thể tác động cả hai nơi. Đây là tài nguyên chung có chủ đích; lưu CMS World không sửa chúng.

## Tách riêng

| Thành phần | World | Chat thường |
|---|---|---|
| Lịch sử | scenes bên trong ai_world:<id> | Room / Message hiện có |
| Memory | memories có witnesses trong ai_world:<id> | Memory / reflection / continuity hiện có |
| Quan hệ | relationships trong ai_world:<id> | Relationship / events hiện có |
| Lore / nhiệm vụ / vật phẩm | World-only | Context chat thường hiện có |
| Prompt định hướng | ai_world_config.instruction | ADMIN_RESPONSE_INSTRUCTION hiện có |
| Phân công model | ai_world_config.model_id / tts_model_id | Phân công CMS hiện có |

World dùng baseline an toàn tĩnh và persona gốc, không lấy editable ADMIN_RESPONSE_INSTRUCTION của chat thường. CMS World chỉ ghi ai_world_config. Nếu để model trống, World kế thừa phân công provider/model hiện có; chọn riêng trong CMS World nếu muốn phân công độc lập. Sửa bản ghi provider/credentials dùng chung vẫn áp dụng cho mọi bên sử dụng bản ghi đó.

## Bộ nhớ không tự đồng bộ

Không có luồng tự đọc ký ức chat riêng vào Academy, cũng không tự ghi sự kiện World thành ký ức chat thường. Cùng database và cùng kiểu kỹ thuật lưu trữ không có nghĩa dùng chung nội dung ký ức.

Hiện World dùng bộ nhớ theo người chứng kiến và context giới hạn dung lượng; chưa tự kế thừa toàn bộ pipeline retrieval/reflection của chat thường. Import/export ký ức có xác nhận, kiểm phạm vi và gắn nguồn là bước phát triển riêng, chưa có trong demo Academy.

## CMS riêng

- Trang: /worlds/admin (xác thực admin HTTP Basic hiện có).
- API GET/PUT: /v1/admin/ai-world.
- Điều chỉnh: model chat World, model TTS World, chỉ dẫn hội thoại, lore công khai.
- Áp dụng từ lượt World tiếp theo.
- Bí mật có điều kiện/nhiệm vụ vẫn thuộc engine demo, chưa có trình biên tập đầy đủ.
- Lore công khai chỉ chứa điều mọi nhân vật được biết; bí mật chưa mở không được đưa vào đó.
- Không cho user thường truy cập chỉ vì đã đăng nhập.

## Giới hạn cách ly

Đã tách dữ liệu và cấu hình theo phạm vi ứng dụng. Chưa cách ly CPU/RAM, database connections, quota provider hay tiến trình máy chủ. Tải World lớn vẫn có thể ảnh hưởng độ trễ chung. Cách ly vận hành tuyệt đối cần worker/quota/tài nguyên riêng, không thể cam kết từ namespace.

## Kiểm tra

tests/test_ai_world.py đối chiếu mọi bảng SQLAlchemy ngoài namespace World trước/sau lưu CMS, điều tra, tặng quà, hội thoại và xóa World; kiểm prompt World không nhận prompt CMS chat thường, model assignment thường không bị sửa và ký ức/phòng chat riêng không được đưa vào context World. Có kiểm quyền admin, CAS và contract API gốc.
