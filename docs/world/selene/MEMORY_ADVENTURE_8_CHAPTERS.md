> Trang chủ AI Companion: giữ màn hình chờ RolePlayLoadingCat và theme hiện có sau khi xác thực. Chờ font, gói UI World, video intro tải đủ và audio ngôn ngữ hiện tại trước khi mở dịch vụ. Thiếu audio đã chuẩn bị hoặc lỗi tải sẽ giữ màn chờ + nút thử lại, không tự bỏ qua readiness. Khi World bị tắt thì không chờ media World. Không preload toàn bộ chương tương lai. Đã kiểm thử browser bằng cách giữ request video: trang chủ không xuất hiện trước khi request được hoàn tất.

> Cập nhật tiếp 18/10: lưu cấu hình World hoặc lời intro tự kích hoạt chuẩn bị VI/EN ở nền. Audio GET chỉ đọc cache trên volume, không gọi TTS. URL audio có phiên bản phụ thuộc lời/giọng/provider, tránh phát bản cũ; trang chủ prefetch audio cho ngôn ngữ đang dùng (VI hoặc EN), video tải trước như cũ. CMS vẫn có nút chuẩn bị lại khi provider lỗi. World tự bật nhạc mỗi lượt vào, nhường intro có nhạc, tự thử phát lại khi user tương tác nếu trình duyệt chặn autoplay. Tài khoản user_accounts.is_admin=1 và status=active được mở mọi chương trong preview riêng; CMS Basic login không tự cấp quyền admin cho tài khoản client. Preview không xuất ký ức sang chat thật.

> Cập nhật 18/10: intro tải đủ video thành Blob trong phiên trình duyệt và chờ tải/tạo xong các câu narration trước khi phát. Nếu TTS lỗi, tiếp tục với phụ đề và báo thiếu giọng; không đứng chờ vô hạn. CMS có nút “Tạo sẵn giọng intro VI/EN”, dùng provider/voice đã lưu để materialize cache DATA_DIR/world_intro_audio. Đổi nội dung/voice sẽ tạo cache mới. Lần đầu vẫn cần đợi tải video; không bảo đảm tránh mọi lag do khả năng giải mã thiết bị. Đã sửa request lưu CMS World không gửi Bearer token client đè lên Basic auth CMS.

> Cập nhật asset: đã tách đủ 8 ảnh location từ memory_locations_showcase.mp4 (17 giây), lấy tại 1.5/3.5/5.5/7.5/9.5/11.5/13.5/15.5 giây, tránh crossfade. File WebP 1280×720 trong backgrounds/memory_locations, tổng khoảng 1.87 MB. Script: scripts/extract_memory_locations.py. Seed mới đã map M01–M08 tới memory_location_01–08. Config CMS/snapshot đã lưu không bị ghi đè; nếu vẫn dùng nền cũ, gán memory.background trong CMS bằng các ID trên và kiểm path manifest đổi .jpg sang .webp khi không có JPG. Phần “còn chờ 8 ảnh” bên dưới là trạng thái trước khi nhận slideshow.

# Echoes of Moonfall — bản 8 chương

Cập nhật 17/10/2026. Bản thử nghiệm desktop; chưa deploy/push, chưa chứng nhận production.

## Đã làm

- Engine v2 độc lập: 8 chương, hotspot, vật phẩm, 6 kiểu câu đố, 3 mức gợi ý, lựa chọn, xác nhận kết và 4 kết truyện.
- Save theo user/run; kiểm quyền, revision/CAS, request receipt. Video không quyết định tiến trình; bỏ qua hoặc lỗi video vẫn chơi tiếp.
- Stats trust/truth/understanding/sacrifice, flags, inspected, solved, inventory, choices, M01–M08, echoes, lore, chapter bookmarks và ending. M08 chỉ mở ở kết ẩn.
- Archive 5 nhóm; reflection, chronicle và lời trở về chat nhận dữ kiện đã mở. Reflection có fallback biên soạn sẵn khi provider lỗi.
- Trở về chat có lựa chọn đồng bộ structured memory. Phần triển khai này không sửa engine chat thường/cá tính nhân vật.
- Narration, speech, thought, system tách loại. Hàng đợi đọc lời kể rồi thoại; thought không đọc.
- CMS /worlds/admin: model, narrator từ API, nhạc chung, điều kiện mở, 8 chương, scenes/hotspots, puzzle, lựa chọn, localization, manifest, prompt phiên bản, kết truyện, validation, preview riêng.
- JSON editor cần bấm Áp dụng bản nháp JSON rồi Lưu cấu hình World. Preview không xuất memory/message sang chat thật.
- Nội dung truyện VI/EN; năm ngôn ngữ khác có EN fallback hiện trên UI, chưa dịch toàn bộ.

