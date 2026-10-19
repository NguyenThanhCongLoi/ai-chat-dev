# Rà soát thoại và clip — 19/10/2026

Thoại và clip sự kiện dùng cùng một hàng đợi. Clip chỉ bắt đầu sau khi lời báo trước kết thúc; câu phản ứng không xuất hiện trong transcript, phụ đề hoặc phát tiếng cho tới khi clip kết thúc/bỏ qua. Một lần bấm có thể có một câu trước và một câu sau clip. Rời World hủy chuỗi đang chờ.

| Chương | Trước clip | Clip | Sau clip |
|---|---|---|---|
| 1 | “Đừng nhúc nhích.” | Bẫy tên, Selene dùng phép | Lời dẫn kết quả, rồi “Tôi không nghĩ… Tôi chỉ biết mình phải làm vậy.” tự phát, không cần bấm mũi tên |
| 2 | “Chờ đã!” | Bóng cô gái chạy qua vòm | Lời dẫn bóng đã tan; dấu cánh hoa vẫn là điểm điều tra tiếp theo |
| 3 | “Lùi lại, ra ngoài đường rune!” | Bẫy xiềng phong ấn | Lời dẫn về xiềng; thao tác phiến đá vẫn là bước chơi riêng. Clip giải phong ấn sau puzzle diễn ra trước “Là tôi. Nhưng đừng để một đáp án trở thành cả bản án.” |
| 4 | “Đi sát tôi!” | Học viện sụp | Lời dẫn vượt qua trần sập; hướng chạy ngược dòng là manh mối tiếp theo |
| 5 | Bấm giấy buộc tội | Kho thức dậy, giấy và bóng phù thủy | Lời dẫn rồi “Một từ được viết đủ nhiều lần không tự biến thành sự thật.” |
| 6 | “Đừng nhìn nó như tôi.” | Phản chiếu lệch nhịp, gương vỡ | Lời dẫn phản chiếu; kiểm tra mép gương vẫn là bước riêng. Clip cửa vault sau puzzle diễn ra trước câu nhận xét về phần ký ức được giữ lại |
| 7 | Bấm mảnh ký ức hội tụ | Vầng Trăng Nhợt hình thành/tách ra | Lời dẫn rồi “Nó không muốn tôi nhớ. Nó muốn được hoàn chỉnh.” tự phát. Clip bàn thờ sau puzzle diễn ra trước câu Selene giải thích cách ngăn hình thể hoàn chỉnh |
| 8 | Xác nhận lựa chọn | Restore / Release / Transfer đúng nhánh | Thoại kết tương ứng chỉ phát sau clip. Nhánh ẩn: M08 mái nhà → phản ứng hiện tại → clip Hidden, không trộn với ba ending thường |

M01–M08: phần dẫn mở đầu/caption thuộc cảnh đang xem; phần thoại phản ứng được nhận từ `finish_memory_cinematic` sau khi video kết thúc/bỏ qua. Mở cổng chương 1 vẫn là một clip riêng trước M01. Không thêm điểm, vật phẩm, điều kiện puzzle hoặc ending.

Các lượt đang lưu được cập nhật riêng thứ tự event trong cấu hình; giữ phase, vật phẩm, điểm và tiến trình. Lịch sử đã xem không tự phát lại.

## Lỗi chuẩn bị media 99% sau mở cổng

Đã tìm thấy câu dẫn quay lại cảnh “Dư âm vòng phép” bị thêm vào danh sách audio bắt buộc tải trước, dù CMS chỉ chuẩn bị các câu kịch bản cố định. Đã chuẩn bị cache còn thiếu cho lượt đang kẹt, giữ nguyên revision 24/phase memory. Planner mới không đưa các nhãn quay lại cảnh và lời gợi ý phát sinh vào gói cố định, nên gói không tăng bất ngờ khi chuyển từ cổng sang M01.

Kiểm tra: hàng đợi trước/clip/sau, hoàn tất/bỏ qua/lỗi clip, giấu câu sau clip, tắt tự đọc, rời World; bảy chuỗi thực tế qua React trên Edge; đoạn mở cổng → M01 → kết chương → chương 2; kiểm tra tiến trình và bốn ending trên backend.
