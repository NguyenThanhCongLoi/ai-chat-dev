> Cập nhật 18/10/2026: World hiện dùng BG đã vẽ trực tiếp vật phẩm và vùng bấm polygon. Xem [bản vị trí mới](EMBEDDED_BG_INTERACTIONS.md). Bảng bên dưới giữ lại để đối chiếu cách ghép prop cũ.

# Vị trí item trên BG — bản đối chiếu

Nguồn: cấu hình layout trong source hiện tại; không lấy cấu hình CMS trên Modal. Ảnh đánh dấu là file mới, không sửa BG gốc.

**Quy ước:** x/y tính từ góc trên trái của BG; W/H là khung đặt item (px), không phải kích thước file cần vẽ. Khung đỏ liền là item/hiệu ứng trong cảnh; khung đỏ đứt là điểm tương tác mở ảnh chi tiết, không dán toàn bộ ảnh item lên BG.

Các số px được làm tròn để dễ đối chiếu. Tọa độ phần trăm và số gốc trong JSON giữ độ chính xác. Khi màn hình co giãn, dùng phần trăm, không cố định px.

**Chế độ hiển thị:** floor/wall/warm/light giữ tỷ lệ ảnh (contain); floor_flat/table có thể kéo theo khung (fill). Ảnh alpha có lề trong suốt nên phần nét vẽ có thể nhỏ hơn khung đỏ. Light là lớp sáng, không phải vật phẩm nhặt được.

**Không ghép lại các hotspot thành item túi đồ:** tên điểm bấm, ảnh trong cảnh và item nhận được có thể khác nhau. Bảng dưới ghi riêng cả ba.

## selene_01 — Cổng cổ

BG: image/worlds/selene/moonfall/backgrounds/ancient_gate.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_01-ancient_gate.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_01-ancient_gate.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Ổ khóa cổng | ch01_gate_lock.webp | 680, 438 | 79 × 80 | 1441 × 1438 | moon_rune | wall |
| 2 | Lối đi sụp | ch01_collapsed_path.webp | 259, 579 | 360 × 185 | 1892 × 743 | ancient_key | floor |

## selene_01 — Tàn tích ngoài

BG: image/worlds/selene/moonfall/backgrounds/moonfall_outer_ruins.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_01-outer_ruins.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_01-outer_ruins.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Pho tượng vỡ | ch01_broken_statue.webp | 144, 201 | 259 × 474 | 1030 × 2138 | moonstone | floor |
| 2 | Bức tường rune | ch01_rune_wall.webp | 648, 217 | 187 × 322 | 959 × 2180 | — | wall |

## selene_02 — Tàn tích trong

BG: image/worlds/selene/moonfall/backgrounds/inner_ruins.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_02-inner_ruins.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_02-inner_ruins.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Mặt dây chuyền bạc | ch02_silver_pendant_scene.webp | 346, 531 | 288 × 209 | 1759 × 1100 | silver_pendant | floor |
| 2 | Cánh hoa dưới đá | ch02_petal_under_stone.webp | 734, 611 | 202 × 137 | 1797 × 1059 | moonflower_petal | floor |

## selene_02 — Kho lưu trữ cổ

BG: image/worlds/selene/moonfall/backgrounds/ancient_archive.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_02-archive.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_02-archive.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Nhật ký cổ | ch02_ancient_journal.webp | 403, 507 | 166 × 105 | 1794 × 1174 | ancient_journal | floor |
| 2 | Trang nhật ký rách | ch02_torn_diary_page.webp | 864, 587 | 108 × 72 | 1920 × 1224 | torn_diary_page | table |

## selene_03 — Căn phòng ngầm

BG: image/worlds/selene/moonfall/backgrounds/underground_chamber.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_03-chamber.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_03-chamber.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Vòng nghi lễ | ch03_ritual_circle.webp | 590, 450 | 432 × 88 | 3466 × 664 | witch_symbol | floor_flat |
| 2 | Rune màu đỏ | ch03_red_rune.webp | 756, 478 | 101 × 32 | 1937 × 725 | seal_stone | floor_flat |
| 3 | Lá thư cháy | burned_letter.webp | 202, 651 | 173 × 96 | 1601 × 1117 | — | floor_flat |
| 4 | Dấu Hội đồng | council_seal.webp | 893, 595 | 130 × 96 | 1673 × 1149 | council_record | floor |

