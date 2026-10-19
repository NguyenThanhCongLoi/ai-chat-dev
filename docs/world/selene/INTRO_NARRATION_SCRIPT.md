# Intro World Mode — lời dẫn đã căn theo clip mới

Bản biên tập dựa trên lời người dùng gửi ngày 18/10/2026. Giữ ý chính, rút gọn để vừa clip 93,708 giây cùng bốn khoảng im lời. Không sử dụng nguyên timeline dài hơn clip.

Video: `image/worlds/hub/video/selene_intro_20261018_from17.webm`. Lấy từ giây 17 đến hết nguồn `image/video/intro.mp4`; nhạc MP3 cùng thư mục thay audio nguồn, nhỏ dần trong 4 giây cuối.

Các mốc sau tính từ đầu bản đã cắt. Phụ đề có bảy ngôn ngữ, TTS chuẩn bị trước bằng giọng VI/EN đang chọn trong CMS.

## Khoảng im lời

- **7.5–18.5 giây:** Hai người bị hút qua màn hình. Không lời đọc hoặc phụ đề; nhạc trở về mức không duck.
- **18.5–23.5 giây:** Fantasy world đầu tiên mở ra. Không lời đọc hoặc phụ đề; nhạc trở về mức không duck.
- **77.5–83.5 giây:** Đỉnh nhạc montage nhiều thế giới. Không lời đọc hoặc phụ đề; nhạc trở về mức không duck.
- **87.3–89.8 giây:** Nghỉ 2,5 giây trước lời chào World Mode. Không lời đọc hoặc phụ đề; nhạc trở về mức không duck.

## Lời đọc chính thức

### 0–7.5 giây · `intro_door`

Có những cánh cửa không dẫn đến một nơi... mà dẫn đến cả một thế giới.

### 23.5–32 giây · `intro_journey`

Bước qua cánh cửa ấy, bạn trở thành một phần trong hành trình của họ. Những nhân vật có câu chuyện, ký ức và bí mật riêng.

### 32–39.5 giây · `intro_memories`

Qua những vùng đất bị lãng quên, theo dấu ký ức còn sót lại... cùng họ tìm những điều ngay cả chính họ cũng chưa thể nhớ ra.

### 39.5–47.5 giây · `intro_everyday`

Nhưng không phải thế giới nào cũng có phép thuật. Đôi khi, câu chuyện bắt đầu giữa thành phố không ngủ... hay trong một văn phòng trên cao.

### 47.5–54 giây · `intro_encounter`

Hay chỉ từ một lần tình cờ gặp nhau ở hành lang trường học. Mỗi nhân vật... lại mở ra một hành trình mới.

### 54–63 giây · `intro_connections`

Phiêu lưu. Bí ẩn. Tình bạn. Tình cảm. Một bí mật trong ký ức, hay một người đang đợi cuối đường... mỗi cuộc gặp đều có thể đổi hướng câu chuyện.

### 63–70.5 giây · `intro_characters`

Ở đây, nhân vật không chỉ tồn tại để trò chuyện. Họ có quá khứ, có điều muốn tìm lại... và những lựa chọn cần bạn cùng đưa ra.

### 70.5–77.5 giây · `intro_choices`

Bạn không chỉ là người xem. Bạn cùng họ viết tiếp câu chuyện. Đôi khi... chỉ một lựa chọn cũng thay đổi cách nó kết thúc.

### 83.5–87.3 giây · `intro_return`

Rời thế giới ấy, câu chuyện vẫn ở lại cùng bạn.

### 89.8–93.6 giây · `intro_welcome`

Chào mừng đến với World Mode. Nơi mỗi nhân vật... mở ra một thế giới.

## Chuẩn bị và áp dụng

- CMS nguồn mới hiển thị cả mốc im lời, mức nhạc/duck/voice và nút kiểm tra độ dài file đã tạo. Mốc thoại lấn khoảng im lời hoặc vượt clip bị từ chối.
- Audio cố định dùng cache theo nội dung, model và giọng. Lúc vào chương chỉ tải file đã có; thiếu file trả trạng thái chưa chuẩn bị, không gọi TTS tại lượt chơi.
- Công cụ chuẩn bị riêng trong CMS bao gồm M08 và mọi kết thúc. Danh sách dành cho người chơi vẫn chỉ có những audio được phép ở nhánh hiện tại.
- Source sẽ nâng bản intro cũ chưa sửa sang script mới khi dùng bản video mới; giữ mức âm lượng và bật/tắt từ CMS. Script CMS đã sửa riêng không bị ghi đè.
- Công cụ `scripts/world_cms_audio_remote.py --operation stage-intro` và `stage-chapters` tạo audio vào volume hiện có bằng giọng/model CMS, không deploy ứng dụng hay thay tiến trình người chơi. Kết quả đo ở `artifacts/world-hub/cms-stage-intro.json`.
- Timeline mới chỉ hoạt động trên website sau khi triển khai source/video mới. Chưa ghi đè intro đang chạy trên website bằng timeline của video khác.
