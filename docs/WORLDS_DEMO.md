# Worlds — bản thử nghiệm CPU trên Modal

> Cập nhật chương truyện mới: [nhiệm vụ liên kết, lối tắt, hội thoại và gợi ý](WORLDS_CHAPTER_UPDATE.md). Các mô tả giới hạn của bản demo ban đầu bên dưới cần đọc cùng bản cập nhật này.

Ngày 16/10/2026. Nhánh: experiment/worlds-modal. Đây là demo chơi đơn có dữ liệu bền vững, không phải bản đầy đủ mọi tính năng trong nghiên cứu.

## 1. Đã có trong demo

- Tab /worlds, vào từ sidebar platform hoặc nút trong phòng chat.
- Cùng kho Character/effective_presets/publications; chọn 1–3 người đồng hành. Không tạo bản sao Character mới khi bắt đầu chuyến đi.
- Thế giới có ID ổn định, bản dịch Việt/Anh và phiên bản; dữ liệu riêng theo user × journey × branch.
- Một cốt truyện hoàn chỉnh “Lời hẹn dưới trăng”: 5 địa điểm, 5 manh mối, 3 kết thúc.
- Bản đồ SVG; bầu trời, cổng, trăng, chuyển cảnh, xúc xắc và tiến trình bằng CSS.
- Thời điểm đổi theo lượt chơi, không theo thời gian user vắng mặt.
- Cơ hội phụ: nghe tiếng chuông tại quảng trường khi trăng lên để giữ một kỷ vật; không khóa nhiệm vụ nếu bỏ lỡ.
- Tìm manh mối, chứng kiến riêng, chủ động chia sẻ cho nhóm, lore mở khóa theo khám phá.
- Nhật ký, vật phẩm, quan hệ cục bộ, checkpoint tối đa 5, tạo nhánh mới; nhánh cũ được giữ.
- Export nhật ký TXT bằng thao tác người dùng, không tự public.
- Ba chế độ: khởi đầu mới, ký ức tự chọn tối đa 8, tiếp nối (snapshot trust và ký ức đã ghim).
- Xem và bỏ ký ức mang theo/ghi chú trong chuyến đi. Không sửa chat gốc.
- User tạo world draft riêng từ khung điều tra; gửi xét công khai; admin review.
- CMS /worlds/admin: sửa bản dịch, lore/canon/từ khóa/điều kiện khám phá, prompt narrator và chọn model từ kho model hiện tại.
- CPU rules demo chạy không cần provider. Chế độ narrator AI là tùy chọn; tiến trình không do AI tự ghi.

## 2. Ai viết cái gì?

| Nguồn | Có thể viết | Hiệu lực |
| --- | --- | --- |
| Admin/creator được duyệt | Canon, lore, mở đầu, bản dịch, prompt narrator, trạng thái public | Mẫu thế giới được version hóa |
| User | Tên/mở đầu world draft; ghi chú riêng; ký ức chọn mang theo; hành động | Thế giới hoặc chuyến đi riêng của họ |
| AI | Lời kể/hội thoại dựa trên sự kiện đã commit | Không sửa canon, inventory, quest hoặc tự public |

User draft hiện kế thừa luật 5 địa điểm của demo, chưa có editor thiết kế quest graph tùy ý. AI chưa tự sinh world pack hoặc tự ghi đề xuất lore vào canon.

Canon và tin đồn có nhãn riêng. Notes của user được đánh dấu reference data, không nâng thành system instruction. Template thay đổi không sửa các chuyến đi đã bắt đầu; muốn dùng phiên bản mới phải mở journey mới.

## 3. Cốt truyện demo

Nguyệt Thạch biến mất trước lễ hội. Người chơi đối chiếu lời buộc tội với bằng chứng:

1. Quảng trường: dấu sáp kho lưu trữ.
2. Quán trọ: lời chứng riêng về người áo trắng.
3. Tháp: vai trò của phong ấn.
4. Rừng: tấm gương hé lộ khả năng đây là cuộc giải cứu; tìm kiếm có d20.
5. Đài sao: đưa ra lựa chọn khi có ít nhất 3 manh mối.

Kết thúc:
- Bảo vệ bí mật: giữ danh tính người vô tội.
- Công khai bằng chứng: xóa lời buộc tội nhưng để lại câu hỏi về riêng tư.
- Hoãn nghi lễ: cùng nhóm gia cố phong ấn, chọn thận trọng.

Người đồng hành lấy từ kho thực tế của môi trường. Nếu muốn Selene/Aurelion/Mira/Ren/Lyra xuất hiện, cần các nhân vật đó có trong DB của app demo; không tự sao chép database production vào app mới.

## 4. Luồng và module

