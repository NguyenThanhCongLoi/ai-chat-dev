# Giảm latency chat — 2026-10-05

## Các thay đổi đã áp dụng

- Chat stream của Assistant và Role Play gọi gateway ngay trong web container, thay vì RPC sang `assistant_stream_worker`. Assistant không stream và suggest của Assistant cũng gọi trực tiếp.
- Circuit breaker Assistant dùng ID cấu hình CMS để hai gateway có cùng wire model ID không vô tình chặn fallback của nhau.
- HTTPX Client dùng chung trong process, tối đa 64 kết nối / 32 keep-alive, giữ kết nối rảnh 120 giây. Không đặt API key làm header mặc định: mỗi request lấy credential theo model trong CMS.
- SSE được đọc tăng dần, chuyển tiếp nội dung ngay, không chờ toàn bộ câu trả lời. Bỏ reasoning/private metadata khỏi nội dung client. Giữ nhận biết hoàn tất, giới hạn token, partial và fallback trước khi có nội dung.
- Stream có `Cache-Control: no-cache, no-transform` và `X-Accel-Buffering: no`. Đây là tín hiệu cho proxy, không bảo đảm mọi proxy đều tuân thủ.
- Đóng upstream response khi kết thúc hoặc khi generator bị đóng. Khi deadline hết trong lúc một lần đọc đang chạy, cleanup diễn ra khi lần đọc đó trả về; HTTP read timeout vẫn là giới hạn cho lần đọc bị treo.
- Khi tạo chat Assistant thực sự mới, bỏ hai GET tải lịch sử và file rỗng. Chat chuyên biệt được mở lại vẫn tải đầy đủ lịch sử/file.
- Web container CPU tăng 0,5 → 1; min/max containers vẫn 1, max_inputs vẫn 20. Một container tránh nhiều writer độc lập trên SQLite/Modal Volume. CPU tăng có chi phí; không phải cam kết throughput gấp đôi.
- Thêm 3 trường nullable vào log, tự migrate bằng init_db; log cũ vẫn giữ nguyên và các số đo mới để trống.

Không cắt memory, tài liệu, prompt, moderation hay thay model để đạt số latency đẹp. Voice transport không được thay trong đợt này.

## Đo ở đâu, đọc như thế nào

CMS → Logchat → bấm vào một dòng để xem chi tiết. CSV cũng có các trường này:

| Trường | Khoảng đo |
| --- | --- |
| client_first_chunk_ms (Latency) | Trình duyệt bắt đầu gửi → nhận delta nội dung đầu tiên. Có thể gồm tạo chat/upload. |
| server_prepare_ms | Middleware nhận request stream → trước khi bắt đầu gọi gateway. Assistant fallback có thể bao gồm thời gian các lần thử trước; nhóm Role Play có thể bao gồm nhân vật trả lời trước đó. |
| gateway_headers_ms | Bắt đầu HTTP gọi gateway → nhận response headers. Gồm chờ pool, kết nối và upstream chờ header; không phải riêng TCP connect. |
| gateway_first_chunk_ms | Bắt đầu cùng HTTP request → nhận SSE chứa nội dung đầu tiên. Đây là TTFT từ Modal tới gateway, gồm cả gateway_headers_ms. |
| latency_ms (Runtime) | Số đo server hiện có, giữ nguyên phạm vi của từng luồng. Không đổi công thức để so sánh log cũ. |

Không cộng gateway_headers_ms với gateway_first_chunk_ms vì chúng chồng lấn. Khi fallback, các số gateway là lần thử phát ra nội dung, không phải tổng mọi lần thử. Trường gateway không có trên transport Modal cũ hoặc các request không stream.

Công thức định hướng với một lần thử, không upload/tạo chat:

`client TTFT ≈ client→Modal + server_prepare + gateway TTFT + Modal→client/render scheduling`

Không thể tính chính xác mạng hai chiều chỉ bằng cách trừ các đồng hồ này: các mốc bắt đầu khác nhau, có queue trước middleware, fallback và lịch xử lý trình duyệt.

## Triển khai và quay lại

Build frontend và deploy Modal như workflow hiện có. Không tự deploy trong đợt thay đổi này.

Mặc định: `CHAT_TRANSPORT=direct`. Muốn quay lại worker cũ: đặt `CHAT_TRANSPORT=modal` trong env của function web trong modal_app.py rồi deploy. Các worker vẫn được giữ để phục vụ rollback.

`GATEWAY_CONNECT_TIMEOUT_SECONDS` vẫn điều khiển connect timeout. Read timeout vẫn theo cấu hình từng model và tổng budget hiện có. Tăng timeout giúp giảm lỗi chờ nhưng không tự làm TTFT nhanh hơn.

So sánh trước/sau bằng cùng gateway, model, prompt, độ dài history, có/không tài liệu và mức concurrency. Đo median và p95; tách fallback và lượt đầu sau cold start. Chưa có benchmark trên Modal/gateway thật, nên không công bố mức giảm từ 5–7 giây xuống một con số cụ thể.

## Mã nguồn mở đã xem và hướng nâng cấp

Nguồn đọc: repo chính thức và tài liệu chính thức; không dùng số quảng cáo để cam kết hiệu năng.

| Dự án | Phù hợp với hệ thống này | Quyết định |
| --- | --- | --- |
| [HTTPX](https://www.python-httpx.org/advanced/clients/) | Tái sử dụng TCP/TLS, pool, đọc SSE tăng dần | Áp dụng ngay trên dependency hiện có. Tài liệu xác nhận pool tránh tạo lại kết nối mỗi request. |
| [LiteLLM](https://github.com/BerriAI/litellm) | Gateway đa provider, routing/fallback và theo dõi | Thử thành gateway riêng nếu cần thay gateway đang dùng; không thêm một hop proxy vào luồng hiện tại chỉ để giảm latency. |
| [Bifrost](https://github.com/maximhq/bifrost) | Gateway có load balancing và hỗ trợ nhiều model | Ứng viên benchmark ở lớp gateway. Số overhead trong README là tuyên bố của tác giả, không chứng minh app này nhanh hơn. |
| [vLLM](https://github.com/vllm-project/vllm) | Tự host model với batching, prefix caching và API streaming | Chỉ phù hợp nếu kiểm soát máy inference/GPU; không nâng tốc độ model bên gateway ngoài bằng cách cài vào web app. |
| [SGLang](https://github.com/sgl-project/sglang) | Framework phục vụ inference | Cũng cần quyền kiểm soát lớp inference và benchmark model/hardware cụ thể. |

Không có chuỗi dữ liệu tăng stars cùng một khoảng thời gian để xác nhận repo nào “tăng sao nhanh nhất mới nhất”. Tổng stars và benchmark khác máy không thay thế phép đo trên workload thực.

Để nâng cấp ít ảnh hưởng: dựng gateway thử độc lập, thêm một cấu hình gateway/model riêng trong CMS, chạy workload đối chiếu rồi mới chuyển phân công. So sánh cả nội dung, streaming, fallback, timeout, auth, TTS và log snapshots. Không thay toàn bộ framework/dependency cùng lúc.

## Kiểm chứng

- Bộ kiểm thử chat/voice/archive/CMS/fallback và transport: 83 ca passed tại thời điểm thực hiện.
- Frontend TypeScript + Vite production build thành công.
- Ca mới kiểm tra first content xuất hiện trước khi đọc phần body còn lại, reasoning không lộ, đóng response khi hủy, lỗi upstream, token limit, fallback khi chưa có nội dung và không đổi model sau partial.
- Đây là kiểm chứng chức năng với upstream giả lập, không phải benchmark mạng thực.
