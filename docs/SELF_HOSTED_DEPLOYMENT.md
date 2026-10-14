# Bản chạy trên server riêng — selfhost/dev

## Phạm vi bản này

Theo yêu cầu giữ nguyên các tính năng GPU, đợt chuyển này chỉ chuyển web/CMS, xử lý CPU và lời gọi provider sang server riêng. Đây không phải bản tự host mọi model.

- UI/CMS/API, Tarot/Tử vi, chat đơn/nhóm, memory, lưu chat: chạy trên server mới.
- LLM, suggestion, kiểm duyệt, TTS lời thoại: gọi provider API trực tiếp từ server mới.
- Ảnh/video/clip reaction đã lưu: giữ qua backup database và assets Git.
- Avatar: mặc định giữ ảnh/default. Có thể bật AVATAR_GENERATOR_MODE=direct để chạy pipeline hiện có trên host và gọi provider ảnh đã cấu hình CMS.
- Chọn speaker nhóm: logic local; không khởi động Laya.
- Chatterbox reaction mới và Laya GPU: giữ nguyên code gốc, chưa chuyển sang server mới và không bật trong entrypoint của bản này.
- Không có SDK Modal trong Docker image. Entry point từ chối transport Modal, token Modal, reaction mode khác disabled và router mode khác local.

Các file modal_app.py, modal_reactions.py, modal_group_router.py là code triển khai cũ được giữ để tham khảo/GPU. Không chạy các file này trong luồng server riêng. Nhánh update trên Git giữ bản triển khai Modal đã commit trước đó; các sửa mới chưa push sẽ chỉ được đưa vào nhánh selfhost/dev nếu bạn commit tại nhánh này.

## Hạ tầng test

Một Linux host, 4 vCPU, 8 GB RAM, SSD/NVMe 100–150 GB là cấu hình khởi điểm để đo cho phạm vi CPU này; không phải cam kết throughput. Không cần GPU. Chỉ một instance API/Uvicorn do SQLite hiện tại và state trong process. Không scale nhiều container dùng chung file SQLite.

Cần Docker Engine + Compose plugin. Node/Python build nằm trong Docker stages, không cần cài Node trên host. Python 3.11+ trên host chỉ cần nếu dùng công cụ restore bên ngoài container. Để tích hợp PostgreSQL/Redis/SSO/payment, cần đợt triển khai riêng; compose hiện chưa có các service này.

## Chuẩn bị GitHub

Kiểm tra đang ở nhánh selfhost/dev bằng git branch --show-current.

Chỉ stage code/docs/assets cần bàn giao, kiểm tra git diff --cached --stat rồi commit và push. Không dùng git add . nếu chưa kiểm tra file mới. Database, backup, secrets, nhạc gốc và cache model không thuộc Git.

Có script chọn đúng các file bàn giao và commit. Chạy tại PowerShell:
~~~powershell
powershell -ExecutionPolicy Bypass -File scripts/publish_selfhost.ps1 -Push
~~~
Bỏ -Push nếu chỉ muốn commit local. Script không tự push khi không có -Push; từ chối file đã stage ngoài danh sách. Nếu có lỗi Git credentials, commit vẫn còn local, có thể push lại sau. Script không deploy Modal hoặc server mới.

Các ảnh Tarot đã giải nén cần commit; ZIP nguồn không cần đưa lên Git. Không cần commit frontend/dist vì Docker tự npm ci và build.

## Server mới: lấy code

~~~bash
git clone --branch selfhost/dev https://github.com/NguyenThanhCongLoi/ai-chat-assistants.git
cd ai-chat-assistants
cp deploy/service.env.example deploy/service.env
chmod 600 deploy/service.env
~~~

Xem ENV_HANDOFF.md để điền và chuyển env riêng. Điền DOCS_USERNAME, DOCS_PASSWORD, provider keys và CORS_ORIGINS của môi trường mới. Giữ DOCS_PASSWORD cũ nếu muốn giải mã API key đã lưu trong backup CMS. Không sao chép MODAL_TOKEN_* hoặc AVATAR_MODAL_FUNCTION từ server cũ.

Cấu hình mặc định bắt buộc:
~~~env
CHAT_TRANSPORT=direct
GROUP_ROUTER_MODE=local
GROUP_ROUTER_TRANSPORT=http
REACTION_GENERATOR_MODE=disabled
AVATAR_GENERATOR_MODE=default
DEMO_AUTH_ENABLED=false
~~~

