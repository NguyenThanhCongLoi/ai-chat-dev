# State machine

Chat riêng đủ điều kiện → eligible → user chủ động vào World → intro chưa xem → intro_complete → overview → outer_ruins → discover clue → gate mở khi đủ điều kiện → 2/3 clue → completed → memory reveal → optional explicit sync → normal chat.

Tạo World không tự tăng điểm chat. Mở khóa không dựa vào số tin nhắn thô: cần câu đủ nội dung, không gần trùng và có phản hồi hoàn tất. Các ngưỡng trong CMS; test có thể đặt bằng 0.

Mỗi lượt giữ snapshot nội dung/config_revision. Sửa story không retcon lượt đang chơi; model/voice vận hành đọc cấu hình hiện tại. GET không chạy inference.

Act yêu cầu revision và request_id. CAS chống ghi đè; request_id trong receipt được trả lại, không cộng tiến triển hai lần. Clue đã có không tăng trust nữa. Có giới hạn 500 act/lượt demo.

Các flag ở unlock_condition là điều kiện server kiểm. Không có script tùy ý trong CMS.
