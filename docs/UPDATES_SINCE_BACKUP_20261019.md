# Cập nhật bản phát triển — 19/10/2026

## Mốc đối chiếu

- Code nền trước đợt phát triển: commit 4b874ae, “Prepare standalone CPU service
  with Tarot and CMS updates; preserve GPU workers”.
- Backup dữ liệu được người dùng nhắc tới: handoff-20261012-153034-cms.zip,
  thư mục trích xuất handoff-20261012-153034/character_chat.sqlite.
- Backup là SQLite/CMS, không phải snapshot source. Vì vậy không thể tuyên bố
  đây là diff source chính xác với backup. Báo cáo này mô tả thay đổi source
  sau commit nền và đối chiếu phạm vi bàn giao dữ liệu.
- Repo đích: NguyenThanhCongLoi/ai-chat-dev; nhánh xuất bản: main.
- Không đính kèm database, backup, credentials hoặc dữ liệu người dùng.

## 1. Chat Roleplay thông thường

- Thêm quản lý lorebook qua CMS: gán nhân vật, từ khóa, độ ưu tiên,
  scope, canon và trạng thái bật/tắt. Chỉ đưa kiến thức phù hợp vào context.
- Bổ sung continuity, ghi nhớ thủ công, truy hồi ký ức và ghi chú hội thoại.
  Giữ ranh giới user/phòng/nhân vật; không tự chia sẻ private lore sang nhân vật khác.
- Bổ sung trạng thái quan hệ và cách xưng hô theo mức thân quen, giữ cá tính
  nhân vật và tôn trọng cách xưng hô user yêu cầu.
- Liên kết giữa các nhân vật là dữ liệu riêng theo user; tương tác chỉ bắt đầu
  khi user tạo phòng chung.
- Điều chỉnh danh mục nhân vật để tránh lặp; có cơ chế đăng ký/duyệt nhân vật public.
- Xóa phòng xử lý thêm dữ liệu phát sinh theo phạm vi user, giữ card/prompt/lore CMS.
- Trở về từ World phát lời gần nhất phù hợp, tránh đọc lại lời chào cũ.
- Prompt chung và nội dung mẫu CMS được tách thành tài liệu điền rõ từng trường.

## 2. JEV / TypeSafe

- Adapter quyết định qua API, key từ env hoặc credential store CMS.
- Moderation nhiều nhóm nội dung, routing một hoặc nhiều người trả lời trong nhóm,
  cảm xúc, sự kiện quan hệ và nhận diện ngôn ngữ.
- Assistant thường và streaming nhận tín hiệu cảm xúc; ngôn ngữ hỗ trợ gợi ý dự phòng.
- Cache hữu hạn, timeout và kiểm tra schema; không gọi trên từng token stream.
- Không thay LLM viết thoại hoặc TTS; không yêu cầu GPU.
- Hướng dẫn tích hợp riêng, không kéo World sang bản SSH: docs/JEV_SERVER_HANDOFF.md.

## 3. World Selene — Echoes of Moonfall

- Hành trình tám chương, khám phá theo điều kiện, câu đố, vật phẩm, các lựa chọn
  dẫn tới ba kết thường và một kết ẩn.
- Tiến độ, vật phẩm, manh mối và kết truyện được lưu có cấu trúc.
  Video là lớp trình bày: bỏ qua/lỗi video không tự quyết định phần thưởng.
- Nhạc nền dùng chung với chat; intro có lời dẫn/phụ đề và âm lượng.
- Tách lời dẫn, lời nhân vật, suy nghĩ và sự kiện hệ thống.
  Lời dẫn trong chương không tự đọc; nút nghe ở transcript.
- Giọng nhân vật dùng cấu hình chat; giọng dẫn riêng qua CMS, có danh sách voice.
- Chuẩn bị và lưu cố định audio VI/EN; đổi nội dung/voice/provider mới tạo lại.
  Ngôn ngữ không hỗ trợ TTS không hiện nút nghe trong chương.
- Chờ tài nguyên theo từng phần/chương, ảnh mèo và phần trăm cho World,
  giải thích thiếu audio hoặc media; tái dùng tài nguyên đã tải.
