# Moonfall — mở rộng cảnh và nhịp chơi

Bản nâng cấp ngày 18/10/2026. Chỉ thay đổi World; không thay prompt, giọng hay thuật toán sinh câu trả lời của chat thường.

## Các cảnh được thêm

Mỗi chương hiển thị bốn giai đoạn: **Khám phá → Đối chiếu → Ký ức → Trở về**. Tiến trình lấy từ manh mối/puzzle đã lưu; video không quyết định trạng thái.

| Chương | Cảnh bổ sung | Tài nguyên |
| --- | --- | --- |
| 1 | Selene dừng lại ở lối sập; bước vào phế tích | enter_ruins_video, memory_video_01 |
| 2 | Nhật ký và tiếng vọng cô gái chưa rõ danh tính | unknown_girl, memory_transition, memory_video_02 |
| 3 | Sau khi giải đố nghi lễ, Selene thời trẻ lên tiếng | young_selene, seal_activation, memory_video_03 |
| 4 | Tiếng gọi trong học viện sụp đổ | young_selene, memory_video_04 |
| 5 | Thư Elarion và khoảng dừng để trò chuyện | elarion, memory_video_05 |
| 6 | Selene thời trẻ và Elarion, khoảng trống thời gian | young_selene, elarion, deep_vault_awaken, memory_video_06 |
| 7 | Bóng cô gái và vật chứa, phong ấn sau giải đố | unknown_girl, seal_activation, memory_video_07 |
| 8 | Selene đối diện lời nói của chính mình trong quá khứ | young_selene, memory_space_video; memory_video_08 theo kết cũ |

memory_exit xuất hiện cuối ký ức; chapter_complete_video giữ mapping hoàn thành. Bỏ qua/lỗi video không làm mất tiến trình. Không ép video ký ức 8 vào ba kết còn lại.

Nhân vật phụ là **tiếng vọng ký ức**, không phải NPC toàn tri hoặc đang hiện diện ở hiện tại. Họ có tên và portrait riêng. Chưa gán giọng riêng nên thoại phụ hiện bằng chữ, không mượn giọng Selene. Selene dùng giọng từ CMS chat thường; lời dẫn trong chương vẫn chỉ đọc khi bấm nghe.

## Kết chương và nhịp mở chương

Kết mỗi chương mở hộp thoại có câu kết riêng và nút **Trở lại trò chuyện với Selene**. Cả bốn kết cuối đều có đường về chat và giữ lựa chọn đồng bộ ký ức. Không có nút đi thẳng chương kế tiếp.

Chỉ tính tin trong phòng riêng với Selene sau khi hoàn thành chương trước, đã có phản hồi hoàn chỉnh. Spam, tin lặp, phản hồi lỗi/dở dang và tin trong World không tính. Dữ liệu từng user độc lập.

Điểm = lượt hợp lệ + thưởng chủ đề liên quan (tối đa 4) + tăng tin tưởng sau chương trước (tối đa 2). Tối thiểu 3 lượt hợp lệ; ngưỡng chương 2–8: 7, 10, 12, 14, 15, 17, 19. Đây không phải số tin bắt buộc vì có thưởng. Không thêm lần gọi LLM để tính điểm.

Save cũ thiếu mốc bắt đầu tính từ lần nâng cấp, không lấy toàn bộ lịch sử trước đó để tự mở hết. Chương đã hoàn thành không bị khóa lại. Admin chơi thật theo cùng nhịp; preview riêng trong CMS không đồng bộ ký ức sang chat.

Lựa chọn và puzzle được hoán vị theo lượt chơi, đổi vị trí giữa các chương; reload không đảo lại cùng câu hỏi.

## CMS

Vào **/worlds/admin → World & giọng đọc**:

- **Nhịp mở chương linh hoạt**: ngưỡng, thưởng, chủ đề, bật/tắt nhịp.
- **Cảnh nối, tiếng vọng và lời kết chương**: thoại, người nói, lời kết, tên giai đoạn và lời gợi. Sửa JSON → Áp dụng bản nháp JSON → Lưu cấu hình World.
- **Âm lượng World mặc định**: chung, nhạc, môi trường, hiệu ứng, dẫn, nhân vật và mức nhạc khi có lời.
- **Manifest asset / Story event → VFX**: tài nguyên theo sự kiện.
- **Kiểm tra & debugger**: tạo và mở preview riêng.

Nhạc dùng lại thư viện chat thường. Mặc định mới: chung 85%, nhạc 45%, nhạc còn 35% khi có giọng. Người đã chỉnh trên trình duyệt có thể bấm **Dùng âm lượng từ CMS** trong World. Intro giữ bộ trộn riêng.

Nội dung truyện áp dụng cho save mới; save đang chơi giữ snapshot. Riêng âm lượng lấy cấu hình mới. Không xóa tiến trình cũ.

## Vật phẩm và nền

Dùng BG sạch và prop alpha có sẵn; hover/focus hiện viền theo hình prop. Thu thập vật rời sẽ ẩn prop, lộ BG gốc. Cổng, vòng nghi lễ, đường sập và dấu cố định không biến mất khi nhận vật liên quan.

Không tạo art mới hoặc đổi tên nguồn. Không ép mọi upload vào truyện khi chưa có vai trò phù hợp.

## Mã và kiểm thử

- character_chat/story_data/moonfall_arc/story_beats.json: nội dung cảnh bổ sung.
- character_chat/adventure/story_enrichment.py: cast, giai đoạn, hoán vị và mapping.
- character_chat/adventure/pacing.py: điểm mở chương theo user.
- frontend/src/worlds/ChapterConclusion.tsx: màn kết chương.
- frontend/src/worlds/AdventureAdmin.tsx: CMS.
- tests/test_world_pacing.py: khóa chương, quyền riêng tư, bốn kết, phạm vi kiến thức.
- tests/test_world_flow_browser.py: màn kết, nút quay về, lưu âm lượng qua browser.

## Kết quả kiểm tra

- 56 bài backend đạt: Moonfall cũ, Memory Adventure và nhịp mở chương mới.
- 4 bài hàng đợi giọng đọc đạt.
- Kiểm tra Edge desktop đạt: tải đúng chương 1 và 8, mở màn kết, quay về chat trả 200; sửa/lưu thanh âm lượng CMS trả 200. Dùng DB riêng và phản hồi LLM giả trong test, không gọi provider thật.
- Build TypeScript/Vite đạt; 708 chuỗi giao diện đủ 6 bản dịch bên cạnh tiếng Việt.
- Dịch nội dung cảnh bổ sung đã được tạo cho các ngôn ngữ đang hỗ trợ; chưa có thẩm định biên tập bởi người bản ngữ.

Deploy Modal thành công. Health 200, build_version: 20261018-004607-62e9513d6c7f. Bundle WorldApp-DuHKQ-nh.js trả 200 và chứa màn kết chương/cấu hình nhạc mới. Chưa nghiệm thu provider TTS/LLM production trong lần kiểm tra này.
