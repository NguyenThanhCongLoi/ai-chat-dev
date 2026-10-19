# JEV / TypeSafe — bật bằng env hoặc CMS

## 1. Cách bật nhanh

Đã có ô trống JEV_API_KEY trong .env của dự án. Điền key thật vào file riêng này, không gửi key vào chat hoặc commit.

```dotenv
JEV_API_KEY=YOUR_TYPESAFE_KEY
JEV_ENABLED=true
JEV_MODEL=jev-latest
JEV_TIMEOUT_SECONDS=5
```

Các cờ JEV_ROUTING_ENABLED, JEV_MODERATION_ENABLED, JEV_EMOTION_ENABLED mặc định true. Chỉ cần key là tự bật, kể cả GROUP_ROUTER_MODE=local. Chỉ định người nói, gọi tên, everyone và follow-up rõ ràng vẫn được ưu tiên, không cần gọi API.

Local đọc riêng các biến JEV/TYPESAFE từ .env ở root; environment đang chạy được ưu tiên. Loader hỗ trợ KEY=value và giá trị có dấu nháy; không hỗ trợ export, nội suy hoặc comment cùng dòng. Docker dùng env_file: deploy/service.env; điền key vào file đó và recreate container.

## 2. CMS

Model → Kết nối & API key → Cấu hình JEV → nhập key → Lưu key.

API base chính xác: https://api.typesafe.ai (không thêm /v1). Không tạo ModelConfig hoặc gán JEV làm model chat; đây là decision API riêng.

Dùng kho credential theo API base đã có: mã hóa Fernet trong DB, GET chỉ trả hint, yêu cầu quyền CMS. Giữ DOCS_PASSWORD/khóa giải mã khi chuyển dữ liệu. Env JEV_API_KEY hoặc TYPESAFE_API_KEY ưu tiên hơn CMS. Xóa key CMS không xóa key env. CMS thay đổi áp dụng ngay cho process hiện tại và được nạp lại lúc startup; deployment nhiều process cần restart đồng bộ.

## 3. Modal

modal_app.py đọc các biến JEV từ .env trên máy deploy và đưa vào Modal Secret runtime; file .env không được bundle vào image. Không cần GPU, không deploy lại router GPU để dùng JEV.

```powershell
python -X utf8 scripts/check_jev.py
python -m modal deploy modal_app.py
```

Probe gọi provider thật bằng một câu giả lập, có thể tính phí; chỉ đọc key env, không nạp key CMS. Nếu dùng CMS, deploy trước rồi cấu hình trong CMS. Không tự deploy/push trong đợt sửa này.

## 4. Đã nối vào đâu?

| Tác vụ | Phạm vi |
| --- | --- |
| Kiểm duyệt đầu vào | Assistant thường/stream, Roleplay thường/stream qua ensure_safe_content |
| Chính sách nhân vật | Tạo/sửa nội dung nhân vật qua enforce_character_policy |
| Worlds | Guard đầu vào và strict guard publication/narration dùng JEV khi bật |
| Chọn người trả lời | Nhóm Roleplay auto: 1 hoặc nhiều người trong roster hợp lệ |
| Cảm xúc | Roleplay dùng cho trạng thái nhân vật và mood observation; Assistant thêm tín hiệu giọng điệu vào prompt |
| Quan hệ | Phân loại sự kiện cho chat một nhân vật; không suy diễn target quan hệ nhóm |

Một request phân loại văn bản gộp chính sách, cảm xúc và loại tương tác. Cache 30 giây, tối đa 256 kết quả đã kiểm tra; cache key là hash, không lưu raw text xuống DB. Trùng text/context được dùng lại; request đồng thời vẫn có thể trùng trước khi cache được ghi. Chọn speaker là request riêng, gửi profile ngắn và 4 lượt gần đây, không gửi private memory/prompt/API key.

Chính sách test: chính trị, tôn giáo thật, tranh chấp địa chính trị/lãnh thổ/sắc tộc, thông tin riêng tư/credentials, tình dục, hướng dẫn gây hại/thù ghét. Đây là chính sách sản phẩm; không coi bất đồng đời thường hoặc xung đột fantasy thông thường là tranh chấp chính trị. Hỗ trợ tâm lý vẫn cho phép lời bộc lộ khủng hoảng; không cho phép hướng dẫn gây hại.

## 5. Lỗi, chi phí và giới hạn

