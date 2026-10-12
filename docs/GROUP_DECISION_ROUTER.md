# Thử chọn người trả lời bằng Laya trên Modal

Model: Laya Multilingual (Apache 2.0), không phải Jev của TypeSafe.
Chỉ tác vụ chọn người thay đổi; LLM sinh lời thoại, suggest, voice và companion giữ nguyên.

## Worker riêng

modal_group_router.py tạo app character-chat-group-router, GPU T4, tối đa 1 container.
Model load một lần mỗi container và cache vào volume character-chat-group-router-models.
Không có endpoint public, không dùng database sản phẩm. Container scale về 0 sau 2 giây không dùng (cấu hình tiết kiệm).
Có chi phí GPU khi worker hoạt động; lần đầu cold-start bao gồm tải/load model.

~~~powershell
cd D:\ai_chat_char
python -m modal deploy modal_group_router.py
python -m modal run modal_group_router.py
~~~

Lệnh run gửi hai tin mẫu và in thời gian cùng quyết định. Không sửa dữ liệu sản phẩm.

## Bật trên backend

~~~powershell
$env:GROUP_ROUTER_MODE="decision"
$env:GROUP_ROUTER_TRANSPORT="modal"
$env:GROUP_ROUTER_MODAL_APP="character-chat-group-router"
$env:GROUP_ROUTER_TIMEOUT_SECONDS="1.5"
$env:GROUP_ROUTER_MIN_PROBABILITY="0.65"
~~~

Chạy backend local bằng terminal này (cần đăng nhập Modal), hoặc dùng terminal này khi
deploy modal_app.py để cấu hình được đưa vào container web. Worker và web phải cùng workspace.
Bản production mặc định local; deployment worker không tự bật bộ chọn trên web.

Tắt: GROUP_ROUTER_MODE=local và restart/redeploy web.
Không đưa model vào container web SQLite, không cần API key Jev riêng cho worker này.

## Cách chọn và fallback

- Gọi tên, chọn người trong UI, yêu cầu mọi người/cặp, hỏi tiếp rõ ràng dùng quy tắc local.
- Còn lại: một request với mỗi nhân vật một choice A/B nên nói hay im.
- Context ngắn: tin user, 4 tin gần nhất, vai trò/mô tả/thế mạnh, chủ đề/tên nhóm; tối đa 6 người.
- Chọn xác suất A đạt ngưỡng, có thể từ 1 đến tất cả, giữ thứ tự roster.
- Timeout/lỗi/sai response/không ai đủ điểm: fallback local.
- Điểm gần như đồng đều (chênh dưới 0.05) cũng fallback, vì lượt thử CPU đã chọn cả người không liên quan.
- Ngưỡng thử chưa hiệu chuẩn; xác suất cao không bảo đảm đúng.
- Cold-start quá timeout không chặn chat: trả local, job model vẫn có thể hoàn tất để warm worker.
- group_routing trong logchat ghi router, điểm, decision_ms và decision_fallback.
- Không dùng cho moderation hoặc quyết định âm thanh.

## Máy local

Môi trường .tools/laya-router và cache .decision-cache vừa tạo đã được yêu cầu xoá.
Các script tải/chạy model local của lượt thử cũng đã được gỡ; chỉ giữ worker Modal.

## Kiểm tra

python -m pytest tests/test_group_decision.py tests/test_group_routing.py
Đo model thật bằng python -m modal run modal_group_router.py.
Kiểm tra vai trò tiếng Việt trên dữ liệu dev trước khi bật production.


## Kết quả thử thật ngày 12/10/2026

Worker đã deploy vào workspace nguyenthanhcongloi332004 và đã chạy model T4 thật.
Đây là Laya 0.3.20 với checkpoint multilingual hiện có, không phải Jev chính hãng.

| Tin mẫu | Model chọn | Thời gian model | Tổng thời gian từ máy local |
|---|---|---|---|
| Đổi công việc nhưng vẫn theo âm nhạc | Morgan, Luna, Mira | 547.29 ms (lượt đầu) | 32,620.76 ms, gồm cold-start |
| Mất ngủ và mệt mỏi | Morgan, Luna, Mira | 44.18 ms (đã nóng) | 1,723.23 ms |

Kết quả vai trò chưa đạt: tin sức khoẻ vẫn chọn người chuyên công việc/nghệ thuật.
Không suy ra chất lượng từ tốc độ hoặc xác suất cao.
Bộ lọc điểm gần đồng đều chỉ là fallback kỹ thuật, không thay được đánh giá chất lượng.
Web production chưa deploy/bật decision. Chưa khuyến nghị thay router local bằng checkpoint này.
Có thể tiếp tục đánh giá hoặc fine-tune bằng dữ liệu lựa chọn người thật của sản phẩm.

Chạy lại worker đã deploy:
~~~powershell
python -X utf8 scripts/check_modal_group_router.py
~~~
Không cần tải weights xuống máy để chạy lệnh này.
