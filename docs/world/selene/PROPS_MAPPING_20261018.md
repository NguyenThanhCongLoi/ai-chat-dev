# Bộ props mới — nhận diện và ghép cảnh 18/10/2026

Đã xem bộ 37 ảnh nguồn và background. Tách nền bằng Python theo yêu cầu người dùng;
không dùng AI vẽ lại. File nguồn giữ nguyên; bản dùng khi chạy nằm ở props/prepared/.

## Quy tắc

- scene_asset là hình đặt trong cảnh; item là phần thưởng nhận được. Hai trường độc lập.
- Tọa độ chuẩn hóa theo chính background của cảnh; không chia vị trí thành một lưới chung.
- detail là ảnh cận cảnh: chỉ đánh dấu vị trí trên tài liệu, mở ảnh chi tiết khi bấm.
- floor_flat ép phối cảnh vòng tròn thành ellipse trên mặt sàn; table đặt giấy trên mặt bàn.
- light dùng screen blend và mask mềm cho texture ký ức, tránh mép ảnh hình vuông.
- Cấu hình/bản lưu cũ nhận lớp trình bày mới theo ID, không sửa tiến độ hay kết quả.
- CMS Scenes & hotspot cho sửa scene_asset, presentation_mode, x/y/width/height.

## Ánh xạ đã kiểm tra

