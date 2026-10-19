# Demo Worlds: Thị trấn đánh mất bình minh

Ngày 16/10/2026. Demo mới có ID lastlight; không ghi đè tiến trình Moonfall đã lưu.

## Ý tưởng và cách chơi

Bạn tỉnh dậy khi mọi đồng hồ chỉ sáu giờ nhưng trời không sáng. Hồi chuông thứ mười ba sẽ xóa tên thị trấn.
Cốt truyện dần hé lộ: không ai trộm bình minh; những người sống ở đây từng cùng chọn quên một đêm đau buồn.

1. Chọn 1–3 nhân vật từ kho chung. Họ là NPC trong chuyến đi; người dẫn truyện là vai riêng.
2. Bấm gặp NPC, nghe và nhận lời nhờ giúp.
3. Đi đến nơi có câu đố. Chọn đáp án bằng nút, hoặc xin mẹo theo ba mức.
4. Nhận cổ vật qua màn lật thẻ, mang về đúng NPC để trao và nhận lại bản đã phục hồi.
5. Hoàn thành ba lời nhờ giúp, tới Đài Sao Cũ và lưu mốc.
6. Chọn cổ vật trong túi, chọn NPC nhận, đọc trước hệ quả rồi xác nhận.
7. Hồi kết hiện thành trang truyện; có nút đóng và đọc lại. Mốc đã lưu cho phép chơi nhánh khác.

Các NPC nhận nhiệm vụ theo số người chọn: một người nhận cả ba, hai người chia 2/1, ba người mỗi người một nhiệm vụ.
Giới hạn 1–3 hiện có vẫn giữ; chưa hỗ trợ cast lớn hơn.

## Ba cổ vật

- Chìa Khóa Bình Minh: mở bình minh nhưng người cứu thị trấn bị quên — kết thúc đánh đổi.
- Gương Gọi Tên: đối diện ký ức, gọi lại tên nhau — kết thúc thắng.
- Chuông Không Tiếng: mở chuyến tàu đưa con người rời thị trấn — kết thúc đánh đổi.
- Trả lời sai câu đố ba lần: kết thúc thất bại. Không có timer thật; đọc/chờ/chat không làm thua.
- Xin mẹo không tốn lượt và không tăng lỗi. Mỗi câu đố có ba mức mẹo; mức cuối nói rõ đáp án.

Ba vật phẩm cố định, không gacha. Hai giai đoạn raw → ready; trao cuối cùng chuyển thành spent.
Backend xác thực địa điểm, NPC, thứ tự nhiệm vụ, đáp án, số lỗi và vật phẩm. Chat tự do không tự cấp thưởng.
Trao lặp lại hoặc đưa sai người không nhân đôi/tiêu hao vật phẩm.

## Nhân vật và trò chuyện

Có thể chat với narrator hoặc tới gặp NPC. Ở đài sao cuối truyện, các NPC cùng hiện diện.
Narrator có model/prompt riêng trong CMS Worlds; persona NPC lấy từ nhân vật được chọn.
Khi chưa cấu hình model, các nút hành động vẫn chơi được bằng nội dung soạn sẵn. Lời thoại rules chưa mô phỏng đầy đủ cá tính.
Chat tự gõ cần kiểm duyệt. Model chỉ kể/đối thoại; không tự kiểm đáp án hoặc sửa luật.
Prompt mẫu đã cập nhật ở docs/world/LEGACY_WORLD_NARRATOR.txt (tài liệu lịch sử, không còn import vào frontend), điền ở CMS của lastlight; không tự thay prompt đã lưu.

## UI và dữ liệu

- Giao diện truyện, hàng gặp NPC, câu đố, túi ba thẻ cổ vật và trang kết.
- Hiệu ứng lật/hiện cổ vật bằng CSS, không cần GPU/model ảnh/video. Có reduced motion.
- VI/EN theo phạm vi Worlds hiện tại. Đây chưa phải bản dịch đầy đủ 7 ngôn ngữ cho truyện.
- Lưu tự động mỗi action, CAS revision, request receipts chống lặp; quyền user và checkpoint giữ cơ chế cũ.
- Catalog mặc định hiện demo mới; journeys cũ vẫn mở bằng luật cũ.
- Tạm ẩn nút tạo world để tập trung demo. Chưa có editor tạo puzzle/đổi vật/ending cho user; backend drafts cũ giữ nguyên.