- Kiểm duyệt: lỗi API, quota, response thiếu/sai schema hoặc confidence thấp sẽ chặn yêu cầu. Không tự chuyển sang LLM để cho qua. Key sai có thể khiến gửi chat/tạo nhân vật bị chặn cho đến khi sửa.
- Speaker: lỗi/không chọn được → thuật toán local hiện có. Không gọi Modal GPU.
- Cảm xúc: lỗi/không chắc → heuristic local; background analysis bỏ qua, không gọi LLM phân tích khi JEV emotion đang bật.
- Background JEV không viết recap, reflection hoặc memory summary mới. Heuristic memory/ghim thủ công vẫn tồn tại. Tắt JEV emotion thì đường phân tích LLM cũ hoạt động lại.
- Không thay model trả lời, suggestion, TTS, RAG, dịch hoặc tạo nội dung. JEV không thay LLM viết văn.
- Không bảo đảm kiểm duyệt đúng 100%. Phân loại đa ngôn ngữ mới kiểm tra contract bằng mock; cần đánh giá mẫu thực VI/EN/... trước dùng thật.
- Guard chung này chưa phải lớp kiểm duyệt trước từng token đầu ra SSE. Không tuyên bố mọi đường output/regeneration/upload đều đã được bao phủ.
- Văn bản trên 6000 ký tự được chia đoạn có overlap; trên 60000 bị từ chối. Chia đoạn có thể mất quan hệ xa giữa các đoạn.
- Lưu lượng văn bản thực sẽ được gửi tới TypeSafe khi bật key. Không dùng endpoint trung gian; adapter khóa host chính thức, HTTPS và không follow redirect.
- Giới hạn 8 request HTTP đồng thời/process, timeout mặc định 5 giây, không retry tự động. Cần đo latency/quota thật trước cam kết RPM.
- Để tắt: JEV_ENABLED=false trong env và restart/redeploy.

## 6. Phần nâng cấp chưa làm trong đợt này

Ưu tiên JEV theo ngân sách người dùng. Recap AI, Event Graph, Persona-specific Memory, Initiative Planner, Director, Dynamic Cast và các tính năng còn lại chưa được bổ sung bởi integration này. Các cải tiến ký ức/lore/scene trước đó vẫn giữ.

## 7. Tham chiếu chính thức

- [TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python)
- [Wire schema từ OpenAPI](https://github.com/typesafe-ai/typesafe-sdk-python/blob/main/src/typesafe_sdk/_schemas/models.py)
- [Endpoint constants](https://github.com/typesafe-ai/typesafe-sdk-python/blob/main/src/typesafe_sdk/_core/constants.py)

Dùng HTTP schema chính thức với httpx đã có; không tải SDK/model/GPU mới.

## 8. Kết quả xác minh

- 119 tests đạt: JEV adapter/integration, router, character policy, chat continuity, Worlds/chapter và API contract.
- Frontend TypeScript/Vite build đạt; cảnh báo chunk app lớn vẫn còn.
- Bộ tests/test_app.py khi chạy riêng: 48 đạt, 7 lỗi. Nhiều ca tạo nhân vật chưa có fixture provider moderation (503); một ca avatar kỳ vọng failed trong khi cấu hình fallback trả default-icons. Không thay guard để làm tests xanh.
- Chưa gọi API bằng key thật, chưa đo latency/RPM và chưa deploy/push.

## 9. Ngôn ngữ và suggestion timeout — 16/10/2026

JEV_LANGUAGE_ENABLED mặc định true. Câu hỏi language được gộp với request kiểm duyệt/cảm xúc.
Kết quả chắc chắn >=0.7 dùng cho detect_message_language, tức cả Assistant và Roleplay, bao gồm finalize_suggestions khi model timeout/thiếu câu.
Không chắc/lỗi API trả về heuristic local; nếu không nhận diện được thì dùng ngôn ngữ tài khoản được truyền vào.
Cache nhãn ngôn ngữ 5 phút (lỗi 30 giây), tối đa 256 hash; không lưu raw text.
Nếu chưa có kết quả cache, chỉ gọi decision language với tối đa 2000 ký tự, không gọi LLM viết văn.
Kiểm ngôn ngữ từng câu suggest trả về vẫn dùng local để không phát sinh request JEV cho từng câu.

14 nhãn ngôn ngữ: vi/en/zh/ja/ko/my/km/th/ru/fr/es/de/pt/id, cộng unknown.
Đã thêm bộ câu mẫu Myanmar/Khmer để đủ 7 ngôn ngữ UI. Đây là câu mẫu cố định, không phải suggestion AI mới.
JEV không bảo đảm phân loại đúng tuyệt đối, nhất là câu rất ngắn hoặc nhiều ngôn ngữ.

## 10. Stream đầu ra

Metadata TTS/speech và nhận diện ngôn ngữ từng chunk luôn dùng local (use_jev=False). JEV chỉ phân loại câu user; không được gọi trên mỗi prefix của câu trả lời. Đây là bản sửa cho hiện tượng stream từng chữ chậm sau integration language.
