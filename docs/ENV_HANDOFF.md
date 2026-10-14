# Env riêng cho server mới

## Hai file

- deploy/service.env.example: mẫu cấu hình, được commit/push GitHub; không có key thật.
- deploy/service.env: file riêng để bạn điền; Git và Docker build context đều bỏ qua. Compose đọc file này khi khởi động container.

File riêng đã được tạo với credentials trống. Điền bằng editor; không gửi nội dung env vào chat hoặc issue.

## Những trường cần điền

| Biến | Mục đích |
| --- | --- |
| DOCS_USERNAME | Tên đăng nhập CMS |
| DOCS_PASSWORD | Mật khẩu CMS và nguồn khóa giải mã credentials; giữ giá trị cũ khi restore |
| LLM_API_BASE / LLM_MODEL | Endpoint/model mặc định; assignment cụ thể vẫn thuộc CMS |
| LLM_API_KEY | Key gateway mặc định, dùng theo luồng hiện có |
| AIMP_API_KEY | Alias gateway AVIBI; để trống nếu dùng LLM_API_KEY |
| OPENAI_API_KEY | Key kiểm duyệt OpenAI theo cấu hình hiện có |
| PROVIDER_API_KEYS_JSON | Key cho các provider theo URL base, gồm model chat/TTS/ảnh nếu dùng cơ chế ModelConfig |
| CORS_ORIGINS | Origin thực tế của frontend, phân cách bằng dấu phẩy |
| BUILD_VERSION | Nhãn bản triển khai |

Chỉ dùng một dòng JSON cho PROVIDER_API_KEYS_JSON:
~~~env
PROVIDER_API_KEYS_JSON='{"https://gateway.avibi.ai/v1":"REPLACE_WITH_KEY","https://api.openai.com/v1":"REPLACE_WITH_KEY"}'
~~~

Ví dụ trên minh họa cú pháp; không dùng placeholder như key thật. File mẫu để '{}' nghĩa là chưa khai báo mapping.

URL phải khớp API base của model trong CMS; hệ thống bỏ dấu / cuối và chuẩn hóa giống registry hiện có. Mỗi API base dùng một key trong mapping. Nếu các model cùng base cần key khác nhau, giữ key riêng mã hóa trong CMS và không khai báo mapping cho base đó.

Thứ tự chọn key:
1. Key explicit trong PROVIDER_API_KEYS_JSON cho base tương ứng.
2. Key riêng của model đã mã hóa trong CMS.
3. Credentials của base/gateway đã mã hóa trong CMS.
4. Env fallback đã hỗ trợ trong code cho gateway AVIBI.

Không tự xuất/decrypt key cũ từ CMS ra file plaintext. Backup vẫn giữ encrypted credentials; bạn có thể điền mapping env mới để override khi chuyển server. Cấu hình model, prompt và voice ID vẫn nằm trong DB; env không thay thế dữ liệu này.

DOCS_PASSWORD đang được ưu tiên hơn ADMIN_ENCRYPTION_KEY trong code. Bản này chưa tách mật khẩu CMS và khóa giải mã thành hai cơ chế riêng; thêm ADMIN_ENCRYPTION_KEY không tự giúp đổi DOCS_PASSWORD cũ.

## Điền và chuyển

1. Điền deploy/service.env tại máy bạn hoặc tạo trực tiếp trên server mới từ file example.
2. Chuyển file riêng qua SCP/SFTP hoặc secret manager/kênh bàn giao riêng.
3. Đặt file tại deploy/service.env trên server mới.
4. Linux: chmod 600 deploy/service.env.
5. Chuyển backup DB/media riêng, không đưa chúng vào env hoặc Git.
6. Chạy docker compose up -d --build; khi chỉ đổi env dùng docker compose up -d --force-recreate companion. docker compose restart đơn thuần không nạp lại env_file.

Nếu giá trị có #, $, khoảng trắng hoặc ký tự đặc biệt, dùng cú pháp quote phù hợp env_file; single quotes giữ giá trị literal. Không chèn key vào VITE_* hoặc source frontend vì chúng sẽ tới browser.

## Những gì không dùng trong bản CPU

Không chuyển MODAL_TOKEN_ID, MODAL_TOKEN_SECRET hoặc AVATAR_MODAL_FUNCTION vào env này; entrypoint sẽ từ chối. GPU worker code giữ nguyên và không đổi; secrets GPU chỉ cần cho đợt chuyển GPU sau này.

Không tự thêm DATABASE_URL=postgresql...: bản này vẫn SQLite, chưa có driver/migration production PostgreSQL.

## Kiểm tra không tiết lộ secrets

~~~bash
git check-ignore deploy/service.env
git ls-files deploy/service.env
~~~

Lệnh đầu phải trả đường dẫn; lệnh thứ hai không được trả file. Khi lỗi startup, chương trình chỉ báo tên biến/cấu trúc JSON, không in payload key.

Không gửi output docker compose config khi env đã có credentials vì lệnh có thể hiển thị giá trị đã resolve.