Nếu API key của model đã nằm trong CMS backup, vẫn phải kiểm tra giải mã và quota/tài khoản provider. Voice ID là tài nguyên của provider, không nằm trong Git và không được tái tạo chỉ bằng restore.

## Chuyển dữ liệu đã có

Dừng service trên server mới trước restore. Giữ backup nguồn nguyên vẹn và không ghi đè database đang chạy.

Đặt ZIP backup tại đường dẫn riêng, ngoài Git. Khôi phục vào thư mục chưa tồn tại:
~~~bash
python3 scripts/service_data.py restore /private/companion-cms.zip --target /private/restored-companion
~~~

Công cụ xác minh checksum và SQLite integrity. Sau restore:

- /private/restored-companion/data/ là DATA_DIR.
- /private/restored-companion/music/ là nhạc nếu ZIP có đóng gói nhạc.
- Di chuyển hoặc sao chép nội dung data/ vào ./data/ trong repo; không tạo ./data/data/.
- Đặt nhạc vào ./music_backgr/mp3/. Nếu backup không có nhạc, chuyển nhạc nguồn riêng.
- Các BLOB ảnh, voice reference, reaction và audio nằm trong database được giữ.
- File ở ngoài DB chỉ được giữ khi nó đã nằm trong backup; kiểm tra manifest và nguồn trước chuyển traffic.

Cấp quyền:
~~~bash
sudo chown -R 10001:10001 ./data
~~~
Chỉ chạy lệnh trên sau khi xác nhận ./data là thư mục dữ liệu đúng của dự án. Không đổi quyền toàn server.

Không cần đem model cache GPU sang host CPU trong đợt này. Không xóa dữ liệu/code GPU nguồn.

## Khởi động

~~~bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 companion
curl --fail http://127.0.0.1:8000/health
docker compose exec companion python -c "import importlib.util; assert importlib.util.find_spec('modal') is None"
~~~

API bind 127.0.0.1:8000, không public trực tiếp. Nginx trên cùng host dùng mẫu deploy/nginx.conf.example; thay domain/certificate và bật HTTPS trước dùng tài khoản thật. FE/CMS do backend phục vụ từ bản build. Proxy cần tắt buffering để SSE hoạt động.

Không đặt service.env hoặc data/ trong thư mục static public. Không dùng Vite dev server trên server sản phẩm.

## Kiểm tra trước chuyển traffic

- Đăng nhập, quyền phòng, CMS đọc lại nhân vật/prompt/model/keys.
- Lưu tên/lời chào/câu gợi ý CMS và client cập nhật khi quay lại tab hoặc trong 30 giây.
- Gửi chat mới xác nhận prompt chính/dự phòng; không đánh giá bằng câu trả lời lịch sử.
- Chat stream, hủy, suggestion, nghe TTS, replay clip đã có.
- Tarot: ảnh, xuôi/ngược, deck riêng theo phòng, rút tiếp, reset và theme.
- Tử vi, upload tài liệu, memory, cảm xúc, xóa phòng.
- Restart container rồi kiểm dữ liệu vẫn tồn tại.
- Reaction generation mới bị tắt có chủ ý; việc phát clip đã có vẫn cần thử với dữ liệu restore thực tế.
- Test quota/latency provider trên host mới; healthcheck không xác minh API trả phí.

## Cập nhật và rollback

~~~bash
git pull --ff-only origin selfhost/dev
docker compose up -d --build
~~~

Backup DB/media trước cập nhật schema. Giữ commit/image và backup trước đó để rollback. Rollback code không tự rollback database.

Không dùng docker compose down -v để khắc phục lỗi dữ liệu. Volume/bind mount giữ dữ liệu khi container restart nhưng không thay thế backup ngoài host.

## Kiểm chứng

Workflow .github/workflows/selfhost.yml kiểm tra package, API, Tarot, cấu hình standalone và build/start Docker không có SDK Modal. Không tự deploy server.

Đợt này không chạy inference GPU hoặc đo RPM/CCU; không thay đổi code GPU. Khi muốn bật lại Chatterbox/Laya trên tài nguyên mới cần một nhánh migration riêng, GPU image/endpoint và kiểm thử thật.
