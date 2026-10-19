# Roleplay và Worlds: tiến độ thực tế, cách chơi và hướng tích hợp AIBox

> Cập nhật chương truyện mới: [nhiệm vụ liên kết, lối tắt, hội thoại và gợi ý](WORLDS_CHAPTER_UPDATE.md). Các mô tả giới hạn của bản demo ban đầu bên dưới cần đọc cùng bản cập nhật này.

Cập nhật thêm cho Chat Bot AI thường: [ROLEPLAY_CHAT_UPGRADE.md](ROLEPLAY_CHAT_UPGRADE.md). Các dòng chưa nâng cấp chat thường trong báo cáo ban đầu bên dưới đã được bổ sung một phần theo tài liệu này.

Ngày 16/10/2026. Nhánh experiment/worlds-modal. Báo cáo phạm vi đợt thử nghiệm Worlds, không phải chứng nhận đã hoàn thành mọi ý tưởng trong báo cáo nghiên cứu.

## 1. Vai trò trong AIBox

Worlds là một không gian nằm trong giao diện AIBox/Avibi Platform, bên cạnh Trợ lý AI và Chat Bot AI. Dùng chung tài khoản đăng nhập và kho nhân vật của backend đang chạy. Không cần một tài khoản Worlds riêng khi chạy trong cùng app.

Vào Worlds: sidebar tự thu gọn; nút mũi tên Mở rộng thanh công cụ cho phép mở lại bất cứ lúc nào. Bấm nút thu gọn để tiếp tục chơi toàn chiều rộng. Rời Worlds khôi phục trạng thái sidebar trước khi vào; việc mở/đóng sidebar trong Worlds không ghi đè lựa chọn sidebar bình thường. Chuyến chơi vẫn được giữ khi chuyển qua chat và quay lại trong cùng phiên giao diện; khi tải lại trang chọn Tiếp tục từ danh sách chuyến đi.

Đây là tích hợp trong shell hiện tại. Chưa triển khai SSO, thanh toán hoặc hợp đồng nhúng với một AIBox bên ngoài repo.

## 2. Roleplay cũ đã thay đổi gì trong đợt này?

| Thay đổi | Tình trạng |
| --- | --- |
| Nút Bắt đầu phiêu lưu trong phòng chat, lấy nhân vật đầu tiên làm lựa chọn sẵn | Đã có |
| Worlds mở trong khung chính, giữ sidebar/tài khoản chung | Đã có |
| Chuyển qua lại mà không điều hướng khỏi ứng dụng chính | Đã có |
| Dừng stream/audio Roleplay khi chuyển vào Worlds | Đã có |
| Dùng lại Character, preset hệ thống và nhân vật community công khai | Đã có |
| Ba cách bắt đầu: mới, chọn ký ức, tiếp nối trust/ký ức ghim | Đã có trong Worlds |
| Thay toàn bộ thuật toán memory/retrieval của chat Roleplay cũ | Chưa làm |
| NPC có chuỗi nhiệm vụ riêng liên kết với các NPC khác | Chưa làm |
| Nút Đến gặp NPC, quay về báo cáo người giao nhiệm vụ | Mới đề xuất |
| AI director sinh nhiệm vụ và gợi ý nhiều cấp | Mới đề xuất |

Kho nhân vật chung không đồng nghĩa progress/quan hệ chung: sự kiện và thay đổi trust trong Worlds hiện lưu riêng, không tự ghi ngược vào chat cũ. Cá tính narrator hiện nhận tên/mô tả ngắn của nhân vật, chưa có hệ thống mục tiêu/động cơ và quest cá nhân hoàn chỉnh.

## 3. Worlds có gì mới?

- Một truyện chơi được: Lời hẹn dưới trăng, 5 địa điểm, 5 manh mối, 3 kết thúc.
- Chọn 1–3 nhân vật đồng hành từ kho hiện có.
- Bản đồ SVG, cổng/trăng/bầu trời và chuyển cảnh CSS; không sinh ảnh/video GPU.
- Thời gian truyện chạy theo lượt: hoàng hôn, trăng lên, đêm bạc, trước bình minh.
- Quán trọ có lời chứng riêng: nhân vật không chứng kiến chưa nhận lời chứng đó trong context; có nút chia sẻ cho cả nhóm.
- Rừng có kiểm tra d20: dưới 7 chưa tìm được, có thể thử lại. Không mất vĩnh viễn đường hoàn thành truyện.
- Kỷ vật nghe chuông ở quảng trường lúc trăng lên; thưởng một lần, không phải điều kiện bắt buộc.
- Lore/canon/tin đồn được phân biệt; lore bí mật mở sau khám phá.
- Nhật ký, túi kỷ vật, trust cục bộ, tối đa 5 checkpoint và tạo nhánh giữ nguyên chuyến cũ.
- Chuyến đi riêng theo tài khoản; có thể xóa chuyến đi, bỏ ký ức snapshot và tải nhật ký TXT.
- VI/EN cho giao diện/cốt truyện mới; chưa có bản dịch đầy đủ các ngôn ngữ khác cho Worlds.
- Draft thế giới riêng; gửi xét duyệt; CMS sửa lore, bản dịch, prompt/model narrator và trạng thái công khai.
- Bộ luật backend xác nhận hành động, không để lời kể AI tự thêm vật phẩm hoặc hoàn thành quest.
- Revision/CAS tránh ghi đè tiến trình; request_id tránh áp dụng lại hành động khi gửi lặp.