## Asset và code

- Manifest: character_chat/adventure/loader.py; chapter data: character_chat/story_data/moonfall_arc/ch01.json … ch08.json; luật/kết/prompt: arc.json trong cùng thư mục.
- Intro image/video/intro.mp4 → image/worlds/hub/video/selene_intro_1080.webm: nguồn 1080p khoảng 69 giây, giữ nhạc.
- Memory 01–08 → image/worlds/selene/moonfall/video/memories/memory_01.webm … memory_08.webm.
- M01/M04 nguồn 720p, 9 giây, camera đã có trong clip; không zoom chồng hoặc phóng giả thành 1080p. M06 dùng bản sửa memory_06_memory_erasure.mp4.
- Memory clip bỏ audio nguồn để không chồng TTS. Tái dùng background, props, Selene expressions hiện có.
- background_pack_labeled.jpg đã tách art thành moonbrook_rooftop.webp, council_chamber.webp, memory_corridor.webp, pale_moon_chamber.webp.
- Script chuyển đổi/kiểm kê: scripts/prepare_memory_arc_assets.py. Báo cáo: artifacts/memory-adventure/assets.json.

## Hiệu ứng từ spec trong chat

Không cần file frontend_effects.md riêng. MemoryLocationEffects.tsx dùng một canvas 2D: 40 bụi bạc; 50 hạt rooftop; 30 hạt và hai rune; 45 tàn lửa; 25 bụi archive; 18 rune + 35 mảnh erasure; 40 mảnh lunar; 20 cánh hoa + 12 bokeh. Có vignette/grain, light/glow, entry fragments và burst MAGIC/CLUE/MEMORY theo event.

Giới hạn 30 FPS, tối đa 60 hạt kể cả transition; giảm nửa khi đo dưới 25 FPS; pause khi tab ẩn/offscreen, tôn trọng reduced motion/data saver. Không WebGL/will-change/translateZ hack. Canvas 2D không bảo đảm trình duyệt/driver tuyệt đối không dùng GPU nội bộ.

Chưa dựng đầy đủ méo toàn ảnh whisper distort, shake toàn scene và fade trắng kết theo timeline chính xác. Cần ảnh location thật để căn tâm ánh sáng/rune/hotspot. Không khẳng định công thức đã khớp từng pixel.

## Còn chờ

Người dùng xác nhận chưa upload 8 ảnh. Thư mục đã chuẩn bị: image/worlds/selene/moonfall/backgrounds/memory_locations/

1. loc_01_academy_corridor.jpg
2. loc_02_moonlit_rooftop.jpg
3. loc_03_ritual_chamber.jpg
4. loc_04_collapsing_academy.jpg
5. loc_05_council_archive.jpg
6. loc_06_erasure_chamber.jpg
7. loc_07_lunar_seal.jpg
8. loc_08_peaceful_rooftop.jpg

ID manifest: memory_location_01 … memory_location_08. Loader chọn ảnh mới cho lượt mới khi file tồn tại; thiếu thì dùng background hiện có. CMS v2 đã lưu/snapshot đang chơi không bị tự ghi đè; admin có thể gán memory.background bằng ID mới.

TTS còn cần provider/key, narrator VI/EN và giọng Selene trong CMS chat thường. Ambient/SFX chưa có thì im lặng. Chưa gọi provider thật khi test.

## Cách thử

1. Bật WORLD_DEMO_ENABLED=true và WORLD_ADVENTURE_ENABLED=true.
2. Build frontend bằng npm run build trong frontend (npm ci nếu thiếu dependencies), chạy/deploy theo quy trình hiện có.
3. /worlds/admin chọn đúng card Selene nguồn, model, giọng, điều kiện mở rồi lưu.
4. Chat riêng Selene đủ điều kiện → Cốt truyện → chương 1; hoặc mở bản đồ từ trang chủ.
5. Khám phá cả hai vị trí, quan sát đủ hotspot, ghép rune, chọn phản hồi, tiếp tục memory, sang chương kế.
6. Chương đã hoàn tất xem lại không nhận thưởng lặp; chương đang chơi có bookmark.
7. Return to Chat và đồng ý đồng bộ nếu muốn Selene nhớ sự kiện.

Tests DB cô lập: DATABASE_URL=sqlite://; pytest tests/test_memory_adventure.py tests/test_moonfall.py -q. Browser: thêm RUN_MOONFALL_BROWSER=1; pytest tests/test_adventure_browser.py -q.

Backend đã thử hết 8 chương qua HTTP, 4 kết ở engine, scope user và memory bridge. Browser thử chương 1 → archive → CMS chương 8, lưu screenshot trong artifacts/memory-adventure. Chưa nghiệm thu thủ công cả 8 chương/provider thật hoặc đo FPS trên máy yếu.

