# Rà soát và dọn source — 05/10/2026

## Phạm vi

Đã đối chiếu module Python, route FastAPI, import frontend, các chỗ gọi trong test/script, CSS được nạp, dependency npm và mock UI. Việc xoá chỉ áp dụng cho phần không có chỗ gọi trong dự án hoặc không được nạp. Không xoá database, asset nhân vật, file upload, log hay cấu hình CMS.

## Đã dọn

- Import/type/hàm không dùng trong CMS và Assistant.
- State chọn nhân vật cũ, bộ lọc danh mục cũ và hàm tạo mirror không còn được UI gọi trong Role Play. API mirror và luồng tạo nhân vật hiện tại vẫn giữ.
- Helper gọi lại câu trả lời trùng và helper nhận diện hostname voice không có nơi gọi.
- Import Python không dùng; các export tương thích của engine/db vẫn giữ.
- `assistant/prototype-layout.css`: stylesheet prototype không được import.
- Rule thanh prototype không còn render và khai báo nền login bị thay thế. Nền mặt trời/mặt trăng đang dùng nằm trong `assistant/login-background.css`.
- Dependency `lottie-web`: frontend hiện dùng canvas/sprite; giữ các asset loading và script tạo asset.
- Cấu hình model mặc định cũ trong mock; mock chọn model hiện tuân theo `user_pick` của từng trợ lý.

## Tính năng được giữ để tiếp tục phát triển

- Form, nút, handler và dữ liệu mock **Tạo trợ lý AI** trong CMS.
- Tab **Thống kê** và type dữ liệu thống kê của trợ lý.
- Backend hiện chỉ có GET hồ sơ và PUT hồ sơ cho các tác vụ đã biết. Chưa có POST tạo trợ lý tuỳ biến; frontend Assistant còn dùng danh sách mode cố định.
- Hồ sơ backend chưa tổng hợp số liệu `stats` từ log thực tế. Tab thống kê vẫn hiện trạng thái chưa có số liệu; mock có dữ liệu mẫu.
- Các prompt, schema, API và export công khai vẫn giữ. Không xoá route vì chưa tìm thấy chỗ gọi từ UI: chúng còn có thể được script hoặc client API sử dụng.
- Giữ scripts kiểm tra gateway/Modal, mock server, scripts tạo asset và tài liệu kỹ thuật.

## Cách ngăn mã thừa quay lại

`frontend/tsconfig.json` bật `noUnusedLocals` và `noUnusedParameters`. Build sẽ báo lỗi khi có import, biến hoặc tham số không dùng. Tính năng đang phát triển cần giữ được đường gọi hoặc module export rõ ràng.

## Kiểm chứng

- Build TypeScript/Vite và kiểm tra cú pháp mock server.
- Chạy các test backend: app, voice, lỗi gateway và định dạng Role Play.
- Kiểm thử phát hiện `engine.time` vẫn là export dùng bởi test gateway; import này được giữ lại để bảo toàn tương thích.
- Không chạy stress test hoặc gọi model ngoài; chưa kiểm chứng bản deploy đang chạy.
