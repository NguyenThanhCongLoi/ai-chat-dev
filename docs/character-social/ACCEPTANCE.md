# Nghiệm thu Character social V1

17/10/2026. Bản local, chưa push/deploy. Chốt hành vi theo phản hồi cuối: user chỉ chọn hai nhân vật, không viết quan hệ; kết nối không tự tạo phòng.

## Thử trên UI

1. Mở một phòng Roleplay **chat riêng**.
2. Bấm **Mối liên kết**, chọn nhân vật thứ hai và chạm vùng nối ở giữa.
3. Sau xác nhận API, có sợi sáng/flash/phản ứng surprised khoảng 1,2 giây. Hiện “Biết đến nhau, chưa có cuộc gặp được ghi nhận”.
4. Đóng bảng để tiếp tục chat. Nhân vật được cấp tên/vai trò đã giới thiệu, không được đọc chat/memory riêng của nhân vật kia.
5. Khi muốn gặp, user tự tạo phòng nhóm bằng luồng tạo phòng hiện có. Hai AI phải thực sự có câu trả lời hoàn tất cùng một lượt mới tính là đã gặp.
6. Sau 3 lượt chung đủ điều kiện, hệ thống duy trì lịch sử quan hệ; không mặc định yêu/thân.
7. Ngắt/nối lại không xóa knowledge hay lịch sử.

Không cần sửa prompt 11 nhân vật hoặc dán thêm social prompt vào CMS. Context này do backend tự cấp. Canon social là dữ liệu tác giả/hệ thống dự phòng; không có form/API user viết canon.

## Test tự động

- tests/test_character_social.py: **20 passed**, DB cách ly.
- Bộ hồi quy chọn lọc 13 module: **174 passed**.
- npm run build: TypeScript/Vite đạt.
- API contract gốc vẫn giữ; route mới được liệt kê riêng trong test contract.
- SQLite cũ được thử migration hai lần, giữ nguyên nội dung tin nhắn; reply_to cũ để null.

Bộ hồi quy chọn lọc gồm social, continuity, recall upgrade, lorebook, episode, group routing, JEV, AI World, Worlds, chapter, Lastlight, catalog và contract.

Chạy thêm tests/test_app.py cho thấy **48 passed / 7 failed**: sáu lỗi kiểm duyệt tạo nhân vật trả character_policy_unavailable, một lỗi expectation failed/default-icons của biểu cảm. Chưa sửa những nhánh kiểm duyệt/GPU đó. Không tuyên bố toàn bộ test suite đều xanh.

## Trình duyệt

Script: artifacts/character_social_smoke.py, Edge headless, Uvicorn thật và SQLite trong thư mục artifact mới. Chỉ tài khoản/nội dung giả; không gọi provider trả phí.

Kết quả đạt: artifacts/character-social/6829a8a9/report.json.

Đã kiểm tra:

- UNKNOWN trước giới thiệu; AWARE chỉ sau API thành công.
- Tải lại đọc đúng dữ liệu đã lưu; picker chờ danh sách liên kết, tránh hiện UNKNOWN giả khi tải chậm.
- Dùng trình tải surprised hiện có; thử nhân vật còn lại bị 404 vẫn hoàn tất bằng fallback.
- Ép API POST lỗi 503: không có connection trong DB hoặc sợi nối thành công.
- Ngắt liên kết giữ knowledge.
- Màn hình 390 px và prefers-reduced-motion: không chạy hoạt ảnh di chuyển, trạng thái vẫn đọc được.
- Không có ô viết quan hệ hoặc nút tự mở phòng.
- Sau kết nối vẫn chỉ có phòng riêng ban đầu.
- Không có lỗi JavaScript trong lượt kiểm thử đạt.

Ảnh:

- [Desktop](../../artifacts/character-social/6829a8a9/connected-desktop.png)
- [Lỗi API](../../artifacts/character-social/6829a8a9/failure.png)
- [Mobile / reduced motion](../../artifacts/character-social/6829a8a9/reduced-motion-mobile.png)
- [Chat riêng sau khi đóng](../../artifacts/character-social/6829a8a9/ordinary-chat.png)

Một số lần chạy trước chưa đạt do selector, chờ networkidle khi tải nhạc, điều hướng iframe của bài test, và lỗi chọn trước khi tải xong danh sách. Lỗi tải danh sách đã sửa; lượt đạt kiểm tra lại reload. UI social được nghiệm thu bằng URL workspace trực tiếp /role-play-ai?workspace=1&room=...; không coi đó là kiểm chứng toàn bộ luồng điều hướng của platform.

## Giới hạn trước production

Evaluator chỉ nhận tín hiệu đơn giản, rõ ràng Anh/Việt; không phân tích mọi ngữ nghĩa hay tự tạo crush/ghen/quan hệ gia đình. Một số bản dịch UI chưa đủ, fallback Anh. Build vẫn cảnh báo bundle lớn.

Chưa kiểm thử provider thật hoặc tải production. Context được lọc và có chỉ dẫn chống bịa quan hệ, nhưng không thể chứng minh LLM tuyệt đối không hallucinate. Xem [kiến trúc](ARCHITECTURE.md) và [state machine](STATE_MACHINE.md).