## selene_04 — Moonbrook trong ký ức

BG: image/worlds/selene/moonfall/backgrounds/moonfall_past.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_04-past.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_04-past.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Mảnh tinh thể | ch04_crystal_fragment.webp | 259, 587 | 187 × 177 | 1468 × 1035 | crystal_fragment | floor |
| 2 | Tiếng vọng đang vỡ | ch04_shattered_echo.webp | 619, 306 | 230 × 217 | 1572 × 1600 | — | light |
| 3 | Phiến đá gãy | ch04_broken_tablet.webp | 475, 523 | 173 × 225 | 1520 × 1212 | broken_tablet | floor |
| 4 | Hành lang đổ nát | ch04_corridor_guiding_lights.webp | 749, 539 | 245 × 185 | 1776 × 1296 | — | light |

## selene_05 — Kho lưu trữ cổ

BG: image/worlds/selene/moonfall/backgrounds/ancient_archive.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_05-records.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_05-records.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Lớp mực | ch05_archive_record.webp | 432, 552 | 144 × 44 | 1871 × 1328 | council_record | table |
| 2 | Dấu niêm | ch05_archive_record_detail_seal.webp | 446, 569 | 36 × 20 | 705 × 485 | — | detail |
| 3 | Ngày chỉnh sửa | ch05_archive_record_detail_edit_date.webp | 533, 555 | 36 × 20 | 2005 × 1007 | — | detail |

## selene_05 — Ngôi nhà bên rừng

BG: image/worlds/selene/moonfall/backgrounds/witch_area_witch_house.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_05-witch_house.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_05-witch_house.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thư Elarion | ch05_elarion_letter.webp | 518, 563 | 130 × 64 | 1700 × 1080 | elarion_letter | floor |
| 2 | Chữ ký và vết cháy | ch05_elarion_letter_detail_signature.webp | 598, 595 | 36 × 28 | 1581 × 1199 | — | detail |

## selene_06 — Hầm sâu

BG: image/worlds/selene/moonfall/backgrounds/deep_vault.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_06-vault.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_06-vault.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 23:47 · Kích hoạt | ch06_record_activation.webp | 245, 257 | 130 × 394 | 598 × 2425 | — | floor |
| 2 | 23:52 · Hàng rào phía bắc | ch06_record_barrier.webp | 878, 273 | 122 × 386 | 589 × 2784 | — | floor |
| 3 | Mảnh gương | ch06_mirror_shard.webp | 446, 571 | 274 × 201 | 1675 × 1054 | mirror_shard | floor |

## selene_06 — Hành lang ký ức

BG: image/worlds/selene/moonfall/backgrounds/memory_corridor.webp — **1281 × 719 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_06-corridor.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_06-corridor.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 00:03 · Dấu tách | ch06_separation_mark.webp | 205, 259 | 167 × 201 | 827 × 1875 | — | wall |
| 2 | 00:16 · Moonfall dừng | ch06_moonfall_end_mark.webp | 538, 532 | 205 × 86 | 1866 × 1075 | — | floor_flat |

## selene_07 — Đền Trăng

BG: image/worlds/selene/moonfall/backgrounds/moon_temple.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_07-temple.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_07-temple.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Bàn thờ bốn vật | ch07_four_item_altar.webp | 389, 539 | 418 × 217 | 1837 × 1081 | — | floor |
| 2 | Dòng khắc dưới ánh trăng | ch07_moonlit_inscription.webp | 173, 257 | 173 × 257 | 1143 × 1920 | — | wall |

## selene_07 — Phòng Trăng Nhợt

BG: image/worlds/selene/moonfall/backgrounds/pale_moon_chamber.webp — **1282 × 719 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_07-pale_chamber.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_07-pale_chamber.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Dấu vật dẫn | ch07_vessel_mark.webp | 282, 395 | 179 × 173 | 1427 × 1591 | — | wall |
| 2 | Ranh giới giữa các mảnh | ch07_fragment_boundaries.webp | 551, 209 | 269 × 280 | 1600 × 1600 | — | light |

## selene_08 — Không gian ký ức

