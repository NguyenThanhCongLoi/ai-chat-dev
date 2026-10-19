# Kiến trúc hạ tầng production AI Companion

Ngày: 13/10/2026. Mục tiêu: 60–100 người online, một server riêng, thay Modal. Đây là tài liệu thiết kế và bàn giao; không thay runtime/config và chưa chứng nhận tải production.

## 1. Giả định và cấu hình chốt để khảo sát

LLM, suggestion, phân tích nền, kiểm duyệt, TTS lời thoại và tạo ảnh vẫn dùng provider API. Tự host web/CMS, lưu trữ, xử lý file/ảnh, Chatterbox reaction và Laya nếu bật. Chưa bao gồm tự host LLM lớn hoặc TTS realtime toàn bộ user.

Cấu hình khởi điểm: Linux x86_64, 16 vCPU, RAM32GB, NVMe1TB, NVIDIA24GBVRAM khi chuyển model GPU về máy; cổng mạng1Gbps, backup ngoài server. Hiệu năng vCPU phụ thuộc nhà cung cấp; cần benchmark trước cam kết throughput. GPU24GB là ngân sách thử nghiệm, không phải peakVRAM đã đo.

Nếu không tự host GPU: 8vCPU/RAM16GB/NVMe500GB có thể chạy phần web/API và clip đã tạo; tạo clip mới cần worker/provider khác. Mục tiêu hoàn toàn rời Modal chọn phương án có GPU hoặc cung cấp dịch vụ inference thay thế.

## 2. Sơ đồ trên một máy

~~~text
Browser / AIBox
      |
HTTPS443: Nginx
      |---- UI và CMS đã build
      |---- ảnh, nhạc, audio, video được phép public
      |
Companion API8000 ------ API gateway / TTS / moderation / image provider
      |
      +---- PostgreSQL5432: nghiệp vụ
      +---- Redis6379: queue/cache
      +---- Worker CPU: tài liệu/ảnh/jobs
      +---- Service Laya: chọn speaker
      +---- Worker Chatterbox: tạo reaction
      |
Persistent media + model cache + logs
      |
Backup mã hóa ngoài máy
~~~

Chỉ443 công khai;80 phục vụ redirect nếu cần. API/DB/Redis/inference bind mạng nội bộ, không public. Media private vẫn đi qua kiểm quyền hoặc URL ký; không mở toàn bộ thư mục chứa dữ liệu user dưới Nginx.

## 3. Services và ngân sách tài nguyên

| Service | Trách nhiệm | CPU dự trù | RAM dự trù |
| --- | --- | --- | --- |
| Nginx/static FE/CMS | HTTPS/proxy/SSE/static/range | 0.5vCPU | 0.5GB |
| Companion FastAPI | Auth/CMS/chat/stream/usage | 3vCPU | 4GB |
| PostgreSQL | Metadata/history/config/memory | 2vCPU | 4GB |
| Redis | Queue/status/cache cần thiết | 0.5vCPU | 1GB |
| Worker CPU | Document parse/avatar/jobs | 2vCPU | 3GB |
| Worker Chatterbox | Generate bộ reaction offline | 2vCPU | 5GB |
| Laya service | Decision inference | 1vCPU | 3GB |
| Host/monitoring | Linux/Docker/agents | Khoảng1vCPU | 3GB |
| Tổng dự trù | Không phải idle consumption | Khoảng12vCPU | 23.5GB |
| Dự phòng trên host16/32 | Burst/filesystem cache | Khoảng4vCPU | Khoảng8.5GB |

CPU/RAM trên là ngân sách để bắt đầu đo, không phải reservation chính thức, hard limit đã kiểm thử hoặc guarantee. VRAM tách RAM hệ thống. Đo peak của đúng phiên bản model, context/batch và concurrency trước quyết định hai model cùng resident. Chatterbox concurrency ban đầu1job, ưu tiên Laya cho chat. Media playback trên browser không dùng GPU host.

FE/CMS là static React/Vite: không chạy Vite dev hoặc Node thường trực. Build cần tài nguyên tạm riêng; nên CI build và triển khai artifact. Không build nặng đồng thời tải cao trên host nhỏ.

## 4. Môi trường

| Thành phần | Môi trường đề xuất |
| --- | --- |
| Host | Ubuntu Server LTS hoặc Linux tương đương được đội vận hành hỗ trợ |
| Orchestration | Docker Engine + Compose, một host |
| Backend | Python3.12, FastAPI/Uvicorn, dependencies theo lock/release |
| Build UI | Node24, npm ci, TypeScript/Vite |
| CPU worker | Cùng image backend hoặc image xử lý ảnh có rembg/ONNX cần thiết |
| Reaction worker | Python3.11 theo worker hiện có, chatterbox-tts0.1.7, ffmpeg/PyTorch/CUDA tương thích |
| Router worker | Môi trường riêng theo Laya0.3.20/torch2.5.1/transformers4.57.3 hiện có; kiểm khả năng cài trước khi khóa image |
| GPU host | NVIDIA driver + Container Toolkit tương thích CUDA của image |
| DB | PostgreSQL phiên bản được đội vận hành pin và hỗ trợ |
| Queue | Redis + một framework worker được BE chọn/pin |

