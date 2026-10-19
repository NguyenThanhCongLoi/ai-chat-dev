# Điền gì để trải nghiệm Moonfall Academy tốt?

## 1. Những mục cần có

| Nơi cấu hình | Điền/chọn gì | Tác dụng |
|---|---|---|
| CMS chính → Cấu hình AI / Kết nối | API base và API key hợp lệ của provider | Backend gọi model; không đặt key trong prompt/lore hoặc frontend |
| CMS chính → Cấu hình AI | Một model hội thoại đã bật, hỗ trợ chat/completions | Dùng cho đối thoại tự do |
| CMS World /worlds/admin → Model hội thoại World | Chọn rõ model chat trên | Phân công World riêng; không thay phân công chat thường |
| CMS World → Chỉ dẫn hội thoại World | Đoạn tiếng Anh trong MOONFALL_CMS_COPY.md, mục thứ nhất | Nhân vật giữ tính cách, nói gọn, biết đúng phạm vi, không tự trao thưởng |
| CMS World → Lore công khai | Đoạn tiếng Anh trong MOONFALL_CMS_COPY.md, mục thứ hai | Bối cảnh chung và 5 địa điểm; không chứa đáp án hoặc bí mật |
| Kết nối kiểm duyệt | JEV/TypeSafe key đã lưu ở CMS hoặc JEV_API_KEY của backend | Free-text và phản hồi World phải qua kiểm duyệt |
| Kho nhân vật | Chọn 4 nhân vật có tính cách và cách nói khác nhau khi bắt đầu World | Cảnh nhóm tự nhiên hơn; tối thiểu 2 vẫn chơi được |

Nếu chưa dùng JEV, strict World moderation cũng hỗ trợ WORLD_MODERATION_API_KEY hoặc OPENAI_API_KEY với WORLD_MODERATION_API_BASE nếu cần. Không cần cấu hình đồng thời cả hai nhà kiểm duyệt. Không có credential moderation thì hội thoại tự do bị chặn; các lựa chọn demo vẫn chơi được.

**Giữ prompt nhân vật gốc. Không nhét nhiệm vụ hoặc đáp án Moonfall vào prompt nhân vật dùng chung**, vì prompt gốc được dùng cả trong chat thường và World.

## 2. Để có voice

1. CMS chính: model TTS đã bật, purpose “Phát giọng nói TTS” (tts), API base/key đúng provider.
2. CMS World: chọn model đó tại Model voice World; để trống sẽ dùng phân công TTS hiện có.
3. CMS Nhân vật: kiểm tra Voice ID và tài khoản/provider tương ứng.
4. Nếu giọng chia theo ngôn ngữ, chọn đúng VI/EN. Không dùng Voice ID của provider khác.
5. Trong cảnh, bấm Nghe một câu để xác nhận. Chưa có kiểm chứng voice thật bằng credentials production trong phiên phát triển này.

Replay World hiện gọi TTS lại, chưa có cache audio persistent của MessageSpeech như chat thường.

## 3. Nhạc nền — đã nối chung

- Kho nhạc: CMS chính → Nhạc nền.
- Chọn ít nhất một bài, hoặc upload nhạc trong CMS rồi Lưu thiết lập.
- World gọi đúng playlist /v1/roleplay/background-music, gồm nhạc gốc và nhạc upload đang được chọn trong CMS.
- Nhạc gốc ngoài DB cần ROLEPLAY_MUSIC_DIR trỏ đúng thư mục khi chuyển server; nhạc đã upload nằm trong DB backup.
- Khi mở World, bấm Bật nhạc nền ở thanh trên; không tự phát khi mới tải.
- Gợi ý âm lượng World ban đầu 20–30%, nhạc ít lời cho cảnh hội thoại.
- Playlist phát tiếp/lặp, tránh lặp bài vừa phát nếu có nhiều bài.
- Khi voice phát, gain nhạc giảm còn 25% mức đang chọn rồi khôi phục khi voice dừng.
- Khi ẩn tab hoặc rời World trong AIBox, nhạc dừng.
- Âm lượng World lưu riêng ở world_background_music_volume; không ghi đè roleplay_background_music_volume của chat thường.
- Chọn/xóa bài trong CMS Nhạc nền là thay đổi kho dùng chung, nên có hiệu lực cho cả chat thường và World sau khi tải lại playlist.
- Đây là playlist chung, chưa tự chọn ambience theo địa điểm.

## 4. Ảnh và cá tính nhân vật

Dùng ảnh đã có trong CMS Nhân vật; nếu thiếu ảnh thì hiện chữ đầu tên. Không cần tạo ảnh/video hoặc cài GPU. Chọn bốn nhân vật theo sắc thái khác nhau, chẳng hạn điềm tĩnh / tò mò / thực tế / dí dỏm, nhưng không sửa họ thành cùng một kiểu học sinh để khớp bối cảnh.

## 5. Không cần điền thêm cho demo hiện tại

Nhiệm vụ, bí mật có điều kiện, vật phẩm, mở khóa và kết chương đã có trong backend. Không ghi chúng vào lore công khai. Không cần tạo Redis, vector database, model embedding hay agent chạy liên tục để chơi demo này.

CMS **Lorebook · Chat thường** là kho kiến thức gốc cho chat thường. Không tự động được nhập vào Academy; CMS World có ô lore riêng.

## 6. Nghiệm thu nhanh

1. Mở World và chọn 4 nhân vật.
2. Bật nhạc, kéo âm lượng; chuyển cảnh xem nhạc vẫn chạy.
3. Vào thư viện, chat một câu và gọi tên một nhân vật.
4. Bấm Nghe, kiểm tra voice đúng và nhạc nhỏ lại.
5. Tìm thư → nghe nhân chứng → tới vườn → lên đài thiên văn.
6. Đọc kết chương; tải lại để kiểm tra tiến trình còn.
7. Quay sang Trợ lý AI/chat thường: nhạc World phải dừng, ký ức và lore phòng cũ vẫn riêng.

## 7. Để thấy bản code mới trên Modal

Build/redeploy theo quy trình hiện có; thay đổi local không tự lên Modal. Sau khi bản mới đã deploy, việc lưu prompt/lore/model trong CMS áp dụng cho lượt kế tiếp, không cần deploy lại cho mỗi lần sửa nội dung.