- Điểm bấm không hiện viền vùng, có đốm sáng cho manh mối thường.
  Manh mối kết ẩn không có đốm chỉ dẫn.
- Map cùng BG được gộp; các bước tương tác vẫn tuần tự và lưu sau reload.
- Kết chương có trục thư, nội dung riêng và nút về chat.
  Cầu nối ký ức chỉ chia sẻ thông tin có cấu trúc được cho phép.
- Xem lại chương đã hoàn thành không tự phát lại thoại/video; lượt chơi mới
  giữ bộ sưu tập kết nhưng đặt lại tiến trình theo quy tắc.
- Admin mặc định preview riêng: nhảy chương, chơi lại và xem trực tiếp bốn kết,
  không cộng chỉ số hay xuất ký ức vào chat thường.

## 4. Sửa gần nhất

- Sửa loading kẹt 99% khi audio chưa chuẩn bị hoặc manifest trỏ BG đã mất.
- Dùng bộ BG và video chính thức; bỏ các cinematic prototype không phù hợp.
- Chương 4: hành lang chưa sập → click trần → video sập → nền hậu cảnh đã sập.
- Đặt lại tinh thể/phiến đá trên sàn, thu nhỏ và chỉnh tone; bỏ lớp props nổi
  không hợp BG ở chương 4 và Hành lang ký ức chương 6.
- Sửa BG kết ẩn từng bị phủ lên mọi map chương 8. Ba địa điểm giữ BG riêng.
- Admin có mục “Xem thử kết truyện”, bao gồm kết ẩn, phát lại nhiều lần.
- Dọn 1.172 file cũ/cache/preview/script lỗi thời, khoảng 254,65 MiB.
  Giữ tài nguyên chính thức và các alias còn cần cho cấu hình cũ.

## 5. CMS và đa ngôn ngữ

CMS có cấu hình World, chương, nội dung, model, voice dẫn, voice bổ sung,
chuẩn bị audio, nhạc và lorebook chat. Các phần mới theo bảy ngôn ngữ UI:
VI, EN, JA, ZH, KO, MY, KM; riêng hỗ trợ TTS thực tế theo provider/cấu hình.
Không khẳng định mọi bản dịch đã qua biên tập viên bản ngữ.

## 6. Kiểm thử và giới hạn

Các lượt kiểm tra gần nhất:
- Đợt dọn: 121 kiểm thử đạt, build và kiểm tra World trên Edge đạt.
- Bố cục chương 4/hành lang: 53 kiểm thử đạt và kiểm tra trình duyệt.
- Admin preview: kiểm tra bốn kết, quyền admin/chủ sở hữu, idempotency và phát lại.
- BG chương 8: 14 kiểm thử đạt.
- Build nghiêm ngặt: 728 chuỗi UI × 6 bản dịch, cộng nguồn tiếng Việt.
- Modal đã được deploy trong phiên; repo không tự mang theo secrets/volume Modal.

Không phải báo cáo “toàn bộ suite luôn xanh”: một số test lịch sử có thể còn
giả định gameplay/asset cũ. Live provider, chất lượng voice, quyền tài khoản
production và dữ liệu khôi phục cần nghiệm thu trong môi trường đích.

## 7. Khi clone sang máy/server mới

- Điền env theo .env.example hoặc deploy/service.env.example.
- Không dùng Git thay cho backup dữ liệu. Restore DB/media upload riêng.
- Giữ DOCS_PASSWORD đúng nếu cần giải mã credentials CMS từ backup cũ.
- Media chính thức được đưa cùng source; cache giọng đã sinh, DB và nhạc có
  giấy phép không được đưa lên GitHub. Cần bàn giao riêng hoặc chuẩn bị lại.
- Chức năng GPU giữ kiến trúc/cấu hình riêng hiện có; đợt này không chuyển GPU
  sang server CPU mới.
- Xem docs/SELF_HOSTED_DEPLOYMENT.md, docs/ENV_HANDOFF.md và
  docs/world/selene/ADMIN_CMS.md trước khi vận hành.
