# Bản dịch giao diện

## Phạm vi

- Dịch nhãn UI, menu, nút, placeholder, thông báo và câu chào Assistant.
- Không dịch tên, tính cách, prompt, tags của nhân vật hoặc nội dung lịch sử chat. Câu giới thiệu ngắn và mô tả trên thẻ được dịch theo ngôn ngữ chọn, không sửa dữ liệu gốc.
- Role Play: câu chào gốc khi chọn tiếng Việt; bản tiếng Anh dùng chung cho mọi ngôn ngữ khác. Bản tiếng Anh được cache phía server theo nhân vật và hash câu chào gốc. Sửa câu chào sẽ tạo bản dịch mới. Giọng đọc lấy đúng biến thể đang hiển thị.
- Assistant: câu chào theo ngôn ngữ chọn. Các câu chào mặc định en/zh/ja/ko/my đã lưu sẵn.

## File

- `frontend/src/locales/{en,zh,ja,ko,my}.json`: bản dịch, khóa là chữ giao diện gốc.
- `frontend/src/locales/catalog.json`: danh mục tự thu thập từ mã UI, không chứa nội dung nhân vật trong database.
- `frontend/scripts/ui-locales.cjs`: thu thập và dịch tăng dần bằng Avibi.
- `frontend/src/uiLocales.ts`: đóng gói sẵn cả năm bộ dịch trong ứng dụng; đổi ngôn ngữ không tải thêm lazy chunk.
- `frontend/src/UiLanguageLoading.tsx`: màn hình chờ mà không tháo iframe/chat đang mở.

## Tạo toàn bộ bản dịch bằng Avibi

Chạy trong thư mục `frontend`, với Node 24 hoặc mới hơn:

```powershell
$uiLocaleKey = Read-Host "Avibi API key" -AsSecureString
$env:UI_I18N_API_KEY = [System.Net.NetworkCredential]::new("", $uiLocaleKey).Password
$env:UI_I18N_API_BASE = "https://gateway.avibi.ai/v1"
$env:UI_I18N_MODEL = "openai/gpt-4.1-mini"
npm run i18n:update
npm run i18n:check
npm run build
Remove-Item Env:UI_I18N_API_KEY
```

Dùng model khả dụng trên tài khoản Avibi của bạn. Script có thể tính phí các lượt dịch. Key chỉ dùng trong tiến trình build, không có tiền tố `VITE_`, không được ghi vào JSON hay gửi lên browser.

Bản dịch đã hoàn tất được lưu sau mỗi batch. Nếu HTTP 401/403, script dừng ngay và giữ các batch đã lưu. Sửa khóa rồi chạy lại sẽ tiếp tục phần thiếu; không dịch lại bản đã có. Khi sửa chữ nguồn, khóa mới tự xuất hiện trong danh mục và được dịch. Có thể chỉnh thủ công file JSON để duyệt cách dùng từ; bản đã lưu không bị ghi đè.

## Tự động khi build / CI

`npm run build` chạy `prebuild`. Nếu có `UI_I18N_API_KEY`, bước này tự thu thập chữ mới, dịch phần thiếu, lưu JSON rồi build. Nếu danh mục đã đầy đủ, không gọi model. Commit các file JSON để người sửa UI không cần key khi chỉ build bản đã dịch.

`npm run i18n:check` thất bại nếu còn thiếu bản dịch hoặc placeholder không khớp. Đặt `UI_I18N_STRICT=1` trong CI để chặn release khi bản dịch thiếu và không có key.

Để giữ build hiện tại hoạt động, chế độ thường chỉ cảnh báo khi thiếu bản dịch và không có key riêng cho dịch. Trong lúc các file chưa đầy đủ, UI tải phần còn thiếu qua endpoint dịch; request được chia tối đa 120 chữ. UI chỉ mở sau khi toàn bộ danh mục vượt qua kiểm tra, không mở nếu dịch thiếu hoặc lỗi. Sau khi `i18n:update` hoàn tất, năm ngôn ngữ trên dùng bản dịch đóng gói, không gọi gateway khi user chọn. Danh sách chọn chỉ hỗ trợ vi/en/zh/ja/ko/my; lựa chọn cũ ngoài danh sách quay về vi.

## Trạng thái hiện tại

Hiện năm bộ dịch UI đã đầy đủ: 480 mục × 5 ngôn ngữ, gồm slogan Role Play. Giới thiệu nhân vật mới vẫn dùng API dịch khi chưa có cache hợp lệ; bước này cần model và credential hợp lệ trên server.

Tổ chức theo file ngôn ngữ và tải khi cần tham khảo:
- https://github.com/lobehub/lobehub/tree/main/locales
- https://www.i18next.com/principles/fallback
- https://react.i18next.com/latest/translation-render-prop

Dự án tiếp tục dùng bộ dịch hiện có, không thêm thư viện i18next.


## Mở giao diện sau khi dịch hoàn tất

Assistant và Role Play cùng kiểm tra toàn bộ danh mục trước khi mở giao diện. Không còn bỏ qua lỗi rồi hiển thị bản dịch thiếu. Kiểm tra gồm giá trị không rỗng, số lượng response, placeholder, chữ gốc chưa dịch, bản tiếng Anh dự phòng và hệ chữ cho Trung/Nhật/Hàn/Myanmar. Các nhãn kỹ thuật/tên thương hiệu được giữ nguyên.

