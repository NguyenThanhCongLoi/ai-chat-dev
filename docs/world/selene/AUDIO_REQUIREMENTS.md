# Âm thanh

BGM: dùng đúng playlist chat thường, quản lý trong CMS nhạc nền hiện có. CMS World chọn shared:<track-id> hoặc shared: tự dùng bài đầu. Không copy BGM. Có crossfade ~0,9 s và duck khi đọc thoại.

Ambient loop ở audio/ambient/: ruins_wind, underground_hum, forest_night, archive_room, memory_space, moon_temple; OGG/MP3, khoảng 20–60 s, seamless, dịu hơn speech, không chứa giọng/chữ.

SFX audio/sfx/: rune_activate, magic_pulse, stone_move, stone_door, clue_found, memory_trigger, memory_reveal, secret_reveal, location_unlock, chapter_complete, seal_break. OGG/MP3, 0,3–3 s (stone door tối đa 5 s), không loop, transient nhẹ.

Narration: mặc định provider TTS, Voice ID VI/EN riêng trong CMS World. audio/narrator/en và vi dành cho bản thu sau; V1 chưa tự ưu tiên file thu sẵn. Không cần tự cung cấp file audio nhân vật.

Selene: model/Voice ID/cấu hình ngôn ngữ của chat thường. Không có clone/voice override mới trong World.

Mixer: master/music/ambient/effects/narrator/character riêng; voice duck nhạc và ambient. Mức UI là tương đối, không phải chứng nhận loudness. Gợi ý master audio -16 LUFS, peak ≤ -1 dBTP, ambient thấp hơn speech. Browser có thể yêu cầu gesture để phát; thiếu audio vẫn tiếp tục truyện.

VI/EN voice; thought/system tuyệt đối không có TTS. Bật auto-reader là lựa chọn, mặc định tắt.