~~~text
UI /worlds → authenticated World API
                   |
             ownership + moderation
                   |
           version / request_id / CAS
                   |
             deterministic engine
                   |
          commit event + journal/state
                   |
        optional direct provider narrator
                   |
          moderate output before display
~~~

- character_chat/world_engine.py: story rules, locales, evidence, knowledge visibility.
- character_chat/api/worlds.py: identity, template publication, campaign CRUD, snapshots, optional narrator.
- frontend/src/worlds/: UI, CMS editor, typed API; lazy-loaded bundle.
- modal_worlds.py: app/volume riêng, CPU, min_containers=0, max_containers=1.
- tests/test_worlds.py: privacy, idempotency, scopes, branches and rule invariants.

Demo lưu các document JSON trong AppSetting với prefix world_template:, world_campaign:, world_report:, world_audit:. Không ALTER schema cũ. Checkpoints là snapshot bên trong campaign. Cơ chế compare-and-swap chống ghi đè trạng thái và request_id chống áp dụng lại hành động. Không tuyên bố kiến trúc JSON/SQLite này đã đáp ứng tải lớn hoặc collaborative multiplayer.

## 5. Quyền và riêng tư

- World template có private/pending/public; journey luôn owner-only.
- Public template không bao gồm chat, notes, ký ức hoặc tiến trình của người khác.
- Trong engine, “public evidence” có nghĩa là cả nhóm AI của journey biết, không phải public Internet.
- Chỉ private character của chính user, community character được public và system presets mới được chọn.
- Model credentials không nằm trong API world/journey.
- Public view không chứa definition gốc, lore chưa mở khóa hoặc prompt nội bộ.
- Canon/lore được lọc quyền trước khi xếp hạng từ khóa/alias. Có ngân sách ký tự cho context; chưa phải token accounting chính xác.
- Ký ức và trust mang theo là bản chụp tại lúc bắt đầu; không đồng bộ hai chiều tự động.
- Xóa journey xóa toàn bộ document gồm checkpoint/nhật ký riêng. Audit admin vẫn giữ metadata thay đổi template.

Chưa có mời bạn thật vào một journey, ACL thành viên, công khai replay, xác minh tuổi, export/xóa dữ liệu toàn tài khoản theo mọi hệ thống, hoặc shared-state nhiều người thật. Không tự mở public những phần này.

## 6. Ngôn ngữ và kiểm duyệt

- ID địa điểm/quest/nhân vật không dịch. Nội dung template là dictionary theo locale.
- Demo story/UI được viết và kiểm tra Việt/Anh. Các màn cũ giữ hệ dịch hiện có.
- Chưa công bố world UI đã dịch đủ Nhật/Hàn/Trung/Myanmar/Khmer.
- Scope này chỉ hỗ trợ general audience; không có world adult.
- Free text, notes, public submission và output AI yêu cầu moderation provider. Thiếu provider hoặc lỗi → từ chối/chưa publish; nút hành động có sẵn vẫn chơi được.
- Draft riêng còn có lớp kiểm tra nội dung hiện có; không coi keyword guard là kiểm duyệt đa ngôn ngữ đầy đủ.
- Public submission còn phải admin duyệt. Kiểm tra email/key dạng phổ biến trước khi gửi; không tuyên bố đây là DLP hoàn chỉnh.
- Narration AI được kiểm duyệt trước khi hiển thị; lỗi provider dùng lời kể đã biên soạn. Không stream token AI chưa kiểm duyệt.
- Lịch sử/ghi chú không được gửi sang provider chỉ để render giao diện; khi bật narrator, context liên quan sẽ được gửi theo cấu hình provider.

Biến:
- WORLD_DEMO_ENABLED=true: bật API/UI experiment.
- WORLD_MODERATION_API_KEY hoặc OPENAI_API_KEY.
- WORLD_MODERATION_API_BASE (mặc định OpenAI /v1).
- narrator_model_id/narrator_prompt thuộc template trong CMS.

## 7. Chạy local và Modal

Ưu tiên desktop; mobile chỉ giữ mức dùng được, chưa tối ưu trải nghiệm riêng.

Local: build frontend bằng npm run build trong frontend, rồi chạy python scripts/run_worlds_demo.py từ gốc repo. Mở http://127.0.0.1:18765/worlds, đăng ký tài khoản test qua trang đăng nhập hiện có rồi quay lại /worlds. Database demo lưu riêng tại artifacts/worlds-desktop/data, giữ lại sau restart; không dùng DB production. Script tắt provider keys, nên chơi bằng nút luật có sẵn; free text/publication cần môi trường moderation riêng. CMS local chỉ mở khi bạn chủ động đặt DOCS_USERNAME/DOCS_PASSWORD cho process. Ctrl+C để dừng.

WORLD_DEMO_ENABLED mặc định false trên môi trường khác.