Màn hình chờ khóa cả chuột và bàn phím bằng inert; trạng thái từ các iframe được đồng bộ lên workspace. Chỉ mở sau khi React/DOM áp dụng bản dịch và qua hai animation frame. Nếu lỗi: Thử lại hoặc quay về Tiếng Việt (vi). Không mất nội dung chat.

Cập nhật phạm vi theo yêu cầu mới: câu giới thiệu ngắn và mô tả dùng trên thẻ nhân vật cũng được dịch theo ngôn ngữ chọn, cache theo nội dung gốc và ngôn ngữ. Không sửa Character Card, tên, tính cách, prompt hay lịch sử chat. Role Play vẫn dùng câu chào tiếng Anh ngoài tiếng Việt.

Các kiểm tra trên xác nhận bản dịch đầy đủ về kỹ thuật; chất lượng/cách dùng từ vẫn cần duyệt bản dịch. Bản dịch chưa hoàn tất hoặc gateway lỗi sẽ chặn mở ngôn ngữ đó.


## Khi model trả bản dịch không hợp lệ

Script giữ lại từng trường ngôn ngữ hợp lệ, rồi thử lại tối đa ba lượt cho các trường thiếu/sai. Lượt cuối tách từng chữ nguồn để giảm lỗi định dạng. Sau ba lượt vẫn sai, script ghi rõ chữ nguồn và mã ngôn ngữ, tiếp tục các mục khác rồi kết thúc với lỗi để không coi bản dịch thiếu là hoàn tất. Chạy lại chỉ xử lý phần còn thiếu. Ký hiệu như × hoặc số thuần được giữ nguyên, không yêu cầu có ký tự Trung/Nhật/Hàn/Myanmar. Các lỗi HTTP 400/401/403/404/429 dừng ngay.

Các lượt thử lại có thể tính phí gateway; không thử lại bản dịch đã lưu và hợp lệ.

## Khi Role Play báo tải ngôn ngữ thất bại

Bộ UI đóng gói và câu giới thiệu nhân vật là hai bước riêng. Câu giới thiệu vẫn cần dịch runtime khi chưa có cache. Mô tả dài được chia thành phần tối đa 900 ký tự; mỗi request tối đa 6 phần/1.800 ký tự. Các phần thành công được lưu ngay để thử lại không mất tiến độ. Cache được tách theo tài khoản/ngôn ngữ.

Backend chọn model đã phân công Suggestion, hoặc Compiler, hoặc model trả lời mặc định đang hoạt động. API key nhập trong Terminal để build không tự cập nhật API key CMS/Modal trên server. Nếu thông báo nói khóa model dịch trên server không hợp lệ, cần sửa credential của gateway/model trong CMS.

Endpoint trả mã lỗi riêng: credentials, model_not_assigned, timeout, output_limit, gateway_error, invalid_translation. Không trả lỗi gateway thô/khóa API ra frontend. Frontend vẫn chặn giao diện khi dịch thiếu, nhưng hiển thị rõ lỗi ở giao diện hay câu giới thiệu.

Nhãn tab có số lượng dùng khóa chữ gốc rồi giữ số đếm riêng, ví dụ Nhân vật của tôi (6) thành My characters (6). Không cần tạo bản dịch riêng cho từng số lượng.


### Runtime introduction translation repairs

- Language code `my` is explicitly Burmese (Myanmar) in the server translation prompt.
- The server validates target writing systems and preserved placeholders before reusing or saving cached translations. Invalid old cache entries are removed automatically.
- A malformed batch or invalid field is retried once as an individual item. Valid fields are retained. Authentication and network errors are not retried by this repair path.
- If the second result is still invalid, the language gate remains closed and reports the failure. Script validation does not prove the linguistic quality of a translation.


### Loading after deployment

The five supported UI dictionaries are now eager imports inside the main app bundle. Switching language no longer fetches a separate hashed locale chunk that may belong to an earlier deployment. This adds about 50 KB gzip to the initial app bundle. Runtime translation of new character introductions still uses the server cache and translation endpoint. Invalid translation results and network errors have distinct error codes.


## Khmer / Campuchia (km)
- Bộ dịch giao diện Khmer đã lưu sẵn ở frontend/src/locales/km.json, bao gồm 505 mục hiện có, slogan và câu chào Assistant.
- Hiển thị trong danh sách ngôn ngữ là ភាសាខ្មែរ (km); gói được đóng cùng frontend để dùng lại, không cần gọi API dịch giao diện khi lựa chọn.
- i18n:update/build/check hỗ trợ km và kiểm tra hệ chữ Khmer cùng placeholder.
- Backend hỗ trợ dịch giới thiệu nhân vật sang Khmer và lưu cache theo nội dung.
- Nhận diện ngôn ngữ lượt chat hỗ trợ chữ Khmer; voice vẫn chỉ hỗ trợ Việt/Anh.
- Font dùng Khmer UI/Noto Sans Khmer nếu có, với system font dự phòng.
- Cần duyệt cách dùng từ bằng người bản ngữ trước khi phát hành rộng rãi; kiểm tra kỹ thuật không chứng minh chất lượng ngôn ngữ.