## 4. Cách chơi bản demo

1. Đăng nhập giao diện chính; chọn Thế giới ở sidebar. Hoặc mở phòng chat rồi chọn Bắt đầu phiêu lưu.
2. Chọn Lời hẹn dưới trăng, chọn 1–3 người đồng hành và chế độ ký ức. Nhấn Cùng bước qua cánh cửa.
3. Bắt đầu ở Quảng trường Ngân Nguyệt. Nhấn Quan sát & tìm kiếm để lấy manh mối đầu tiên.
4. Bấm địa điểm nối liền trên bản đồ để đi. Ví dụ Quảng trường → Quán trọ → Quảng trường → Tháp Trăng.
5. Tìm manh mối ở quán trọ/tháp. Trong tab Tri thức, có thể Kể cho cả nhóm lời chứng riêng.
6. Tùy chọn vào Rừng Thì Thầm tìm thêm góc nhìn; nếu d20 thất bại có thể thử lại. Thời gian đổi sau mỗi 4 lượt. Ở quảng trường lúc trăng lên có nút nghe chuông.
7. Có ít nhất 3 manh mối thì tới Đài Sao Cũ qua Tháp hoặc Rừng.
8. Nhấn Lưu mốc trước khi quyết định. Chọn Bảo vệ bí mật / Công khai bằng chứng / Hoãn nghi lễ.
9. Sau kết thúc mở Nhật ký, chọn một checkpoint để tạo nhánh khác; chuyến đi cũ vẫn giữ.
10. Dùng Các chuyến đi để tiếp tục hoặc xóa một chuyến đi. Mở lại sidebar để chuyển về chat/không gian khác.

Chọn người ở ô hội thoại là chọn người nói, chưa phải di chuyển tới NPC hoặc đổi chuỗi quest cá nhân. Demo không giới hạn một NPC độc quyền cho mỗi địa điểm.

## 5. Hội thoại AI và quyền tác giả

| Vai trò | Quyền |
| --- | --- |
| Admin | Canon, bản dịch, mở đầu, lore, prompt/model và duyệt publication |
| User | Chọn hành động, ký ức mang theo, ghi chú và draft riêng |
| Narrator AI | Viết lời kể dựa trên sự kiện đã xác nhận, không tự sửa tiến trình |

Nút hành động có sẵn dùng lời kể tác giả khi chưa cấu hình narrator. Không phải toàn bộ lời thoại đang được LLM sinh trực tiếp. Gõ hội thoại tự do, lưu ghi chú, publish và trả lời AI cần moderation được cấu hình. Thiếu moderation thì khóa các thao tác đó; vẫn chơi bằng nút có sẵn được. Narrator cần chọn model trong CMS và cấu hình credentials/provider. Đầu ra narrator lỗi/không qua moderation thì dùng lời kể luật có sẵn.

World public là mẫu truyện có thể dùng chung. Nó không công khai lịch sử chat, ký ức, ghi chú hoặc tiến trình cá nhân. Demo chơi đơn với nhóm AI; chưa có nhiều người thật cùng một campaign.

## 6. Triển khai và kiểm tra

- App chính: python -m modal deploy modal_app.py, Worlds bật mặc định trong cấu hình deploy mới; có thể tắt bằng WORLD_DEMO_ENABLED=false trên máy deploy.
- App thử nghiệm độc lập: modal_worlds.py dùng app/volume riêng; không dùng nó nếu muốn tài khoản/dữ liệu app chính.
- Local: python scripts/run_worlds_demo.py, dùng DB demo riêng.
- Hướng dẫn chi tiết: WORLDS_DEMO.md; nguồn mở: WORLDS_RESEARCH.md.
- Chưa tự deploy từ phiên sửa này; cần deploy để thay đổi xuất hiện trên Modal.

Không coi build/test local là bằng chứng đã hoạt động trên app Modal của người dùng. Chưa nghiệm thu provider AI thật, tải nhiều người hoặc tích hợp AIBox bên ngoài.
