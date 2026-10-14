> Nhánh selfhost/dev: dùng [hướng dẫn server riêng](SELF_HOSTED_DEPLOYMENT.md). Không dùng token Modal. GPU giữ nguyên và chưa chuyển; tạo reaction mới tắt trong bản CPU. Tài liệu này mô tả packaging/data gốc, ưu tiên cấu hình của hướng dẫn mới.

# Bàn giao AI Companion ver1 cho BE

## 1. Phiên bản và phạm vi

Nhánh integration/service-ver1 (tag bàn giao v1.0.0-service.1) bắt đầu từ tag v1.0.0: backend + UI + CMS, không có companion video. main/ver1, tag v1.0.0 và update giữ nguyên. Đây là gói triển khai SQLite một instance; chưa phải bản PostgreSQL nhiều instance hay SSO với sản phẩm khác.

| Mục | File/thư mục | Vai trò |
| --- | --- | --- |
| Backend | character_chat/ | FastAPI, assistant, roleplay, CMS API |
| UI + CMS UI | frontend/ | Build thành frontend/dist, backend phục vụ cùng host |
| Container | Dockerfile, compose.yaml | Build UI riêng rồi chạy Python một process |
| Cấu hình | deploy/service.env.example | Mẫu trống, secrets cấp riêng |
| Dữ liệu | data/ | Persistent ngoài image và Git |
| Backup/restore | scripts/service_data.py | Snapshot SQLite, file phụ, nhạc tuỳ chọn, SHA256 |
| Kiểm tra | scripts/smoke_service.py | Health, UI, CMS, xác thực; không gọi LLM trả phí |
| CI | .github/workflows/service-ver1.yml | Test backup + build và smoke container |

## 2. Chạy trên server có Docker Compose

```bash
git clone --branch integration/service-ver1 --single-branch https://github.com/NguyenThanhCongLoi/ai-chat-assistants.git ai-companion
cd ai-companion
cp deploy/service.env.example deploy/service.env
mkdir -p data music_backgr/mp3
sudo chown -R 10001:10001 data
```