Hai worker GPU cần image riêng vì môi trường/version không giống web. Không cài tất cả model libraries vào backend. Không cần Kubernetes cho giai đoạn một host. Không có autoscale phần cứng: tăng process/concurrency chỉ trong giới hạn host và upstream.

## 5. Dữ liệu và nơi lưu

| Dữ liệu | Hiện tại | Đích đề xuất |
| --- | --- | --- |
| Users/session/profile/quyền | SQLite | PostgreSQL |
| Character/spec/preset/version/publication | SQLite | PostgreSQL |
| Room/member/messages/alternatives/suggest | SQLite | PostgreSQL |
| Memory/relationship/state/event/reflection | SQLite | PostgreSQL |
| Model/prompt/assignment/settings | SQLite/CMS | PostgreSQL |
| Encrypted CMS keys | DB dùng DOCS_PASSWORD để giải mã | DB mới, giữ key decrypt hoặc rekey có quy trình |
| Uploaded/reference/reaction/speech/assets | Nhiều loại BLOB trong SQLite | Giai đoạn1 giữ dữ liệu; giai đoạn2 filesystem/objectstore + metadata |
| Original music | music_backgr/mp3 ngoài Git | Persistent media, chuyển riêng |
| Image/video bundled | Git/image | Build/release assets |
| Model weights/cache | Modal volumes | Persistent model volume |
| Queue | BackgroundTasks và worker Modal | Queue durable/status, cấu hình retry |
| Log/audit | DB và application logs | DB + logs rotated/monitoring |
| Secrets | Modal secrets/env | Envfile hạn chế quyền hoặc secret manager |

MongoDB chưa được dùng. Không bắt buộc chuyển Mongo để tích hợp AIBox; PostgreSQL phù hợp tiếp tục mô hình quan hệ SQLAlchemy hiện có. Nếu tổ chức bắt buộc Mongo cần một dự án đổi persistence/query/schema riêng.

Không public static các file upload private. VoiceID provider không là model giọng nằm trong backup; phải giữ đúng tài khoản/provider hoặc clone lại.

## 6. Ngân sách disk và băng thông

| Khoản | Dự trù |
| --- | --- |
| OS/images/releases | 40–60GB |
| DB/index | 30–50GB |
| Media/speech cache/uploads | 150–250GB |
| Model cache | 30–50GB |
| Logs/temp | 20–40GB |
| Dung lượng trống | Ít nhất20% ổ |

NVMe1TB tạo khoảng dự phòng, không có nghĩa dữ liệu luôn dùng hết. Retention/cache cleanup tránh đầy ổ. Mức tăng media phải đo từ audio bitrate/duration và số lượt thực tế. Ví dụ1000clip/ngày, trung bình0.5MB → khoảng15GB/tháng chưa gồm backup/ảnh.

100 streams nhạc128kbps =12.8Mbps payload; chưa audio voice/video/download. Cổng1Gbps hữu ích cho burst; cần kiểm tốc độ thực và quota egress, không chỉ thông số cổng. Không đưa giá thuê khi chưa có nhà cung cấp/region.

## 7. Ánh xạ chức năng Modal

| Modal | Thay thế |
| --- | --- |
| web | API container + reverse proxy |
| assistant_worker/assistant_stream_worker | Direct pooled gateway trong API |
| process_avatar/regenerate_avatar | CPU worker gọi cùng image pipeline/provider |
| backfill/optimize functions | Admin/CLI jobs có giới hạn |
| generate_reactions | Chatterbox inference service + durable job worker |
| GroupRouter | HTTP nội bộ Laya, local routing fallback |
| Volume | Host persistent volumes + backup |
| Secrets | Secret manager/envfile riêng |
| Cold-start autoscale | Service resident/worker queue trên host; tài nguyên giới hạn |

GroupRouter HTTP adapter đã có trong code. Reaction/ảnh local worker và queue chưa được tích hợp hoàn chỉnh. Default router local không gọi model GPU.

## 8. Luồng vận hành

Chat: browser → Nginx → API/auth/ownership → DB/context → provider SSE → browser. Proxy phải tránh buffer SSE, có timeout phù hợp. Suggest/TTS/analysis làm tăng upstream calls; API keys không vào frontend.

Reaction: CMS request → DB/reference/job → queue → workerGPU → validate/save clips → CMS status; browser dùng clips đã lưu. Job phải version/token guard, retry giới hạn và không ghi bộ cũ sau đổi giọng/xóa nhân vật.

