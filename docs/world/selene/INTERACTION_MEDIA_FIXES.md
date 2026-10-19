# Moonfall: sửa tương tác và media — 18/10/2026

## Trải nghiệm
- Enter gửi, Shift+Enter xuống dòng, không gửi khi đang nhập IME; chặn gửi trùng.
- Tin đang gửi hiển thị ngay cùng ba dấu chấm; lỗi gửi giữ bản nháp.
- Chat tự do dùng model World đã chọn trong CMS, nhận persona Selene, cảnh, mục tiêu,
  tên/vị trí các item đang nhìn thấy và dữ kiện đã khám phá. Không nhận đáp án/bí mật chưa mở.
- Không tự chèn câu gợi ý có sẵn sau mỗi câu trả lời của LLM.
- Item đã xem không phát lại lời thoại/giọng. Câu thoại và thought soạn sẵn trùng được lọc;
  câu trùng trong bản lưu cũ được ẩn khỏi trình chiếu, không xóa dữ liệu.
- Bỏ khung vuông của hotspot; vẫn giữ tên item và viền focus cho bàn phím.
- Không có nút Tiếp tục ký ức. Video hết/bỏ qua/lỗi gửi cùng một action backend
  finish_memory_cinematic, kiểm tra phase, ghi kết quả và trao ký ức một lần.
- Trong memory clip chỉ đọc lời dẫn đầu đoạn, không phát hàng đợi giọng nhân vật.
  Selene phản hồi sau clip. Bỏ qua dừng/huỷ audio ngay.
- Narration ngắn lấy từ kịch bản hiện có. Tốc độ phát điều chỉnh tối đa 1.35 lần theo
  thời lượng video; video kết thúc dừng lời dẫn ngay. Cần nghe lại với voice thật trong CMS.
- Tải trọn clip thành Blob trước khi phát, chuẩn bị trước clip của chương đang khám phá.
  Chưa benchmark dropped frames trên thiết bị/mạng thực của người dùng.
- Quay lại chat hoạt động cả với admin preview, nhưng preview không được ghi ký ức
  hay lời chào thử nghiệm vào chat thường. Tổng kết không khóa nút quay lại.
- Lỗi tạo lời chào sau chương không chặn điều hướng; ký ức đã lưu vẫn dùng được.

## Ảnh
Dùng built-in imagegen để tách nền và loại logo; giữ nguyên file nguồn.
10 ảnh nhân vật: image/worlds/selene/moonfall/characters/cutouts/*.png
4 item mới: image/worlds/selene/moonfall/props/cutouts/*.png
Các item cũ đã có alpha tiếp tục dùng. Elven Council là tranh cảnh, không phải
một item có đường viền riêng; giữ nguyên tranh gốc đó.

Bộ prompt chỉnh ảnh đã dùng:
- Nhân vật: background-extraction; remove white background to real transparent alpha;
  preserve face, expression, pose, hair, clothing, jewelry and intentional magical effects;
  crop only the lower strip containing Meta AI logo; no new art/text/background.
- Item: background-extraction; extract whole item silhouette, including internal holes and
  torn edges; remove black background and Meta AI logo; preserve shape, details, colors,
  runes and soft glow; no border/frame/new symbols; no cropping of item edges.

asset_variants.py ánh xạ đúng đường dẫn nguồn đã biết sang bản tách nền.
Đường dẫn CMS tự tùy chỉnh không bị đổi. Bản lưu cũ không cần reset để nhận ảnh mới.
Projection thêm phiên bản URL cho ảnh đã xử lý để tránh cache ảnh nền trắng cũ.

## Kiểm tra
- DATABASE_URL=sqlite:// python -m pytest tests/test_memory_adventure.py tests/test_moonfall.py -q
- RUN_MOONFALL_BROWSER=1 và DATABASE_URL=sqlite://:
  python -m pytest tests/test_adventure_browser.py -q
- node --experimental-strip-types --test tests/chapter_voice_queue.test.mjs
- frontend: npm run build

Provider LLM/TTS trong kiểm thử là mock; không xác nhận chất lượng giọng thật
hoặc đảm bảo mọi thiết bị hết giật. Logic chat thường không được chỉnh trong đợt này.
