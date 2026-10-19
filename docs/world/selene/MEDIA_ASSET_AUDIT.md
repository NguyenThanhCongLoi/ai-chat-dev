# Media Selene hiện tại

Đã dọn bộ media prototype và các video đã được thay thế. Manifest runtime hiện trỏ tới bộ chính thức.

## Video đang giữ

| File | Asset ID |
| --- | --- |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/endings/hidden.webm | ending_video_hidden |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/endings/release.webm | ending_video_release |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/endings/restore.webm | ending_video_restore |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/endings/transfer.webm | ending_video_transfer |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/transitions/gate_opens.webm | enter_ruins_video |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_01.webm | memory_video_01 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_02.webm | memory_video_02 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_03.webm | memory_video_03 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_04.webm | memory_video_04 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_05.webm | memory_video_05 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_06.webm | memory_video_06 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_07.webm | memory_video_07 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/memories/memory_08.webm | memory_video_08 |
| image/worlds/selene/moonfall/video/intro/moonfall_intro.webm | moonfall_intro |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/events/academy_collapse_selene.webm | story_academy_collapse |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/events/archive_awakens.webm | story_archive_awakens |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/events/echo_girl.webm | story_echo_girl |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/events/ev_ch1_arrow_trap_v6.webm | story_ev_ch1_arrow_trap_v6 |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/events/mirror_desync.webm | story_mirror_desync |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/events/pale_moon_manifestation.webm | story_pale_moon_manifestation |
| image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/events/seal_trap.webm | story_seal_trap |
| image/worlds/hub/video/selene_intro_20261018_from17.webm | hub:selene_intro_1080 |

## BG và props

- BG chính thức: image/worlds/selene/moonfall/backgrounds/echoes_bg_16x9/.
- Props đang phục vụ: image/worlds/selene/moonfall/props/prepared/.
- Ảnh nhân vật đang phục vụ: characters/selene_*.webp và characters/cutouts/.
- Không thiếu ảnh/video trong manifest mặc định và sảnh World.
- Ambient/SFX chưa cung cấp là audio tùy chọn, có silent fallback.

## Kiểm tra và lịch sử dọn

- Chạy: python -B scripts/audit_selene_media.py.
- Danh sách xóa và phạm vi bảo vệ: CLEANUP_20261019.md.
- Chi tiết từng file, dung lượng và SHA-256: artifacts/cleanup/*-removed.json.
- Việc dọn không xóa database, API key, backup hay cache TTS đang được sử dụng.