BG: image/worlds/selene/moonfall/backgrounds/memory_space.webp — **1440 × 804 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_08-memory_space.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_08-memory_space.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Những điều đã giữ | ch08_preserved_memories.webp | 187, 193 | 374 × 402 | 1920 × 1280 | — | light |
| 2 | Mặt dây chuyền đang ấm | ch02_silver_pendant_item.webp | 691, 362 | 173 × 209 | 1912 × 1272 | — | warm |

## selene_08 — Căn phòng cuối

BG: image/worlds/selene/moonfall/backgrounds/pale_moon_chamber.webp — **1282 × 719 px**.

[Mở BG đánh dấu](../../../artifacts/memory-adventure/item-placement-new-props/selene_08-final_chamber.png) · [SVG vector](../../../artifacts/memory-adventure/item-placement-new-props/selene_08-final_chamber.svg)

| # | Điểm bấm | Ảnh trong cảnh | x, y (px) | W × H đặt trên BG (px) | File ảnh (px) | Item nhận | Kiểu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Ba cơ chế | ch08_three_mechanisms.webp | 256, 367 | 397 × 273 | 1530 × 1252 | — | floor |
| 2 | Đường sáng ngăn các mảnh | ch08_dividing_light_lines.webp | 667, 173 | 218 × 288 | 1344 × 1792 | — | light |

## 14 item trong túi đồ

Đây là icon túi đồ, không tự dán lên BG. Item trong cảnh có thể dùng ảnh khác để phù hợp phối cảnh.

| Item ID | Tên | File icon | Kích thước file (px) | Nhận tại BG / điểm bấm |
| --- | --- | --- | --- | --- |
| ancient_key | Chìa khóa cổ | ch01_wrapped_key.webp | 1600 × 1600 | ancient_gate / Lối đi sụp |
| silver_pendant | Mặt dây chuyền bạc | ch02_silver_pendant_item.webp | 1912 × 1272 | inner_ruins / Mặt dây chuyền bạc |
| ancient_journal | Nhật ký cổ | ch02_ancient_journal.webp | 1794 × 1174 | ancient_archive / Nhật ký cổ |
| moonflower_petal | Cánh nguyệt hoa | ch02_moonflower_petal.webp | 1600 × 1600 | inner_ruins / Cánh hoa dưới đá |
| crystal_fragment | Mảnh tinh thể | ch04_crystal_fragment.webp | 1468 × 1035 | moonfall_past / Mảnh tinh thể |
| broken_tablet | Phiến đá vỡ | ch04_broken_tablet.webp | 1520 × 1212 | moonfall_past / Phiến đá gãy |
| council_record | Hồ sơ Hội đồng | ch05_archive_record.webp | 1871 × 1328 | underground_chamber / Dấu Hội đồng; ancient_archive / Lớp mực |
| elarion_letter | Thư Elarion | ch05_elarion_letter.webp | 1700 × 1080 | witch_area / Thư Elarion |
| mirror_shard | Mảnh gương | ch06_mirror_shard.webp | 1675 × 1054 | deep_vault / Mảnh gương |
| torn_diary_page | Trang nhật ký rách | ch02_torn_diary_page.webp | 1920 × 1224 | ancient_archive / Trang nhật ký rách |
| moon_rune | Rune Trăng | moon_rune.webp | 1600 × 1600 | ancient_gate / Ổ khóa cổng |
| moonstone | Nguyệt thạch | moonstone.webp | 1600 × 1600 | moonfall_outer_ruins / Pho tượng vỡ |
| witch_symbol | Biểu tượng phù thủy | witch_symbol.webp | 1600 × 1600 | underground_chamber / Vòng nghi lễ |
| seal_stone | Đá phong ấn | seal_stone.webp | 1600 × 1600 | underground_chamber / Rune màu đỏ |

## Ảnh để dành

- ch08_warm_pendant: Different pendant design; retain original Chapter 2 pendant and add realtime warm glow.

## Bộ file

- Gallery: artifacts/memory-adventure/item-placement-new-props/index.html
- Tọa độ đầy đủ: artifacts/memory-adventure/item-placement-new-props/placements.json
- Bảng CSV: artifacts/memory-adventure/item-placement-new-props/placements.csv
