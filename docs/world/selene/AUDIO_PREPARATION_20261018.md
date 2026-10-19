# Chuẩn bị audio World — 18/10/2026

CMS được đối chiếu: `https://nguyenthanhcongloi332004--character-chat-web.modal.run/admin`.

## Kết quả tạo thật

Audio đã lưu trên volume `character-chat-data`, dùng model và giọng đã cấu hình trong CMS; không dùng audio giả hoặc đổi sang TTS ngoài cấu hình.

| Phần | Tiếng Việt | Tiếng Anh |
|---|---|---|
| Intro World Mode mới | 10/10 | 10/10 |
| Chương 1 | 31/31 | 31/31 |
| Chương 2 | 29/29 | 29/29 |
| Chương 3 | 30/30 | 30/30 |
| Chương 4 | 29/29 | 29/29 |
| Chương 5 | 31/31 | 31/31 |
| Chương 6 | 32/32 | 32/32 |
| Chương 7 | 29/29 | 29/29 |
| Chương 8, gồm mọi ending | 37/37 | 37/37 |

Tổng kế hoạch: 20 đoạn intro và 496 đoạn thoại chương. Đây là số mục trong kế hoạch theo chương/ngôn ngữ; cache có thể dùng chung file cho nội dung trùng nhau.

## Đối chiếu intro

- 10 đoạn VI và 10 đoạn EN đã được đo thời lượng bằng FFmpeg. Tất cả nằm vừa khung phát, kể cả khi cần tăng tốc nhẹ; không đoạn nào cần vượt 1,25 lần.
- Bốn khoảng im lời: 7,5–18,5; 18,5–23,5; 77,5–83,5; 87,3–89,8 giây.
- Khoảng nghỉ trước “Chào mừng đến với World Mode” là 2,5 giây.
- Giọng kể intro vẫn theo giọng đã gán trong CMS. Nhạc nền dùng bản MP3 người dùng cung cấp, đã fade-out ở 4 giây cuối video.

## Sửa giọng Selene trẻ

Provider liệt kê `vi_north_female_an_nhien_healing` nhưng endpoint tạo âm thanh trả HTTP 404 “Không tìm thấy voice”. Bốn câu VI ở chương 3, 4, 6 và 8 không thể tạo với giọng đó.

Theo lựa chọn rõ ràng của người dùng, riêng giọng VI của `young_selene` đã đổi thành giọng Selene hiện tại: `selene_moonbrook`. CMS xác nhận lưu revision 11 tại thời điểm thao tác. Cả bốn câu đã tạo lại thành công. Giọng EN và các nhân vật khác được giữ nguyên.

## Source/CMS đã sửa

- CMS intro có mốc im lời và thời lượng clip; từ chối lời đọc lấn khoảng im lời hoặc vượt cuối video.
- Có kiểm tra audio đã tạo và thời lượng thực ngay trong CMS. Không gọi TTS chỉ để kiểm tra trạng thái.
- Bộ chuẩn bị của admin bao gồm M08/kết ẩn; catalog người chơi vẫn giới hạn theo nhánh đã được phép.
- Lúc tải thoại cố định của chương, thiếu cache trả HTTP 409 để chuẩn bị từ CMS; không tự gọi TTS ở lượt vào chương.
- CMS có danh sách chính xác câu còn thiếu và endpoint chuẩn bị lại từng câu.
- Nội dung intro mặc định cũ đi theo video mới khi triển khai source mới, giữ mức âm lượng/bật tắt của CMS. Kịch bản tùy chỉnh riêng không bị ghi đè.

## Kiểm tra và phạm vi đang hoạt động

Build TypeScript/Vite đạt. Các kiểm thử backend về cache, quyền truy cập, tạo từng câu, bốn khoảng im lời, nhánh ẩn và tương thích CMS cũ đã đạt; kiểm thử JavaScript về giới hạn thời lượng và hàng đợi thoại cũng đạt.

Audio thật và thay đổi giọng Selene trẻ đã được chuẩn bị/lưu trên môi trường hiện có. **Chưa deploy video, timeline và code CMS mới lên website.** Không bật timeline dành cho clip đã cắt trong khi website còn dùng video cũ. Lượt chơi/tiến trình người dùng không được tạo hoặc thay đổi bởi công việc chuẩn bị audio.

Chi tiết máy đọc được:

- `artifacts/world-hub/cms-stage-intro.json`: audio intro và thời lượng từng đoạn.
- `artifacts/world-hub/cms-stage-chapters.json`: kế hoạch audio 8 chương, không còn mục thiếu.
- `artifacts/world-hub/cms-repair-young-voice.json`: xác nhận lưu thay đổi giọng trong CMS.

Kịch bản đọc: [INTRO_NARRATION_SCRIPT.md](INTRO_NARRATION_SCRIPT.md). Danh sách video đã có: [CHAPTER_VIDEO_INVENTORY.md](CHAPTER_VIDEO_INVENTORY.md).