Avatar/documents: request → queueCPU → xử lý → DB/media/status. Đặt concurrency nhỏ, resource cap và giới hạn input. Công việc background analysis nhẹ có thể giữ inline ban đầu nhưng phải xác định việc nào cần durable.

DBpool không lấy một connection cho mỗi user online. Redis queue cần persistence/recovery policy; không chỉ cache trongRAM. Log job không ghi key/reference riêng tư.

## 9. Secrets/config và tình trạng code

Code có DATA_DIR, DATABASE_URL, FRONTEND_DIST, CHARACTER_IMAGE_DIR, ROLEPLAY_MUSIC_DIR, DOCS_USERNAME/PASSWORD, LLM/gateway/moderation configs, CHAT_TRANSPORT=direct, GROUP_ROUTER_MODE và HTTP GROUP_ROUTER_API_BASE/API_KEY.

Envfile hiện còn MODAL_TOKEN_*; Dockerfile cài optional modal; reaction/ảnh và nhánh transport còn lời gọi Modal. Compose hiện chỉ web, SQLite, mộtUvicorn process. Không thể lấy sơ đồ này rồi chỉ docker compose up để có toàn bộ hạ tầng đề xuất.

Cần BE bổ sung queue/backend, worker endpoints/auth, dedicated GPU images, PostgreSQL driver/migration/SQLite-specific fixes, reverse proxy và monitoring. Không tự tăng Uvicorn workers khi chưa review state/cache/DB behavior. Không gửi secrets Git hoặc đặt VITE_* secret.

## 10. Năng lực và kiểm thử tải

Giả định100người gửi1tin/30s →3.3turn/s. Turn trung bình6s →20turns in-flight. Hai LLMcalls/turn →6.7calls/s; nhóm/voice/analysis thêm. 100người gửi ngay cùng lúc là burst khác.

Code hiện HTTPpool64 và incrementalTTS8slots mỗiprocess. Quota upstream/concurrency/DBquery có thể là bottleneck trước CPU. Test20→60→100online và burst, chat đơn/nhóm, cachehit/miss, upload cùng lúc. Đo p50/p95 firsttext/fullreply/firstaudio/queuewait, timeout/error, memory/CPU/disk/GPU, DBpool và gateway429.

Đặt SLO theo yêu cầu sản phẩm/provider, không khẳng định máy này chắc cân100active generations. Một host không HA; hostdown là toàn stackdown.

## 11. Backup, deploy, rollback

Mục tiêu ban đầu đề xuất: RPO<=24h từ backupngày; RTO vài giờ cần diễn tập. Muốn RPO thấp hơn dùng continuous WAL/archive cho PostgreSQL. Đặt backup mã hóa ngoài host, thử restore DB+media+credential. DB/media phải snapshot nhất quán.

Trước migration: backup SQLite bằng service_data.py, originalmedia, secrets qua kênh riêng, passworddecrypt cũ và provideraccounts. Sau PostgreSQL dùng công cụ backup PostgreSQL tương ứng; service_data.py hiện dành SQLite.

Deploy từ commit/tag xác định, buildCI, backup trướcschema change, healthcheck/smoke, rollout/restart có kiểm soát. Rollback code và schema phải tương thích; thay code không luôn rollbackdata. Đội BE quảnmigration, độiops quản host/backups/monitoring, sản phẩm quản provider/content/billing.

## 12. Lộ trình chuyển, chưa thực hiện trong tài liệu

1. Chốt host/APIprovider/GPU và domain hoặc path AIBox.
2. Chuẩn bị host/Docker/network/persistent directories.
3. Thay transport Modal; xây workerCPU/reactionHTTP/LayaHTTP và queue.
4. Diễn tập DBmigration và media permissions.
5. Giữ decrypt key, xác thực provider voiceIDs/models.
6. Stagingsmoke mọi tính năng, error/cancel/retry và restartjobs.
7. Benchmark60–100users, điều chỉnhlimits, thiết lập alerts/backups.
8. Chuyểntraffic rồi giữ nguồn cũ theo rollbackplan.

SSO/payment AIBox là integrationcontract riêng; hạ tầng không tự triển khai thanh toán.

## 13. Nguồn và tài liệu liên quan

Đối chiếu compose.yaml, Dockerfile, deploy/service.env.example, service_entrypoint.py, chat_transport.py, incremental_voice.py, modal_app.py, modal_reactions.py, modal_group_router.py và backend DB/media code.

- [Báo cáo hệ thống](AI_COMPANION_SYSTEM_REPORT.md)
- [Bản đồ code](CODE_STRUCTURE.md)
- [Bàn giao BE](BE_SERVICE_HANDOFF.md)
- [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)
- [Docker GPU Compose](https://docs.docker.com/compose/how-tos/gpu-support/)
- [PostgreSQL connections](https://www.postgresql.org/docs/17/runtime-config-connection.html)

Bảng sizing là ước lượng kỹ thuật theo scope đã nêu, không phải benchmark từ tài liệu của các hãng.