## Dọn dẹp

Đã xóa hai derivative intro cũ không còn dùng (~59.9 MB); danh sách artifacts/memory-adventure/cleanup.json. Giữ MP4/PNG nguồn dùng bởi script và engine/media v1 còn phục vụ snapshot cũ. Không xóa asset chat thường, nhạc chung, card/prompt/lore CMS hoặc save user.

## Lời dẫn và gợi ý theo nhiệm vụ (18/10/2026)

Đã thay 62 câu khám phá cho cả 8 chương. Lời dẫn xác định điều đáng quan sát; Selene gợi một bước thử, giữ giọng tò mò và thận trọng. Lời thoại từng vật phẩm riêng biệt, không còn dùng một câu chung cho cả cảnh.

| Chương | Hướng dẫn khi khám phá |
| --- | --- |
| 1 | Kiểm tra cổng và bậc đá; sang tàn tích đối chiếu văn tự ở pho tượng với các rune trên tường. |
| 2 | Quan sát chiếc vòng, cánh hoa; nối trang rách với nhật ký để đọc trình tự lời hứa. |
| 3 | Đối chiếu dấu chân, nét rune, điều kiện trong thư và dấu niêm; phân biệt người tham gia với người xác nhận. |
| 4 | So sánh góc nhìn của tinh thể, phiến đá và hành lang; nhận ra điều bằng chứng chưa cho thấy. |
| 5 | So mực, sáp, ngày chỉnh sửa với ngày thư và chữ ký để kiểm tra hồ sơ. |
| 6 | Tìm các mốc độc lập, nối đoạn thiếu và nhớ trình tự qua nửa đêm. |
| 7 | Đối chiếu vật phẩm với các hõm; quan sát ranh giới giữa các mảnh trước khi ghép. |
| 8 | Đọc lại kho ký ức, xem chiếc vòng, cơ chế và đường sáng trước khi quyết định kết truyện. |

- Nút gợi ý ưu tiên vật bắt buộc chưa xem ở cảnh hiện tại. Khi tìm được manh mối mới, cấp gợi ý trở lại mức nhẹ.
- Trả lời sai nhận gợi ý của đúng câu đố; gợi ý sâu hơn vẫn cần người chơi yêu cầu, không tự giải hộ.
- Chỉ cập nhật câu mặc định cũ trong CMS và bản lưu. Nội dung CMS đã tự biên soạn được giữ nguyên; không reset tiến độ hay thay đáp án, điểm, điều kiện và kết truyện.
- Nội dung mới có VI/EN và bản dịch tĩnh JA/ZH/KO/MY/KM. Audio theo nội dung mới có khóa cache mới; vào CMS chuẩn bị lại VI/EN để phát ngay. Intro giữ nguyên.

## Nhịp thoại và video theo chương

Mỗi hành động chỉ hiện tối đa một lời dẫn và một thoại nhân vật. Các thoại bổ sung vẫn nằm trong bản lưu để bảo toàn nội dung, nhưng không tự nối vào hàng đợi giọng đọc hay khung thoại chính. Lời dẫn vẫn nghe thủ công; không bật tự đọc lại.

| Chương | Video đúng thời điểm |
| --- | --- |
| 1 | Mở cổng → enter_ruins → memory_01 → thoại kết ngắn → trục thư. |
| 2 | Khám phá và ghép lời hứa → một thoại xác nhận → memory_02 → trục thư. Xem mặt dây chuyền chỉ có glow. |
| 3 | Giải cơ chế → seal_activation; chọn cách đáp lại → memory_03 → trục thư. |
| 4 | Đối chiếu góc nhìn → memory_04 → trục thư. |
| 5 | Đối chiếu hồ sơ → memory_05 → trục thư. |
| 6 | Xếp dòng thời gian → deep_vault_awaken; quyết định → memory_06 → trục thư. |
| 7 | Ghép bốn vật → seal_activation; quyết định → memory_07 → trục thư. |
| 8 | Kết ẩn: memory_08 → một thoại kết → mái hiên chapter_complete → trục thư. Ba kết khác dùng lời kết và nền đúng nhánh, không ghép clip mái hiên vui vẻ vào kết nguy hiểm. |

Không còn tự nối memory_transition, memory_exit hoặc cảnh mái hiên vào chương 2–7. Hiệu ứng nhẹ vẫn dùng frontend. Video đã tải khi mở chương; không xếp thành playlist ba clip. Một bước mới thay phần thoại đang chờ, không đọc bù hội thoại cũ sau phim.

Player và bước preload dùng cùng URL phiên bản của video. Nhánh kết không có clip riêng tự hoàn tất phần trình bày bằng chữ, không đứng kẹt ở phase memory.
