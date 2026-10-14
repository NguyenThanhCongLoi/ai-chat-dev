# Tarot và Tử vi

Bấm mục Tarot & Tử vi để mở màn chọn hai lá úp rồi lật, có nhãn Tarot/Tử vi. Chọn một lá, lá còn lại thu nhỏ và biến mất trước khi mở phòng. Màn chọn hỗ trợ bàn phím, Escape, focus trap và reduced motion.

Tarot dùng đủ78ảnh WebP từ ZIP người dùng cung cấp. Runtime dùng image/tarot_tuvi/cards; các file .tmp không được lấy. Hai ảnh chọn chế độ là tarot.jpg và tu_vi.jpg. character_chat/tarot_deck.json giữ catalog cố định.

Backend shuffle78lá bằng SystemRandom mỗi trải mới, rút không hoàn lại và chọn ngược/xuôi50% từng lá. Mặc định3lá, một lá cho hôm nay, hỗ trợ yêu cầu sốlá1–10. Câu giải thích Tarot chung không bắt buộc rút; follow-up dùng cùng trải đã lưu; yêu cầu rút mới tạo reading_id mới. Không có thuật toán dự đoán vận mệnh.

Kết quả thực nằm trong Message.sources với kind=tarot, reading_id và cards; không cần đổi schema. Event SSE tarot đến trước text; client lật từng lá, hiển thị tên và chiều. Ảnh ngược quay180°. History tải lại đúng kết quả. AI phải diễn giải các lá server cấp, không tự đổi/rút thêm; chất lượng tuân thủ vẫn phụ thuộc model.

Tử vi/Bát Tự là purpose assistant_tuvi riêng, không drawTarot. Chỉ diễn giải dữ liệu hoặc lá số cung cấp; cần bổ sung thông tin sinh khi thiếu, không giả lập phép tính lá số chính xác.

CMS → Trợ lý AI có Tarot và Tử vi & Bát Tự riêng. Mỗi mục có model chính, hai fallback và prompt từngslot. Phân công Tarot cũ được sao chép sang purposeTử vi một lần để dùng được ngay; sau đó quyền CMS quyết định. Hai mode có history riêng, mỗi mode giữ cơ chế một phòng như Assistant hiện có. Chat Tarot cũ vẫn assistant_tarot.

Các nội dung chỉ để chiêm nghiệm; không khẳng định tương lai hoặc thay tư vấn chuyên môn. Nhãn tên lá theo tài nguyên gốc (English), UI lựa chọn/trạng thái theo locale.

Build UI và deploy backend/image cùng nhau. Chưa tự deploy hoặc push trong tác vụ này.

## Lượt rút và làm mới
Bộ78lá được tráo khi bắt đầu/reset; rút tiếp tiêu thụ bộ còn lại, không trùng trong lượt. Hỏi tiếp giữ cùng trải. Hiển thị số lá còn lại. Nút Làm mới lượt rút xác nhận trước khi xóa messages của phòng Tarot, tạo session mới78lá; không xóa phòng Tử vi, uploads, memory thủ công hoặc cấu hình CMS. Kết quả model muộn sau reset bị bỏ. Khi không đủ lá trả409 và yêu cầu reset. State lưu AppSetting tarot_session:<room>; không cần migrationschema.

## Xác minh ngày 14/10/2026
- Build strict TypeScript/Vite đạt; 546 chuỗi × 6 locale.
- 9 test divination/API contract/startup và 13 regression Assistant đạt.
- Edge headless với account/DB giả: chọn hai chế độ, ảnh thực, lật, orientation, mobile, reset đạt; không có pageerror.
- Chưa gọi LLM thật hoặc triển khai production. Việc model diễn giải đúng ý nghĩa cần test trên model được CMS phân công.


## Sửa CMS, lịch sử và theme (14/10/2026)

Client lấy trường giao diện CMS qua /v1/assistant/profiles sau đăng nhập, khi quay lại tab và mỗi 30 giây khi tab hiển thị. Endpoint chỉ trả trường giao diện; prompt và credentials ở backend. Prompt mới áp dụng cho lượt gửi tiếp theo, không viết lại tin nhắn cũ.

Tarot/Tử vi có thể tạo phòng mới bằng nút “Hỏi chủ đề mới”; lịch sử hiển thị mọi phòng của mục đó. Backend nhận new_session: true cho hai chế độ này; mặc định vẫn mở phòng gần nhất. Mỗi phòng Tarot có bộ bài riêng. Làm mới lượt rút chỉ xóa lịch sử phòng hiện tại.

Nền huyền bí tối chỉ nằm ở màn chọn hai lá. Chat giữ theme người dùng. Chuyển trợ lý hoặc mở phòng đóng màn chọn và hủy timer hiệu ứng khi unmount.
