# Video đã tích hợp

Đã nhận đủ 8 clip. Bản gốc MP4 ở image/worlds/selene/ được giữ nguyên. Runtime dùng WebM VP9, tối đa 1280×720, 24 fps, không audio.

- video/intro/moonfall_intro.webm — WORLD_INTRO.
- video/locations/enter_ruins.webm — LOCATION_ENTER cho outer_ruins.
- video/memories/memory_space.webm — backdrop ký ức, có loop.
- video/memories/memory_transition.webm — MEMORY_RECONSTRUCTION_START (chuẩn bị).
- video/memories/memory_exit.webm — MEMORY_RECONSTRUCTION_END (chuẩn bị).
- video/reveals/chapter_complete.webm — CHAPTER_COMPLETE.
- video/reveals/seal_activation.webm — MAGIC_SEAL_ACTIVATE (chuẩn bị).
- video/reveals/deep_vault_awaken.webm — MAJOR_REVEAL / VAULT_AWAKEN (chuẩn bị).

Đường dẫn tương đối với image/worlds/selene/moonfall/. Xem ASSET_MAPPING.md và manifest CMS.

CinematicPlayer dùng manifest và registry, không có đường dẫn MP4 trong scene. Player không cấp manh mối/ký ức hay hoàn thành nhiệm vụ. Backend đã lưu state trước khi player chạy. Clip lỗi dùng nền thật + VFX nhẹ; intro có bộ đếm/skip độc lập nên không chặn tương tác. Reduced motion/save-data bỏ video.

Nội dung lời kể/phụ đề/hội thoại nằm trong các layer riêng, không được đưa vào video. BGM giảm âm trong lúc clip chạy; ambient không bị tắt theo cinematic.

Chỉ một clip địa điểm có khả năng tiếp theo được preload metadata. Intro không phát lại sau intro_seen. Các clip chương sau có trong manifest nhưng không tự mở khóa chương sau.

Cập nhật video: python scripts/prepare_world_videos.py. FFmpeg cần trên PATH, --ffmpeg hoặc .tools/media-python.
