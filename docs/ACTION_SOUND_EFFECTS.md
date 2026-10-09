# Âm hành động trong Role Play

## Luồng hiện tại
- Thư viện từ sound_effect (chỉ WAV/MP3/OGG), cộng file admin upload lưu trong DB.
- Sound thích hợp trong ZIP được giải nén vào sound_effect/library trên ổ D. ZIP không đưa vào image deploy.
- Trang Role Play tải sẵn thư viện và decode vào AudioBuffer. Trước khi mở phòng, làm mới metadata CMS và chuẩn bị sound đang bật; file đã có giữ lại theo URL/version.
- Mỗi delta chuyển vào detector tại client. Nhận đủ từ trong hành động *…*, **…**, ***…*** là phát ngay, không cần chờ dấu đóng hoặc câu trả lời hoàn tất.
- Nút tắt âm phản ứng tắt cả clip phản ứng và sound hành động, dừng ngay sound đang phát.
- Kiểm tra thêm bản trả lời cuối nếu stream chưa phát được; chỉ tiêu một sound được tính khi audio thực sự bắt đầu.
- Chỉ xử lý câu trả lời đang stream. Không phát khi đọc lại lịch sử hay trước câu chào.
- SFX dùng AudioContext riêng, không gọi stop của clip phản ứng/TTS/nhạc nền. Các luồng được trộn bởi trình duyệt.
- Bản đầu dùng rule, không gọi LLM riêng, không cài ML/GPU.
- Không thể nhận diện hành động chưa được LLM sinh. Nếu hành động nằm cuối, sound phát lúc nhận được hành động; không dự đoán trước.
- Tải sound lỗi không chặn câu trả lời; bỏ qua file lỗi. Trình duyệt cần cho phép audio sau tương tác người dùng.
- Mỗi câu trả lời chỉ phát một sound hành động. Không phát chồng sound hành động; mỗi sound tối đa 3 giây, giảm âm ở cuối để tránh cắt gắt.

## CMS → Âm hành động
- Âm lượng tổng nhân với âm lượng từng sound.
- Mỗi dòng từ khóa là một lựa chọn; dấu + yêu cầu tất cả từ xuất hiện trong cùng câu hành động.
- Ví dụ: đặt+bút+xuống, quạ+kêu, lật+trang, put+pen+down, 翻页.
- Có sẵn rule Việt/Anh và một số rule Trung/Nhật/Hàn. Các ngôn ngữ hoặc cách diễn đạt khác cần admin thêm từ khóa; không cam kết hiểu mọi biến thể ngữ nghĩa.
- Bỏ dấu chọn để tắt sound gói sẵn. File upload có thể xoá.
- Sound mới upload mặc định tắt, cần thêm từ khóa rồi bật và lưu.
- Nhiều sound có cùng từ khóa được nhóm thành biến thể, chọn ngẫu nhiên và tránh lặp ngay file vừa phát.
- tap.wav là tiếng chạm dùng làm sound đặt bút, có thể tắt và thay bằng file đặt bút chuyên biệt.
- Các sound người như thở/cười vẫn dùng bộ clip giọng clone hiện có.

## Deploy
Deploy lại modal_app.py để đưa backend, frontend và thư viện sound vào ứng dụng. Không cần deploy worker GPU phản ứng cho tính năng này. Dữ liệu CMS/upload được lưu trong DB volume hiện có.

## Kiểm thử
- python -m pytest tests/test_action_sounds.py -q
- Trong frontend: node --test scripts/action-sounds.test.cjs
- npm.cmd run build


## Short playback files
Bundled PCM WAV files are served as cached excerpts of at most three seconds.
WAV uploads use the same length limit; MP3/OGG are decoded and retained as short
buffers in the browser. Approved files up to 20 MB are accepted for playback;
the previous 5 MB / 30 second preload filter no longer silently skips pencil sounds.
File URLs include a new clip version to invalidate previous browser downloads.

Only audible actions with configured keywords trigger a sound. For example,
"puts the pen down" matches a pen tap; "fingers pause on the pen" does not.
Action detection currently uses narration inside asterisks. Plain dialogue is
not scanned. Custom CMS keywords remain authoritative and are preserved.
