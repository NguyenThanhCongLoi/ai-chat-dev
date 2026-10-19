# BG gắn vật phẩm và vùng tương tác

Đã dùng 14 BG do bạn vẽ và 34 đường bao tương tác. Không chồng thêm prop lên BG. Nguồn PNG/WebP gốc được giữ nguyên.

Vùng bấm là polygon SVG, chỉ hiện viền/tên khi hover hoặc focus; hỗ trợ Enter/Space. Bấm lặp vật đã xem không phát lại thoại.

Thu từng vật trả lại riêng vùng nền sạch được căn theo mốc ảnh gốc, không đổi toàn bộ nền làm mất vật còn lại. Có 9 vùng thu thập. Hồ sơ và thư chỉ ẩn sau khi đã xem hết các chi tiết liên quan. Dấu cố định không biến mất. Trạng thái được suy từ inspected/inventory đã lưu nên reload, quay lại cảnh và save cũ vẫn đúng.

## Vị trí và kích thước

Tọa độ và kích thước dưới đây là hộp bao của polygon trên chính BG mới, không phải vùng chữ nhật có thể bấm. Các góc ngoài polygon không nhận click.

| BG | Vật / chi tiết | X, Y (px) | Rộng × cao (px) | Sau quan sát |
| --- | --- | --- | --- | --- |
| ch01_ancient_gate.png | Ổ khóa cổng | 956, 572 | 186 × 192 | Giữ nguyên |
| ch01_ancient_gate.png | Lối đi sụp | 448, 968 | 346 × 148 | Giữ nguyên |
| ch01_outer_ruins.png | Pho tượng vỡ | 352, 374 | 236 × 588 | Giữ nguyên |
| ch01_outer_ruins.png | Bức tường rune | 1348, 348 | 134 × 296 | Giữ nguyên |
| ch02_inner_ruins.png | Mặt dây chuyền bạc | 634, 976 | 190 × 94 | Thu / trả nền sạch |
| ch02_inner_ruins.png | Cánh hoa dưới đá | 1692, 918 | 128 × 82 | Thu / trả nền sạch |
| ch02_archive.png | Nhật ký cổ | 436, 1060 | 166 × 90 | Thu / trả nền sạch |
| ch02_archive.png | Trang nhật ký rách | 1462, 854 | 112 × 52 | Thu / trả nền sạch |
| ch03_chamber.png | Vòng nghi lễ | 838, 674 | 590 × 150 | Giữ nguyên |
| ch03_chamber.png | Rune màu đỏ | 1356, 882 | 76 × 60 | Giữ nguyên |
| ch03_chamber.png | Lá thư cháy | 506, 902 | 224 × 118 | Giữ nguyên |
| ch03_chamber.png | Dấu Hội đồng | 1300, 948 | 146 × 70 | Giữ nguyên |
| ch04_past.png | Mảnh tinh thể | 352, 856 | 140 × 206 | Thu / trả nền sạch |
| ch04_past.png | Tiếng vọng đang vỡ | 1266, 780 | 106 × 106 | Giữ nguyên |
| ch04_past.png | Phiến đá gãy | 1006, 792 | 212 × 298 | Thu / trả nền sạch |
| ch04_past.png | Hành lang đổ nát | 1462, 688 | 252 × 240 | Giữ nguyên |
| ch05_records.png | Lớp mực | 422, 818 | 422 × 150 | Thu sau khi xem đủ chi tiết |
| ch05_records.png | Dấu niêm | 614, 832 | 62 × 30 | Giữ nguyên |
| ch05_records.png | Ngày chỉnh sửa | 526, 892 | 170 × 46 | Giữ nguyên |
| ch05_witch_house.png | Thư Elarion | 588, 878 | 448 × 230 | Thu sau khi xem đủ chi tiết |
| ch05_witch_house.png | Chữ ký và vết cháy | 832, 986 | 120 × 80 | Giữ nguyên |
| ch06_vault.png | 23:47 · Kích hoạt | 444, 534 | 76 × 118 | Giữ nguyên |
| ch06_vault.png | 23:52 · Hàng rào phía bắc | 1594, 418 | 156 × 164 | Giữ nguyên |
| ch06_vault.png | Mảnh gương | 610, 892 | 476 × 232 | Thu / trả nền sạch |
| ch06_corridor.png | 00:03 · Dấu tách | 419, 199 | 109 × 274 | Giữ nguyên |
| ch06_corridor.png | 00:16 · Moonfall dừng | 911, 688 | 220 × 347 | Giữ nguyên |
| ch07_temple.png | Bàn thờ bốn vật | 652, 916 | 562 × 222 | Giữ nguyên |
| ch07_temple.png | Dòng khắc dưới ánh trăng | 168, 164 | 168 × 624 | Giữ nguyên |
| ch07_pale_chamber.png | Dấu vật dẫn | 609, 379 | 125 × 260 | Giữ nguyên |
| ch07_pale_chamber.png | Ranh giới giữa các mảnh | 1290, 99 | 464 × 507 | Giữ nguyên |
| ch08_memory_space.png | Những điều đã giữ | 260, 488 | 316 × 448 | Giữ nguyên |
| ch08_memory_space.png | Mặt dây chuyền đang ấm | 1272, 596 | 194 × 218 | Giữ nguyên |
| ch08_final_chamber.png | Ba cơ chế | 83, 673 | 1125 × 400 | Giữ nguyên |
| ch08_final_chamber.png | Đường sáng ngăn các mảnh | 1211, 286 | 105 × 750 | Giữ nguyên |

## Kiểm tra và cập nhật ảnh

- Gallery tham chiếu: artifacts/memory-adventure/embedded-bg/index.html. Viền đỏ chỉ có trong ảnh tham chiếu, không nằm trong BG trò chơi.
- 30 bài kiểm thử backend đạt; Edge đã kiểm tra hover, click trong/ngoài polygon, thu riêng một vật, reload và các chi tiết hồ sơ qua bàn phím.
- BG chuẩn bị sẵn và lớp nền sạch được tải trước theo cảnh; server không xử lý ảnh khi người chơi bấm.
- Manifest trình bày: character_chat/story_data/moonfall_arc/embedded_scenes.json. Quy tắc/cốt truyện vẫn lấy từ trạng thái backend.
- Khi thay BG, cập nhật polygon theo hình mới rồi chạy scripts/prepare_embedded_backgrounds.py. Script căn nền bằng SIFT/RANSAC, tạo WebP và 9 lớp nền sạch có mép chuyển mềm; không vẽ thêm bằng AI.
- Nếu chủ động chọn background hoặc scene_asset tùy biến khác trong CMS, cảnh chuyển về bố cục prop tùy biến. Với các BG gắn sẵn hiện tại, tọa độ trong embedded_scenes.json quyết định vùng bấm.

- Đã deploy Modal: 20261018-010336-330261e2e64b. Health, bundle mới và toàn bộ 23 ảnh phục vụ trả HTTP 200.
