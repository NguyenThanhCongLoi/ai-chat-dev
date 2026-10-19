# Nơi đưa tài nguyên

Gốc: image/worlds/selene/moonfall/

- backgrounds/: cảnh tĩnh.
- characters/: art bổ sung tùy chọn; reaction mặc định lấy image/react/elf.webp.
- props/: đồ vật trong truyện.
- video/intro/, video/locations/, video/memories/, video/reveals/.
- audio/ambient/, audio/sfx/, audio/narrator/en/, audio/narrator/vi/.
- vfx/: tài nguyên hiệu ứng bổ sung; V1 dùng CSS/SVG.
- mobile/: biến thể crop.

Nhạc nền dùng chung music_backgr/mp3 hoặc nhạc đã upload trong CMS chat thường. Không cần một thư mục BGM riêng cho World.

Manifest có trong character_chat/story_data/echoes_of_moonfall.json và CMS. File chưa có → fallback; không cần tạo file giả rỗng. Đường dẫn là tương đối, chặn traversal và URL ngoài.

Chỉ đặt media được phép public, không upload riêng, credentials hay story script bí mật. Khi deploy bằng image, thêm file rồi build/pull bản mới; tự host có thể mount riêng thư mục World này tại /app/image/worlds/selene/moonfall, không đè toàn bộ thư mục image.

Image/Video thiếu dùng cảnh CSS/SVG; sound thiếu im lặng; API free chat thiếu trả thông báo và không làm mất tiến trình.
