# Social state machine

## Quyền của user

Chỉ chọn ai kết nối với ai. Không chọn AWARE/MET/RELATIONSHIP, điểm số hay quan hệ yêu/ghét/gia đình. Kết nối không tự tạo phòng. Cuộc gặp chỉ bắt đầu khi user tạo phòng nhóm theo luồng cũ và các nhân vật thực sự tham gia.

## Tiến triển

UNKNOWN — không có bản ghi
↓ user xác nhận giới thiệu/khớp tên
AWARE — biết tên/vai trò, chưa có cuộc gặp được ghi nhận
↓ hai AI có câu trả lời hoàn tất cho cùng một tin user trong cùng phòng nhóm
MET — đã có lần tương tác có nguồn
↓ ít nhất 3 lượt chung khác nhau
RELATIONSHIP — có lịch sử xã hội; không đồng nghĩa bạn bè hay tình yêu

Trạng thái được tính từ bản ghi, không nhận từ client. Mỗi receipt chỉ tính một lần cho mỗi cặp/lượt. Chỉ số có hướng; A → B có thể khác B → A. Nhãn được tính theo ngưỡng deterministic.

## Ngoại lệ canon đáng tin cậy

Bối cảnh do tác giả/hệ thống chuẩn bị có thể xác lập quan hệ nền trước diễn biến động. Lưu riêng, origin AUTHORED_CANON. Không tạo timestamp gặp hay trích dẫn giả. Không có giao diện/API user viết social canon trong V1.

## Không tạo tiến triển giả

- Tạo phòng, greeting có sẵn, một AI trả lời, reply dở dang/lỗi: không thành MET.
- Mention mơ hồ: không tự nối.
- Retry receipt: không tăng lượt/điểm.
- Nguồn bị sửa/xóa: không dùng lại trích dẫn cũ; lịch sử đếm không tự biến thành lời kể mới.
- API lỗi: không có sợi nối thành công.
- Ngắt kết nối: active=false; không quên/xóa lịch sử.
- Kết nối lại: giữ mức quen biết, không bắt đầu lại từ số không.

Xem ARCHITECTURE.md để biết giới hạn evaluator V1 và quyền riêng tư.
