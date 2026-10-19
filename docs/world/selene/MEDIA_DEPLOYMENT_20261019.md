# Media World — kiểm tra và deploy 19/10/2026

Đã cập nhật ứng dụng Modal đang dùng và cấu hình CMS World revision 13. Intro CMS revision 12 có 10 cue, 4 khoảng im lời; nhạc intro nhỏ dần ở cuối.

- Đã gắn 18 nền WebP, M01–M08, 7 video sự kiện, mở cổng và bốn video ending. Video phục vụ game đều là WebM; giữ file người dùng cung cấp trong thư mục `thay_the`.
- Các vùng bấm được đặt lại theo tranh. Có ánh sáng nhẹ, phản hồi hover/focus/click; vùng đã khám phá không thưởng lại. Không dùng clean plate cũ trên nền mới.
- Giữ ID, điểm, phần thưởng, puzzle và điều kiện ending. Nguyệt hoa và mảnh gương tùy chọn chuyển đến cảnh có chúng trong tranh. M04 mở đầu theo cuộc gặp trong clip mới; M08 vẫn dành cho nhánh ẩn, rồi mới đến clip kết ẩn.
- Build TypeScript/Vite qua. Các kiểm tra backend liên quan qua, gồm toàn tuyến và cả bốn ending, bỏ qua video, clip chỉ phát đúng chương và không nhận thưởng lặp.
- Kiểm tra trình duyệt: 60 lượt cảnh desktop/mobile, 122 vùng bấm bằng chuột và bàn phím. Báo cáo và ảnh ở `artifacts/selene-replacements/browser/`.
- Kiểm tra live: health OK; file media khớp local; audio chương VI/EN đủ 496/496, không thiếu. Báo cáo tại `artifacts/world-hub/cms-verify-media.json`.

Không còn thiếu clip chính trong danh sách đã yêu cầu. Các hình có thể bổ sung sau được ghi ở [NARRATIVE_MEDIA_PENDING.md](NARRATIVE_MEDIA_PENDING.md).

Các lượt chơi đang lưu vẫn giữ snapshot nội dung của chúng; bản CMS mới áp dụng cho lượt mới và preview theo revision mới, không reset tiến trình người chơi.
