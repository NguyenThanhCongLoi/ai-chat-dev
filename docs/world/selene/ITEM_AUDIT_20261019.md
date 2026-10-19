# Rà soát vật phẩm cả 8 chương — 19/10/2026

Đã đối chiếu trực quan ảnh nền đang được manifest gọi và kiểm tra dữ liệu của **68 điểm tương tác / 32 cảnh logic**. Các cảnh dùng chung nền vẫn gộp cùng một bản đồ. Không thêm tranh mới hoặc đổi đáp án, phần thưởng, điều kiện hidden ending.

| Chương | Kết quả và sửa đổi |
|---|---|
| 1 | Cổng, chìa khóa, bẫy tên, dấu chân, tượng/nguyệt thạch và cột rune đã đối chiếu. Giữ vùng chìa khóa bị che trước khi kiểm tra cổng. |
| 2 | Nắn vùng click mặt dây chuyền, nhật ký, trang rách, ghế đá và nét khắc theo hình thật. Dấu bóng người tan đặt lại dưới mái vòm. Cánh hoa bí mật chưa được vẽ vào nền: dùng đúng prop cánh hoa dưới phiến đá thay vì vùng trống; túi đồ phóng phần cánh hoa bằng khung nhìn CSS, không dùng ảnh chiếc lá bạc. |
| 3 | Dấu Hội đồng trỏ vào phù hiệu trên tường thay vì props ở vị trí cũ. Lời quan sát sửa từ sáp niêm sang dấu khắc, đủ VI/EN/JA/ZH/KO/MY/KM. Các bước chạm phong ấn/nghi lễ giữ nguyên điều kiện. |
| 4 | Đã đối chiếu tinh thể, bia vỡ, tiếng vọng, hành lang và trần sập. Giữ các vị trí/clean plate đang khớp hình. |
| 5 | Bổ sung vùng chuẩn cho những trang giấy và dấu niêm thư viện; không còn điểm marker chung chung tại tọa độ mặc định. Thư và chữ ký vẫn nằm trên cùng lá thư trước nhà. |
| 6 | Mốc đổi ngày và đối chiếu thời gian dùng đúng nền phòng đồng hồ. Gộp đúng phòng đó với hầm đồng hồ, tách khỏi hành lang ký ức. Thu vùng mảnh gương bí mật sát một mảnh kính thay vì cả đống kính. |
| 7 | Đã đối chiếu bệ nguyệt, hốc đặt vật, văn tự, hình thể và các mảnh ký ức. Giữ vùng hiện có; vật bí mật không có đốm sáng. |
| 8 | Đã đối chiếu cụm ký ức, mặt dây chuyền, sân thượng và ba cơ chế cuối. Mặt dây chuyền ở không gian ký ức vẫn dùng asset rời đã có, không giả vờ là chi tiết vẽ sẵn trong nền. |

## Quy tắc hiển thị

- Vật đã vẽ trong nền: vùng click vô hình theo hình đó, không chèn lại sprite.
- Vật chưa có trong nền nhưng có asset phù hợp: dùng prop rời và vùng nhận click của prop.
- Không còn điểm tương tác nào rơi về marker không có hình trong bộ 8 chương mặc định.
- Mục tiêu thông thường đang mở có đốm sáng; item bí mật không có đốm.
- Một mục tiêu chưa khám phá mỗi bản đồ ở mỗi bước; không nới điều kiện nhiệm vụ.
- Không xóa asset chỉ vì nó không xuất hiện trong cảnh hiện tại: nhiều ảnh phục vụ túi đồ, lời nhắc hoặc chương khác.

## Đường dẫn

- Vùng tương tác và nền: `character_chat/story_data/moonfall_arc/embedded_scenes.json`.
- Ánh xạ túi đồ và khung nhìn cánh hoa: `character_chat/story_data/moonfall_arc/props.json`.
- Ảnh nền thực dùng: `image/worlds/selene/moonfall/backgrounds/interactive/`.
- Props thực dùng: `image/worlds/selene/moonfall/props/prepared/`.
- Ảnh đối chiếu nội bộ có vẽ vùng: `artifacts/memory-adventure/full-item-audit/`. Đây là tài liệu kiểm tra, không đưa vào gameplay.

Bộ kiểm tra mới xác nhận đủ ảnh, kích thước nền, vùng chuẩn hóa, chế độ prop/embedded và các lỗi chương 2/6. Bộ trình tự kiểm tra cả user thường lẫn admin ở cả 8 chương. Không xác nhận chất lượng thẩm mỹ là tuyệt đối; cần xem thêm ở kích thước màn hình thực dùng.