Modal:
~~~powershell
python -m modal deploy modal_worlds.py
~~~

App: character-chat-worlds-demo
Volume: character-chat-worlds-demo-data
Không dùng volume character-chat-data hoặc deploy đè app character-chat.

Mặc định tái dùng Secret character-chat-docs để bảo vệ CMS; chỉ tham chiếu tên, không export mật khẩu. Muốn tách mật khẩu, tạo secret riêng và đặt WORLDS_DOCS_SECRET lúc deploy.

Mặc định không mount secret provider, demo rules không gọi LLM. Để bật moderation/free text và cấu hình narrator:
~~~powershell
$env:WORLDS_USE_PROVIDER_SECRETS="true"
python -m modal deploy modal_worlds.py
~~~
Lệnh này tham chiếu character-chat-llm và character-chat-moderation. Model narrator cần được chọn qua CMS; việc deploy không tự gọi inference GPU hoặc tạo media.

Sau deploy:
- Mở /worlds.
- Tạo tài khoản test mới (DB demo riêng).
- CMS /admin và /worlds/admin dùng tài khoản Secret docs.
- Các nhân vật production không tự có trong volume mới; có thể dùng preset sẵn để thử trước.

## 8. Chưa triển khai trong demo này

Semantic embedding/graph database; director nhiều agent; proactive scheduler; realtime voice/call; soundscape mới; creator marketplace; cộng tác nhiều người thật; quest editor tổng quát; world generation bằng prompt; auto-public lore; toàn bộ nâng cấp memory/chat cũ trong roadmap.

GPU: không tạo ảnh/video/selfie/comic, không inference Chatterbox hoặc Laya. Hiệu ứng CSS/SVG chạy trên browser; không cần GPU inference trên server.

## 9. Tài liệu nghiên cứu và kiểm chứng

Xem WORLDS_RESEARCH.md. Build/test/browser results được ghi trong báo cáo khi hoàn tất, không suy từ /health hoặc schema.

## 10. Kiểm chứng ngày 16/10/2026

73/73 test backend đạt: Worlds, API contract, selfhost, Tarot, group routing và chat transport. Browser Edge đạt luồng lobby → chọn cast → khám phá → chia sẻ lời chứng → checkpoint → hai kết thúc trên hai nhánh → reload persistence, VI/EN, CMS và reduced motion; không phát hiện JavaScript error. Có smoke responsive cơ bản, chưa đầu tư UI mobile riêng. Build TypeScript/Vite đạt; cảnh báo chunk ứng dụng cũ >500KB còn tồn tại. Chưa kiểm thử provider narrator thật hoặc tải production; chưa deploy Modal.


## 11. Worlds trong giao diện chính

Worlds hiện được nhúng vào Avibi Platform cùng Roleplay, dùng chung auth_token, kho nhân vật và database của app đang chạy. Mục Thế giới mở panel trong khung chính; nút Bắt đầu phiêu lưu ở chat gửi yêu cầu về shell và chọn sẵn nhân vật. Tin nhắn điều hướng chỉ nhận từ iframe của app cùng origin. Khi mở Worlds, stream/audio chat được dừng; chuyển về giữ khung chat và tiến trình Worlds đã mở. Header Worlds nhúng dùng theme tài khoản; VI/EN của câu chuyện vẫn chọn riêng.

modal_app.py bật WORLD_DEMO_ENABLED mặc định true cho lần deploy tiếp theo. Có thể tắt bằng biến WORLD_DEMO_ENABLED=false trên máy deploy. Không cần dùng app/volume demo riêng nếu muốn dùng tài khoản và nhân vật hiện tại. Chạy python -m modal deploy modal_app.py rồi mở link character-chat cũ, vào Thế giới ở sidebar. Chưa tự deploy từ phiên sửa code này. modal_worlds.py vẫn dùng cho thử nghiệm độc lập với DB riêng.

Kiểm chứng tích hợp: TypeScript/Vite build đạt; 17 test Worlds và API contract đạt; Edge desktop đã kiểm tra đăng nhập dùng chung, mở Worlds trong shell, chơi một lượt, quay về chat rồi mở lại giữ tiến trình và nhận yêu cầu từ iframe Roleplay. Screenshot: artifacts/worlds-integrated/39a3e872/integrated.png. Chưa xác nhận deployment Modal thực tế.

Worlds tự thu gọn sidebar AIBox khi mở; nút Mở rộng thanh công cụ cho phép mở lại. Rời Worlds khôi phục trạng thái sidebar trước đó; tùy chọn mở/đóng trong Worlds không ghi đè preference thông thường. Xem ROLEPLAY_WORLDS_PROGRESS.md để phân biệt cải tiến đã có và roadmap, cùng hướng dẫn chơi từng bước.