## Kiểm tra

- Engine: các nhóm 1/2/3 NPC, VI/EN, cả ba kết thúc, thua, mẹo, trao lặp/sai, quyền phòng và receipts.
- Edge với DB riêng: ba câu đố, mẹo, ba lần phục hồi, hiệu ứng thẻ, checkpoint, đọc/đóng/mở lại kết thúc.
- Chưa kiểm thử narrator provider thật hoặc deploy Modal.

# Sửa stream Roleplay chậm giữa các chunk

Phát hiện đường gọi speech_info → sentence_segments → detect_speech_language → detect_message_language.
Sau integration JEV, detect_message_language mặc định cho phép gọi mạng. Vì speech_info chạy mỗi delta trên văn bản dài dần, cache không tránh được request mới cho từng prefix.

Đã sửa detect_speech_language dùng use_jev=False. Các chunk đầu ra và TTS metadata chỉ nhận diện local; JEV tiếp tục nhận diện câu user.
Đồng thời kiểm tra ngôn ngữ bản dịch UI và user history dùng local để tránh request ngoài phạm vi.
Có regression test test_output_speech_metadata_never_calls_jev_while_streaming.
Không đổi tốc độ provider hoặc thêm delay/typewriter; chưa benchmark production nên không đưa ra số tăng tốc.
Cần deploy backend mới để sửa có hiệu lực trên Modal.

Kết quả cuối: 126 tests trong bộ world/episode/JEV/speech/transport/API được chọn đều đạt. Frontend build đạt, còn cảnh báo bundle app lớn. Chưa đo tốc độ provider production.



## Cập nhật: mỗi NPC có phòng riêng

- Có một phòng Người dẫn truyện và một phòng cho mỗi NPC đã chọn.
- Chuyển phòng bằng hàng tab; trong phòng NPC có nút Về người dẫn truyện.
- Lịch sử lưu riêng theo phòng trong adventure.rooms; active_room được lưu cùng chuyến đi.
- Chuyển phòng không thêm tin nhắn giả, không tăng lượt hoặc lỗi, không gọi model.
- Bản nháp giữ riêng theo phòng trong phiên đang mở; reload không giữ bản nháp chưa gửi.
- Quest, địa điểm, vật phẩm và kết thúc dùng chung. Có thể quay lại NPC để giao lưu hoặc xin mẹo.
- Nhận nhiệm vụ/trao cổ vật đưa hội thoại vào phòng người giao; khám phá/giải đố đi qua phòng dẫn truyện.
- Ở NPC, dùng model Roleplay đã phân công và prompt trả lời Roleplay hiện có; narrator ưu tiên model riêng trong CMS Worlds.
- Snapshot persona gồm system_prompt, personality, speech, identity, values, boundaries, goals và sample_dialogues.
- Context chỉ có lịch sử của phòng đang nói, tiến độ chung và ký ức mang theo đúng phạm vi; không tự đọc phòng NPC khác.
- Lưu cũ chuyển lịch sử chung vào phòng narrator; không đoán lại người nhận cho từng đoạn cũ.
- Phòng thuộc chuyến đi; không ghi trạng thái game vào lịch sử chat Roleplay thường.
- Khi chưa cấu hình model/credentials, fallback soạn sẵn vẫn hoạt động nhưng chưa thể hiện đầy đủ cá tính nhân vật.
- Phiên bản hiện giữ tối đa 80 entries/phòng; chưa có pagination lưu toàn bộ cuộc trò chuyện dài.

Xác minh bản phòng riêng: 106 tests liên quan đạt; Edge qua chuyển phòng, lịch sử tách biệt, bản nháp, hint, reload, ba nhiệm vụ và hồi kết. Chất lượng persona với provider thật chưa đo; test request xác nhận đúng card/model và không trộn lịch sử NPC khác.
