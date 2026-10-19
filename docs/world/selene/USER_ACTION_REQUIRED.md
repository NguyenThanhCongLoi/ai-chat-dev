# Những gì bạn cần cung cấp

## ACTION 1
Asset/API: Nhân vật Selene từ backup/kho hệ thống hiện tại.
Why: World dùng đúng cá tính, ảnh, giọng đã có; không tạo bản Selene giả.
Required: CÓ nếu môi trường mới chưa có Selene.
Specification: Card Selene Moonbrook và giọng hiện có.
How to create: Khôi phục backup hoặc gán card hiện có trong CMS → World.
Destination: CMS nhân vật / World → Nhân vật Selene.
Fallback: World báo cần cấu hình, chat khác vẫn hoạt động.

## ACTION 2
Asset/API: Model chat + moderation/JEV hiện có.
Why: Hội thoại tự do cần provider và kiểm duyệt.
Required: CÓ cho free chat, KHÔNG cho các nút khám phá đã viết sẵn.
Specification: Model được bật; API key ở kết nối/model/env.
How to create: Gán model trong CMS; tái sử dụng credentials sẵn có.
Destination: CMS → World → Model hội thoại.
Fallback: Không lưu lượt lỗi; vẫn khám phá và xem gợi ý được.

## ACTION 3
Asset/API: Narrator Voice ID VI/EN và provider TTS.
Why: Giọng kể tách khỏi giọng Selene.
Required: CÓ để nghe người kể, KHÔNG để chơi bằng text.
Specification: Hai ID theo ngôn ngữ, khác ID Selene; provider có quyền sử dụng giọng.
How to create: Lấy ID từ tài khoản TTS của bạn; không gửi key qua chat.
Destination: /worlds/admin → Thế giới & giọng nói.
Fallback: Im lặng + phụ đề; không lấy giọng Selene thay thế.

## Visual assets đã hoàn tất

Đã tích hợp 14 background, 10 props, 8 video WebM và 9 biểu cảm Selene nền trong suốt. Không cần tạo thêm ảnh/video placeholder. File gốc được giữ; runtime dùng WebP/WebM. Xem ASSET_MAPPING.md để đối chiếu toàn bộ đường dẫn.

Âm thanh còn thiếu là 6 ambient và 11 SFX tùy chọn. BGM dùng chung playlist của chat thường; không cần sao chép. Thiếu audio không chặn Chương 1.

## Chạy và nghiệm thu

Xem ACCEPTANCE.md, mục 8. Bật WORLD_DEMO_ENABLED=true trong đúng môi trường chạy. /worlds/admin quản lý story, narrator VI/EN và assets; giọng Selene vẫn sửa ở CMS nhân vật/chat thường.

Nếu đã có cấu hình CMS/lượt chơi cũ, không tự ghi đè: cấu hình và tiến trình có snapshot. Đối chiếu manifest mới trước khi áp dụng cho người/lượt chơi mới.