| Chương / điểm khám phá | Background | Ảnh mới | Cách đặt (x, y, w, h) |
| --- | --- | --- | --- |
| 1 · Ổ khóa cổng | backgrounds/ancient_gate.webp | ch01_gate_lock.webp | wall (0.472, 0.545, 0.055, 0.1) |
| 1 · Lối đi sụp | backgrounds/ancient_gate.webp | ch01_collapsed_path.webp | floor (0.18, 0.72, 0.25, 0.23) |
| 1 · Pho tượng vỡ | backgrounds/moonfall_outer_ruins.webp | ch01_broken_statue.webp | floor (0.1, 0.25, 0.18, 0.59) |
| 1 · Bức tường rune | backgrounds/moonfall_outer_ruins.webp | ch01_rune_wall.webp | wall (0.45, 0.27, 0.13, 0.4) |
| 2 · Mặt dây chuyền bạc | backgrounds/inner_ruins.webp | ch02_silver_pendant_scene.webp | floor (0.24, 0.66, 0.2, 0.26) |
| 2 · Cánh hoa dưới đá | backgrounds/inner_ruins.webp | ch02_petal_under_stone.webp | floor (0.51, 0.76, 0.14, 0.17) |
| 2 · Nhật ký cổ | backgrounds/ancient_archive.webp | ch02_ancient_journal.webp | floor (0.28, 0.63, 0.115, 0.13) |
| 2 · Trang nhật ký rách | backgrounds/ancient_archive.webp | ch02_torn_diary_page.webp | table (0.6, 0.73, 0.075, 0.09) |
| 3 · Vòng nghi lễ | backgrounds/underground_chamber.webp | ch03_ritual_circle.webp | floor_flat (0.41, 0.56, 0.3, 0.11) |
| 3 · Rune màu đỏ | backgrounds/underground_chamber.webp | ch03_red_rune.webp | floor_flat (0.525, 0.595, 0.07, 0.04) |
| 3 · Lá thư cháy | backgrounds/underground_chamber.webp | burned_letter.webp | floor_flat (0.14, 0.81, 0.12, 0.12) |
| 3 · Dấu Hội đồng | backgrounds/underground_chamber.webp | council_seal.webp | floor (0.62, 0.74, 0.09, 0.12) |
| 4 · Mảnh tinh thể | backgrounds/moonfall_past.webp | ch04_crystal_fragment.webp | floor (0.18, 0.73, 0.13, 0.22) |
| 4 · Tiếng vọng đang vỡ | backgrounds/moonfall_past.webp | ch04_shattered_echo.webp | light (0.43, 0.38, 0.16, 0.27) |
| 4 · Phiến đá gãy | backgrounds/moonfall_past.webp | ch04_broken_tablet.webp | floor (0.33, 0.65, 0.12, 0.28) |
| 4 · Hành lang đổ nát | backgrounds/moonfall_past.webp | ch04_corridor_guiding_lights.webp | light (0.52, 0.67, 0.17, 0.23) |
| 5 · Lớp mực | backgrounds/ancient_archive.webp | ch05_archive_record.webp | table (0.3, 0.686, 0.1, 0.055) |
| 5 · Dấu niêm | backgrounds/ancient_archive.webp | ch05_archive_record_detail_seal.webp | detail (0.31, 0.708, 0.025, 0.025) |
| 5 · Ngày chỉnh sửa | backgrounds/ancient_archive.webp | ch05_archive_record_detail_edit_date.webp | detail (0.37, 0.69, 0.025, 0.025) |
| 5 · Thư Elarion | backgrounds/witch_area_witch_house.webp | ch05_elarion_letter.webp | floor (0.36, 0.7, 0.09, 0.08) |
| 5 · Chữ ký và vết cháy | backgrounds/witch_area_witch_house.webp | ch05_elarion_letter_detail_signature.webp | detail (0.415, 0.74, 0.025, 0.035) |
| 6 · 23:47 · Kích hoạt | backgrounds/deep_vault.webp | ch06_record_activation.webp | floor (0.17, 0.32, 0.09, 0.49) |
| 6 · 23:52 · Hàng rào phía bắc | backgrounds/deep_vault.webp | ch06_record_barrier.webp | floor (0.61, 0.34, 0.085, 0.48) |
| 6 · Mảnh gương | backgrounds/deep_vault.webp | ch06_mirror_shard.webp | floor (0.31, 0.71, 0.19, 0.25) |
| 6 · 00:03 · Dấu tách | backgrounds/memory_corridor.webp | ch06_separation_mark.webp | wall (0.16, 0.36, 0.13, 0.28) |
| 6 · 00:16 · Moonfall dừng | backgrounds/memory_corridor.webp | ch06_moonfall_end_mark.webp | floor_flat (0.42, 0.74, 0.16, 0.12) |
| 7 · Bàn thờ bốn vật | backgrounds/moon_temple.webp | ch07_four_item_altar.webp | floor (0.27, 0.67, 0.29, 0.27) |
| 7 · Dòng khắc dưới ánh trăng | backgrounds/moon_temple.webp | ch07_moonlit_inscription.webp | wall (0.12, 0.32, 0.12, 0.32) |
| 7 · Dấu vật dẫn | backgrounds/pale_moon_chamber.webp | ch07_vessel_mark.webp | wall (0.22, 0.55, 0.14, 0.24) |
| 7 · Ranh giới giữa các mảnh | backgrounds/pale_moon_chamber.webp | ch07_fragment_boundaries.webp | light (0.43, 0.29, 0.21, 0.39) |
| 8 · Những điều đã giữ | backgrounds/memory_space.webp | ch08_preserved_memories.webp | light (0.13, 0.24, 0.26, 0.5) |
| 8 · Mặt dây chuyền đang ấm | backgrounds/memory_space.webp | ch02_silver_pendant_item.webp | warm (0.48, 0.45, 0.12, 0.26) |
| 8 · Ba cơ chế | backgrounds/pale_moon_chamber.webp | ch08_three_mechanisms.webp | floor (0.2, 0.51, 0.31, 0.38) |
| 8 · Đường sáng ngăn các mảnh | backgrounds/pale_moon_chamber.webp | ch08_dividing_light_lines.webp | light (0.52, 0.24, 0.17, 0.4) |

## Túi đồ đã đủ ảnh cho 14 vật phẩm

Đã bổ sung đủ bốn ảnh độc lập: moon_rune.png, moonstone.png, witch_symbol.png, seal_stone.png.\nBản runtime: props/prepared/<tên>.webp. Giữ alpha gốc, xử lý màu phông ở mép bán trong suốt, giữ nguyên file PNG nguồn.
Cả 14 vật phẩm đã có ảnh độc lập được gán. Không lấy ảnh cánh cửa/vòng nghi lễ thay ảnh vật phẩm.

ch08_warm_pendant.webp có thiết kế khác dây chuyền chương 2. Giữ ảnh dự phòng này trong manifest;
chương 8 dùng lại ch02_silver_pendant_item.webp với glow vàng, không thay đổi hình dáng dây chuyền.

## Kiểm tra hình ảnh

artifacts/memory-adventure/new-props.jpg: bộ nguồn.
artifacts/memory-adventure/prepared-props-contact.jpg: bộ đã xử lý nền.
artifacts/memory-adventure/props-selene_*.png: ảnh chụp 14 cảnh từ trình duyệt.
artifacts/memory-adventure/props-scenes-review.jpg: bảng xem tổng hợp.