Sửa service.env bằng editor hoặc secret manager:
- DOCS_USERNAME và DOCS_PASSWORD bắt buộc; bảo vệ CMS và API docs.
- Giữ cùng DOCS_PASSWORD cũ nếu chuyển database để giải mã API key CMS. Code hiện ưu tiên DOCS_PASSWORD hơn ADMIN_ENCRYPTION_KEY.
- Cấu hình LLM_API_KEY hoặc khôi phục các key đã lưu trong CMS.
- Cấu hình OPENAI_API_KEY cho kiểm duyệt và các provider voice trong CMS.
- Đặt CORS_ORIGINS đúng origin UI. Mặc định UI và API cùng host.
- Không commit service.env; file này cũng bị loại khỏi Docker context.
- CHAT_TRANSPORT=direct, GROUP_ROUTER_MODE=local tránh phải có worker Modal cho chat thông thường.

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 companion
python scripts/smoke_service.py --url http://127.0.0.1:8000
```

Truy cập / cho UI; /admin cho CMS; /docs cho API docs. Compose chỉ bind localhost:8000; reverse proxy của sản phẩm trỏ về địa chỉ này và cung cấp HTTPS. Không expose cổng trực tiếp ra Internet khi chưa cấu hình proxy.

Để smoke CMS API đã đăng nhập, đặt DOCS_USERNAME/DOCS_PASSWORD trong môi trường terminal rồi dùng --admin. Không truyền mật khẩu bằng URL.

Container chạy UID 10001. Nếu restore/chép dữ liệu bằng root trên Linux, sửa ownership của data/ trước khi khởi động. SQLite chỉ dùng một process/instance; không tăng workers hoặc scale container với cùng database. PostgreSQL/SSO cần một đợt triển khai riêng.

## 3. Các phụ thuộc phải bàn giao

| Chức năng | Yêu cầu |
| --- | --- |
| Sinh text, suggest, phân tích | LLM API và model cấu hình trong CMS |
| Voice nhân vật | TTS API hoạt động, credential và voice ID còn hợp lệ |
| Phát reaction đã tạo | Clip và reference trong database |
| Tạo reaction mới | Modal worker character-reactions + mode modal + quyền đúng workspace |
| Group router Laya | Không cần khi GROUP_ROUTER_MODE=local |
| Xử lý avatar | Local Pillow; tác vụ rembg/model nâng cao cần dependencies/worker phù hợp |
| Nhạc nền gốc | File music_backgr/mp3 riêng, không nằm trong GitHub |
| Reminders/maintenance định kỳ | Khi bỏ Modal cần chuyển các lịch/tác vụ cần thiết sang scheduler hạ tầng mới |

REACTION_GENERATOR_MODE=disabled chỉ chặn tạo clip mới; vẫn phát các clip đã lưu. Để tạo mới qua worker đang có, đặt REACTION_GENERATOR_MODE=modal, MODAL_TOKEN_ID/MODAL_TOKEN_SECRET đúng workspace chứa worker. Worker GPU tách khỏi container web; image web không tải model GPU. Không đặt AVATAR_MODAL_FUNCTION nếu chưa cấu hình worker tương ứng.

Chuyển backend web khỏi Modal không sao chép giọng đã clone ở TTS provider: voice ID vẫn tham chiếu dịch vụ ngoài. Nếu đổi provider/tài khoản voice, có thể phải upload reference và clone lại.

## 4. Dữ liệu CMS có đi theo không?

Clone GitHub KHÔNG có dữ liệu đang chạy. Khi chuyển đủ SQLite, DATA_DIR, asset ngoài DB và secrets phù hợp, mới giữ được dữ liệu.

| Nội dung | Nơi lưu | Cách chuyển |
| --- | --- | --- |
| Prompt, model, cài đặt CMS, nhân vật quản trị | SQLite, app_settings/model_configs và các bảng liên quan | Backup toàn DB |
| User, phòng, lịch sử, cảm xúc, memory, logs | SQLite | Backup toàn DB, bảo vệ thông tin riêng tư |
| Avatar/biểu cảm upload, voice sample, reaction, action sound upload | Các bảng blob trong SQLite | Backup toàn DB |
| Các file phụ phát sinh trong DATA_DIR | Volume/thư mục persistent | Backup DATA_DIR |
| Ảnh và sound có sẵn trong source | image/, sound_effect/ | Theo Git/container |
| Nhạc gốc | music_backgr/mp3 | Chuyển riêng hoặc --music-dir |
| Key đã nhập CMS | Mã hoá trong DB | Cần DOCS_PASSWORD cũ |
| Modal Secrets, service.env, credential provider | Ngoài Git/DB | Cấp riêng qua kênh bảo mật |
| Voice clone bên provider | Dịch vụ ngoài | Giữ provider/account hoặc clone lại |
| Ngôn ngữ/tuỳ chọn lưu browser | localStorage | Không tự chuyển sang origin/trình duyệt mới |

Backup chứa thông tin user, lịch sử và credentials mã hoá; không push GitHub hoặc gửi công khai. Công cụ không xoá dữ liệu nguồn và từ chối restore đè lên thư mục có sẵn.

## 5. Chuyển dữ liệu từ Modal

Không chạy lệnh chuyển khi đang có request ghi. Bật maintenance trong CMS, chờ các chat/job đang chạy xong, đóng băng các writer/scheduler và xác nhận volume đã commit. Maintenance riêng không chặn toàn bộ worker hay thao tác admin. Một bản volume download khi writer vẫn chạy không bảo đảm snapshot nhất quán.

Dùng Modal profile đúng nơi production đang chạy. Lệnh tải volume đã được đối chiếu với CLI hiện có:

```powershell
python -m modal profile current
python -m modal volume get character-chat-data / D:\companion-transfer\modal-data
python -X utf8 scripts/service_data.py backup --data-dir D:\companion-transfer\modal-data --output D:\companion-transfer\cms-backup.zip --music-dir D:\ai_chat_char\music_backgr\mp3
python -X utf8 scripts/service_data.py verify D:\companion-transfer\cms-backup.zip
```

Nếu không chuyển nhạc, bỏ --music-dir. Chọn đường dẫn backup mới chưa tồn tại. Không đọc/hiển thị secret vào log. Dữ liệu production chưa được tải tự động trong đợt đóng gói này.

## 6. Restore trên server mới

Dừng service mới trước restore. Upload ZIP riêng đến server và chạy:

```bash
python scripts/service_data.py restore /private/cms-backup.zip --target /private/restored-companion
```

Target phải chưa tồn tại. Kết quả:
- restored-companion/data/ là DATA_DIR.
- restored-companion/music/ là nhạc nếu đã đóng gói.

Script kiểm checksum mọi file, SQLite integrity và số bản ghi từng bảng trước khi hoàn tất. Chép data/ vào thư mục data của service mới; nếu đã có database thử nghiệm, giữ một bản backup rồi chuyển sang thư mục mới, không gộp đè. Chép music/ vào music_backgr/mp3. Cấp cùng DOCS_PASSWORD cũ và các secrets ngoài DB, sửa ownership, rồi khởi động.

```bash
docker compose up -d
python scripts/smoke_service.py --url http://127.0.0.1:8000
```

Trong CMS, kiểm tra danh sách nhân vật, prompt, model, samples và bấm nghe các clip. Sau đó thử một chat đơn, một chat nhóm, suggest đúng ngôi/ngôn ngữ, voice VI/EN và action sound. Kiểm tra đăng nhập tài khoản cũ, quyền phòng private và lưu cài đặt qua một lần restart container. Chỉ chuyển traffic production sau khi các bước này đạt.

## 7. Tích hợp vào sản phẩm hiện có

Giữ Companion là service riêng. Reverse proxy có thể route một host riêng vào Companion; đây là cách ít đổi đường dẫn nhất vì UI đang gọi /v1/... và asset theo root.

Nếu dùng /companion/ chung host, BE/FE cần sửa base URL, asset path và routing; không chỉ thêm prefix ở proxy.

Đăng nhập hiện tại dùng session bearer riêng, chưa có SSO:
1. Backend sản phẩm xác thực user.
2. Implement trao đổi session hoặc xác minh token tin cậy ở Companion.
3. Ánh xạ external_user_id với User/UserAccount hiện tại; quyết định cách liên kết account cũ.
4. Giữ kiểm tra quyền cho phòng, tin nhắn, nhân vật riêng và CMS.
5. Không tin user_id hoặc X-Demo-User-Id do client gửi; DEMO_AUTH_ENABLED=false.

Proxy phải chuyển tiếp stream từng chunk, không buffer SSE và giữ Range/206 cho audio. Timeout cần phù hợp chat/voice. Browser vẫn có chính sách autoplay, đặc biệt iframe/iPhone; cần kiểm thử UI thực tế. Không có tác vụ riêng trả phí nào được đảm bảo chỉ bằng healthcheck.

## 8. Kiểm thử và giới hạn xác nhận

Đã xác minh:
- Build UI ver1 đạt.
- 6 test đóng gói/khởi động/restore đạt, bao gồm backend Uvicorn chạy thật với CMS restore và credential thử nghiệm mã hoá.
- 10 test reaction hiện có đạt.
- GitHub CI Linux build Docker, khởi động container và smoke health/UI/CMS/xác thực đạt: https://github.com/NguyenThanhCongLoi/ai-chat-assistants/actions/runs/38221493070 (commit e12b7d7; các thay đổi sau chỉ ghi tài liệu).

Máy chuẩn bị gói không cài Docker; container đã được xác minh bằng CI Linux. BE vẫn cần nghiệm thu trên hạ tầng đích với provider và dữ liệu thật. Có thể chạy python -m pytest -q tests/test_service_package.py tests/test_service_startup.py sau khi build UI để lặp lại test migration.

Dữ liệu CMS live chưa được chuyển, provider LLM/TTS/GPU chưa được kiểm thử với secrets thật trong gói này. Đây là bộ triển khai có quy trình xác minh; không phải cam kết tất cả API ngoài luôn hoạt động.

## 9. Cập nhật và rollback

Backup dữ liệu trước mỗi lần nâng cấp. Chạy từ commit/tag rõ ràng, build image rồi smoke trước chuyển traffic. Rollback image không tự rollback schema/database; giữ backup tương ứng. Không dùng docker compose down -v để giải quyết lỗi dữ liệu.

Tài liệu Docker tham khảo:
- https://docs.docker.com/build/building/multi-stage/
- https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/
