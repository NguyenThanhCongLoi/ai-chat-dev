# Ver1 và bản update

## Các mốc Git

| Mốc | Nội dung | Cách dùng |
| --- | --- | --- |
| `main` / `ver1` | Bản hiện tại không có companion video | Bảo trì ver1 |
| `v1.0.0` | Mốc ver1 cố định | Đóng gói, khôi phục, deploy đúng bản này |
| `update` | Giữ companion video elf và các thay đổi phát triển tiếp | Làm bản update |

Ver1 vẫn có ảnh cảm xúc elf, các sửa lỗi chat/voice và reset cảm xúc khi xoá chat. Chỉ phần companion video, nút mắt và video normal/talk được tách ra. Bộ chọn Laya vẫn có trong source nhưng mặc định tắt (`GROUP_ROUTER_MODE=local`).

Không di chuyển tag `v1.0.0` khi sửa code. Nếu phát hành bản vá ver1, tạo tag mới như `v1.0.1`.

## 1. Đóng gói ver1 khi đang ở nhánh update

Chạy PowerShell trong repo gốc:

```powershell
cd D:\ai_chat_char
python -X utf8 scripts/package_ver1.py
```

ZIP xuất vào `backups/releases/`. Script lấy code từ tag `v1.0.0`, không lấy code đang sửa ở nhánh hiện tại. `RELEASE_INFO.json` trong ZIP ghi commit cụ thể. ZIP không chứa `.git`, dependencies, frontend/dist, database hay secrets.

Để đóng gói riêng dùng deploy, kèm nhạc gốc đang có trên máy:

```powershell
python -X utf8 scripts/package_ver1.py --include-local-music
```

ZIP có nhạc chỉ dùng riêng cho deploy; không đăng công khai vì giấy phép nhạc không cho phân phối lại file gốc. File nhạc được lấy từ `music_backgr/mp3` ở máy hiện tại, không được đóng băng trong Git. Nếu thiếu thư mục nhạc, script báo lỗi trước khi tạo ZIP.

## 2. Lấy ver1 về thư mục riêng

Chọn thư mục chưa tồn tại:

```powershell
git clone --branch v1.0.0 --single-branch https://github.com/NguyenThanhCongLoi/ai-chat-assistants.git D:\ai_chat_char_ver1
cd D:\ai_chat_char_ver1
git describe --tags --exact-match
git status --short
```

Kết quả phải là `v1.0.0` và không có thay đổi. Trạng thái detached HEAD là bình thường vì đang dùng tag cố định. Giữ repo gốc ở nhánh update để phát triển, không cần xoá code thử nghiệm hay đổi nhánh trong thư mục deploy.

Cũng có thể giải nén ZIP ở bước 1 vào thư mục riêng; không có Git nhưng có `RELEASE_INFO.json` để đối chiếu phiên bản.

## 3. Build UI và deploy ver1

Nếu clone từ GitHub, chép thư mục `music_backgr/mp3` từ máy cũ vào bản clone nếu muốn kèm nhạc nền. Secrets và dữ liệu trong Modal workspace phải được cấu hình riêng; clone Git không khôi phục chúng.

```powershell
cd D:\ai_chat_char_ver1
python -m pip install -e ".[modal]"
$env:PATH="D:\Chatbot\.tools\node-v24.21.0-win-x64;$env:PATH"
$env:GROUP_ROUTER_MODE="local"
python -X utf8 -m modal profile current
python -X utf8 -m modal deploy modal_app.py
```

Lệnh deploy tự chạy build UI. Nếu muốn kiểm tra UI trước:

```powershell
cd D:\ai_chat_char_ver1\frontend
npm.cmd install
npm.cmd run build
cd ..
```

Nếu Node nằm ở chỗ khác, sửa PATH theo vị trí `node.exe` và `npm.cmd`. Kiểm tra Modal profile/workspace trước deploy để tránh lên nhầm tài khoản. Worker reaction cần được deploy riêng bằng `python -X utf8 -m modal deploy modal_reactions.py` nếu chưa có hoặc đã thay đổi worker. Không cần deploy worker Laya khi router đang ở chế độ local.

## 4. Phát triển bản update

```powershell
cd D:\ai_chat_char
git switch update
git pull --ff-only origin update
```

Sửa và commit trên nhánh này. Không chạy deploy update lên production để thử nghiệm: nhánh Git không tự tách app, secrets hay database; hiện tên Modal app/volume vẫn giống nhau. Muốn chạy server dev cần cấu hình app/volume hoặc workspace dev riêng trước.

## 5. Quay lại bản ổn định và sao lưu

Deploy từ thư mục clone tag `v1.0.0` ở bước 2–3 là quay lại đúng code ver1. Không dùng `git reset --hard` trong thư mục đang phát triển nếu chưa lưu các thay đổi.

Git chỉ sao lưu source và các asset được track. Database Modal, file upload trong volume, secrets và nhạc gốc phải sao lưu riêng. Deploy code cũ không tự khôi phục dữ liệu và không đảo ngược thay đổi schema đã thực hiện ở bản mới.
