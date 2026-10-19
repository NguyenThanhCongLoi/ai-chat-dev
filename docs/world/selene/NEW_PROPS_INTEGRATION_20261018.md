# Thay item mới vào BG sạch — 18/10/2026

- Đã thay 34 source WebP RGBA mới bằng bản runtime tương ứng trong props/prepared.
- Giữ đúng 34 khung x/y/W/H trong bảng bạn gửi. 14 cảnh sử dụng 12 BG gốc sạch, không dùng ảnh đánh dấu đỏ.
- Giữ nguyên alpha của ảnh mới; chỉ cắt lề alpha rỗng trong bản runtime. Ảnh nguồn không bị chỉnh sửa.
- Kiểm tra tự động: alpha sau cắt bằng chính xác alpha nguồn; hash 34 source khớp báo cáo.
- Màu được chỉnh bằng CSS riêng cho BG: giảm sáng/bão hòa nhẹ cho đá và kim loại, thêm sắc ấm nhẹ trong kho giấy; hiệu ứng sáng và mặt dây chuyền có xử lý riêng.
- Không nghiêng/skew giấy thêm vì source mới đã có phối cảnh.
- Khung cảnh dùng tỷ lệ kích thước thật của BG sau khi ảnh tải xong, giúp tọa độ % khớp hình đối chiếu.
- Sáu icon chưa được thay bằng source mới vẫn dùng bản prepared sẵn có: ch01_wrapped_key, ch02_moonflower_petal, moon_rune, moonstone, witch_symbol, seal_stone. Chỉ ảnh trong cảnh được thay theo đợt source mới; icon túi đồ không được thay bằng hình sai nội dung.
- Không thay đổi điều kiện mở chương, tiến độ, clue, item reward hoặc logic chat thường.

Bảng vị trí: [ITEM_PLACEMENT_REFERENCE.md](ITEM_PLACEMENT_REFERENCE.md).
Bằng chứng nguồn/alpha: artifacts/memory-adventure/new-props-integration-20261018.json.
Ảnh nghiệm thu: artifacts/memory-adventure/props-selene_XX-<scene>.png.
