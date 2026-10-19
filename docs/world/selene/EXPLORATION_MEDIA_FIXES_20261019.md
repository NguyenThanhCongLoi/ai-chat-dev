# World: khám phá và media — 19/10/2026

## Hành vi đã sửa

- Điều kiện khám phá áp dụng cho cả 8 chương, được kiểm tra tại backend. Điểm bắt buộc phải hoàn thành theo bước; điểm tùy chọn không chặn tiến trình.
- Map đã khám phá giữ trạng thái sau khi tải lại. Các bước chung BG gộp thành một mục map và tự tiếp tục khi đủ điều kiện.
- Vào lại chương đã hoàn thành mặc định xem map, không tự phát thoại/video. Nút “Ở lại chương” xử lý được xung đột với việc lưu lời kết nền.
- Admin có nút bắt đầu lại chương đang chọn và nút chơi lại từ chương 1 ở mọi thời điểm. Chọn chương trong preview cũng bắt đầu chương đó từ đầu. Chỉ dữ liệu preview riêng được làm mới.
- Bỏ hình nhân vật phụ khỏi phần chơi.
- Chữ sân khấu chỉ lấy sự kiện kịch bản. Phản hồi chat tự do và thao tác nghe tin cũ không đổi chữ trên cảnh.
- Tên map chỉ hiện giữa cảnh 1,8 giây rồi ẩn, không có nút nghe. Các dòng tên map cũ không còn xuất hiện trong transcript.
- Dùng Rune Trăng có sẵn trên tấm trang trí ở góc dưới phải để che watermark; giữ nguyên ảnh gốc.

## Chuẩn bị tài nguyên

Manifest gồm BG, lớp xóa vật phẩm, biểu cảm, vật phẩm và video sự kiện của chương đang chơi. Giữ ảnh đã decode và URL blob để phần chơi dùng lại đúng tài nguyên đã chuẩn bị. Không khởi động loading mới chỉ vì đổi map hoặc pha ký ức. Chuyển chương, ngôn ngữ, giọng, phiên bản cấu hình hoặc lượt preview mới sẽ có phạm vi chuẩn bị tương ứng.

Không tải cả 8 chương vào trang chủ. Khi chuẩn bị có lỗi, giao diện có nút thử lại; không báo sẵn sàng giả. Chế độ xem lại ưu tiên ảnh, không tự tải/phát video.

## Kiểm tra

- Backend: điều kiện 8 chương, tiếp tục save, map gộp, xem lại im lặng, quyền preview, manifest tải trước.
- Trình duyệt: ở lại chương sau xung đột revision, ảnh blob, chuyển map không request media thêm, tên map tự ẩn không nút nghe.
- Frontend: scope preload ổn định, decode/cache ảnh, chữ sân khấu tách khỏi chat.

## Các map sau khi gộp

| Chương | Map | Các bước |
|---|---|---|
| 1 | Cổng cổ | ancient_gate |
| 1 | Con đường bị bỏ quên | side_path, ward_aftermath |
| 1 | Tàn tích ngoài | outer_ruins |
| 2 | Tàn tích trong | inner_ruins |
| 2 | Vườn nguyệt hoa | moonflower_garden, echo_archway |
| 2 | Kho lưu trữ cổ | archive |
| 3 | Cầu thang dưới học viện | descent, quiet_landing |
| 3 | Căn phòng ngầm | chamber, seal_trap |
| 4 | Moonbrook được tái dựng | reconstruction |
| 4 | Moonbrook trong ký ức | past |
| 4 | Hành lang sụp đổ | collapse_passage, quiet_landing |
| 5 | Kho lưu trữ cổ | records, archive_defense |
| 5 | Ngôi nhà bên rừng | forest_threshold, witch_house |
| 6 | Hầm sâu | vault |
| 6 | Hành lang gương | mirror_hall |
| 6 | Hành lang ký ức | clock_landing, corridor |
| 7 | Đền Trăng | temple, temple_boundary |
| 7 | Phòng Trăng Nhợt | manifestation, pale_chamber |
| 8 | Không gian ký ức | memory_space |
| 8 | Lời nhắn trong chiếc vòng | pendant_echo |
| 8 | Căn phòng cuối | decision_threshold, final_chamber |
