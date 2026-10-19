# Worlds — Chương truyện có hướng dẫn và nhiệm vụ liên kết

Cập nhật 16/10/2026. Đây là phần bổ sung cho WORLDS_DEMO.md và thay thế các dòng “chưa có nhiệm vụ liên kết/gợi ý/lối tắt” trong báo cáo tiến độ ban đầu.

## Đã cải tiến

1. Bảng “Bạn nên làm gì tiếp?” có hành động phù hợp trạng thái thật, không phải lời khuyên do AI tự bịa.
2. Hướng dẫn bốn bước ngay trong giao diện; không cần đọc tài liệu trước.
3. Chọn nhanh đội hình, ưu tiên các nhân vật fantasy nếu có trong kho. Vẫn cho chọn 1–3 người và không tạo Character mới.
4. Ba lời nhờ giúp nối tiếp: tìm lời chứng ở quán trọ; đối chiếu trong rừng; tìm trang nghi lễ ở tháp.
5. Nhận nhiệm vụ, tìm bằng chứng, báo cáo người giao nhiệm vụ. Không được hoàn thành trước điều kiện hoặc nhận thưởng lặp.
6. Các vai trong chương được phân theo thứ tự đội hình: người đối chiếu, người dò đường, người giữ nghi lễ. Với 1–2 nhân vật, một người có thể nhận nhiều lời nhờ giúp.
7. Danh sách gặp gỡ có lối tắt đến từng người, đi qua đường nối hợp lệ; có lịch sử cuộc gặp để quay lại.
8. Trò chuyện bằng ba chủ đề soạn sẵn: động cơ, chuyện ngoài nhiệm vụ, điều nhân vật đã biết. Có lời thoại khác nhau theo vai; không cần provider.
9. Ba mức gợi ý chủ động bấm để mở; xin gợi ý không tiêu lượt hoặc phát thưởng.
10. Báo cáo chỉ thêm người nhận vào danh sách biết bằng chứng. Không tự chia sẻ cho tất cả nhân vật.
11. Mỗi nhiệm vụ báo cáo thành công tăng trust với người giao nhiệm vụ một lần. Hoàn tất cả ba nhận kỷ vật Dấu ấn ba lời hẹn.
12. Ba hồi truyện dựa trên tiến trình, danh sách nhiệm vụ có trạng thái khóa/nhận/đang làm/báo cáo/xong.
13. Giữ tự do khám phá và đường kết thúc cũ: có ba manh mối vẫn được tới đài sao. Không bắt buộc hoàn thành chuỗi phụ.
14. Sửa tự cuộn: chỉ cuộn transcript, không kéo cả trang khỏi hướng dẫn.
15. Tương thích save/checkpoint cũ khi chưa có trường nhiệm vụ. Các snapshot cũ không bị ghi đè.

## Cách chơi mới

Thế giới → Bước vào → Chọn nhanh đội hình hoặc chọn thủ công → Khởi đầu mới → Cùng bước qua cánh cửa.

Ở mỗi bước, bấm nút nổi bật trong bảng “Bạn nên làm gì tiếp?”. Luồng đầy đủ:

- Tìm manh mối ở quảng trường.
- Nhận lời nhờ giúp đầu tiên.
- Tới quán trọ, tìm lời chứng, quay về báo cáo.
- Gặp người giao lời nhờ giúp thứ hai, nhận nhiệm vụ, tới rừng. Nếu d20 thấp thì thử tìm lại; không mất cơ hội.
- Quay về báo cáo rồi nhận nhiệm vụ cuối, tìm trang nghi lễ ở tháp và báo cáo.
- Tới Đài Sao Cũ, lưu checkpoint, chọn một trong ba kết thúc.
- Mở Nhật ký để tạo nhánh khác từ mốc trước quyết định.

Có thể dùng bản đồ hoặc lối tắt nhân vật để tự đi; bảng nhiệm vụ luôn phản ánh trạng thái thật. Tạm dừng điều tra để trò chuyện bằng các chủ đề bên dưới hội thoại. Ô nhập tự do vẫn cần moderation và narrator/provider như trước.

## Phân biệt lời thoại, persona và AI

Chuỗi nhiệm vụ, chủ đề hội thoại và phần thưởng của chương này do code/tác giả quy định. Đây chưa phải AI tự thiết kế nhiệm vụ. Vai trong chương không sửa character card gốc. Lời thoại không dùng provider là lời thoại mẫu theo vai; chưa mô phỏng toàn bộ cá tính riêng của mỗi card.

Khi đã chọn model narrator trong CMS và có moderation, actor context lấy mô tả nhân vật gốc, sự kiện đã commit và các bằng chứng actor được phép biết. Đầu ra phải qua moderation; lỗi thì dùng lời kể mẫu. Các thao tác điều hướng/gợi ý không gọi narrator để tránh chi phí không cần thiết.

Chưa có quest editor tổng quát, tự sinh NPC, AI tự sinh world pack, multiplayer người thật hoặc marketplace. Không sinh ảnh/video hoặc bổ sung inference GPU. Giữ VI/EN cho chương này.

## Code

- character_chat/world_chapter.py: quest prerequisites, guidance, contacts, routes, authored topics.
- character_chat/world_engine.py: state transition/journal và projection.
- character_chat/api/worlds.py: ownership, action validation, idempotency/CAS, narrator/moderation.
- frontend/src/worlds/WorldChapter.tsx: hướng dẫn, nhiệm vụ, lối tắt.
- tests/test_world_chapter.py: hoàn thành chuỗi bằng 1/2/3 nhân vật ở VI/EN, báo cáo riêng, không thưởng lặp, route/return, hints, save cũ.

Deploy cùng app chính: python -m modal deploy modal_app.py. Chưa tự deploy trong phiên nâng cấp này.

## Kiểm chứng

Build TypeScript/Vite đạt. Bộ hồi quy backend 83 test đạt; sau khi bổ sung kiểm tra receipt nhiệm vụ và privacy/moderation narrator, 29 test tập trung Worlds/chapter/API contract đạt. Edge desktop đi hết chuỗi ba nhiệm vụ bằng đội hình ba người, hội thoại soạn sẵn, gợi ý, checkpoint và hai kết thúc. Screenshot cuối: artifacts/worlds-chapter/ec41d873/chapter-start.png. Không gọi provider thật trong test; chưa nghiệm thu deployment Modal. Local demo đã khởi động lại ở 127.0.0.1:18765 với dữ liệu riêng giữ nguyên.
