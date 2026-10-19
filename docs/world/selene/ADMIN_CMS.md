> Cập nhật 17/10: mặc định dùng engine 8 chương và intro mới 1080p. Xem [bản triển khai 8 chương](MEMORY_ADVENTURE_8_CHAPTERS.md). Các mô tả một chương/intro 720p bên dưới là lịch sử của bản v1. Hai derivative intro cũ đã dọn.

# CMS World

Vào CMS chính → Worlds · CMS, hoặc /worlds/admin. Dùng docs_auth hiện có; không public API quản trị.

Các tab:
- Thế giới & giọng nói: Selene source, model hội thoại, provider người kể, narrator Voice ID VI/EN, lời hẹn, intro narration, instruction, shared BGM playlist, gate, hint và access thresholds.
- Chương truyện: 8 slot; Chương 1 bật được, 2–8 draft. Title/objective/opening speech/thought/completion, clue facts/keywords/3 hints/expression, memory scope/fact/title.
- Địa điểm/lựa chọn/canon: JSON có schema. requires_clue khóa canon; unlock_condition dùng flag; choice có requires_complete và flag.
- Assets: path tương đối, fallback, duration, loop, license metadata.
- Hoạt ảnh: event registry.
- JSON nâng cao: cấu hình đầy đủ, server validate trước lưu.

Sửa trust/gate tại đây là quyền admin; user không thấy điểm số. Không dán bí mật chương sau vào instruction hay lời kể công khai. Canon phải đặt điều kiện khám phá.

Nội dung story giữ snapshot theo lượt, áp dụng cho lượt mới. Model và narrator voice hiện tại áp dụng cho voice tiếp theo. Selene voice/provider lấy từ CMS nhân vật và phân công TTS chat thường; không có ô Voice ID Selene thứ hai trong World.

Config lưu version/CAS; hai admin lưu cùng revision thì một người nhận 409. Save không thay project prompt hay model assignment chat thường. Key API tiếp tục ở kết nối/model đã mã hóa/env, không đặt trong story config.

## Chọn giọng từ API

/worlds/admin → Thế giới & giọng nói → chọn Provider TTS người kể → danh sách VI/EN tự tải.
Chọn tên giọng trong từng ô, rồi Lưu. Nút Tải lại gọi lại catalog; adapter hiện có có cache 10 phút.
Backend dùng API key đã mã hóa/env, không gửi key ra browser. Endpoint /v1/admin/moonfall/voices yêu cầu quyền CMS và nhận model_id của lựa chọn nháp, nên không cần lưu provider trước để xem danh sách.

Cả ô VI và EN đều hiển thị toàn bộ giọng API trả về, không lọc ngôn ngữ. Nhãn gồm tên, ngôn ngữ, giới tính và ID để admin tự chọn. Danh sách rỗng/lỗi không tự xóa giọng đã gán. Khi đổi provider, kiểm tra và chọn lại giọng tương ứng trước khi Lưu. Không tự thay giọng người kể bằng giọng Selene.

Độ khó 1–5 hiện là thông tin biên tập; chưa tự điều chỉnh puzzle. Các min_trust/min_meaningful_turns/min_days/required_access riêng trong JSON từng chương là phần chuẩn bị, chưa dùng làm gate riêng ở Chương 1. Gate đang hoạt động là entry_gate chung.

## Danh sách chương trong chat Selene

Bảng công cụ nhân vật luôn có nút Cốt truyện đối với Selene Moonbrook, kể cả khi chưa đủ gate. Bấm để xem các chương:
- Đã mở: link Bắt đầu / Tiếp tục / Trở lại.
- Chưa mở: mờ + ổ khóa, không bấm được; ghi rõ cần trò chuyện thêm, World chưa bật, admin tạm khóa hoặc chương chưa triển khai.
- Chương 2–8 hiện luôn khóa vì runtime chưa triển khai.
- Khi trạng thái chuyển từ khóa sang mở, nút có thông báo và hàng chương phát hiệu ứng khóa mở nhẹ một lần khi xem. Không phát lại khi đóng/mở danh sách; tôn trọng prefers-reduced-motion.
- Trạng thái do /v1/moonfall/chapters xác nhận theo đúng owner; frontend không tự quyết định mở khóa.

Trước đây thẻ lời mời bị return null khi không eligible hoặc API lỗi nên người dùng không thấy gì. Giao diện mới không che giấu tình trạng này. Sau khi triển khai code mới, nếu World chưa bật, hãy bật WORLD_DEMO_ENABLED=true và cấu hình World/Chương 1 trong CMS. Danh sách chương không thay đổi gate hay tự tạo một lượt chơi.

## Xóa phòng chat: reset trải nghiệm riêng của user

API DELETE /v1/rooms/{room_id} xác thực owner trước khi xóa. Bản cập nhật reset phòng được chọn và trạng thái trải nghiệm dùng chung của chính user với các nhân vật trong phòng:
- Hội thoại, audio/suggestion/alternatives gắn với message; trạng thái/gợi ý/lore riêng của phòng, tài liệu chỉ dùng ở phòng đó.
- Memory kể cả pinned và ký ức World đã import, cảm xúc/quan hệ/reflection, recap, liên kết và lịch sử tương tác giữa nhân vật.
- Toàn bộ Moonfall run liên quan, kể cả ngoài giới hạn 10 bản hiển thị; save/checkpoint World cũ có nhân vật đó.
- Log AI/archive hội thoại của phòng bị xóa; không tạo thêm bản archive khi user yêu cầu reset.
- Tương tác/rating/usage riêng của user với các nhân vật đó.

Card, prompt, lorebook CMS, model/voice settings và media dùng chung giữ nguyên. User khác không bị reset. Lịch sử ở các phòng khác không tự xóa, nhưng memory/quan hệ/World dùng chung của user với nhân vật sẽ reset; UI xác nhận có nêu phạm vi này. Trước đây UI đã gom các phòng chat đơn trùng nhân vật khi xóa; hành vi đó giữ nguyên.

Reset marker chỉ ghi thời điểm, không giữ nội dung: tin nhắn cũ còn ở phòng khác không tự mở khóa lại World, và tác vụ analysis cũ đang chạy không được ghi lại ký ức sau reset. Các lượt mới sau reset được tính lại theo gate CMS. Gate bằng 0 vẫn cho vào Chương 1 ngay, nhưng tiến trình cũ đã mất.

Quá trình chạy trong cùng transaction: lỗi thì rollback toàn bộ. Đây là thay đổi hành vi khi xóa phòng trong bản mới; không tự chạy cleanup dữ liệu đang có, không sửa backup ngoài ứng dụng. Luồng xóa nội bộ có mục đích lưu trữ và Assistant giữ quy tắc riêng.

## Lối vào từ trang chủ: intro và bản đồ ký ức

- Trang chủ → Thế giới: intro chung có nhạc → bản đồ nhân vật → chọn nhân vật đã mở → bảng chọn chương dùng chung với chat.
- Từ nút Cốt truyện trong chat: vào chương của nhân vật đó, bỏ qua intro chung và bản đồ.
- Intro gốc: image/video/moonfall_final_rock.mp4 (71 giây).
- Bản phát: image/worlds/hub/video/world_intro_8d7a5c753dea.webm, VP9 720p/24fps + Opus stereo.
- Nguồn MP4 giữ nguyên; WebM khoảng 9.06 MB, giảm khoảng 65% từ 26.08 MB.
- Manifest: character_chat/story_data/world_hub.json. Đây là manifest media chung, không phải dữ liệu tiến trình của user.
- Thay video: chạy python scripts/prepare_world_hub_videos.py --source image/video --overwrite rồi build/deploy. Nhiều video phát theo tên 01_, 02_, ...
- Khi nút Thế giới xuất hiện, trình duyệt chuẩn bị video đầu qua preload=auto; mở World dùng lại cùng phần tử video. Chỉ chuẩn bị metadata của đoạn kế tiếp. Chế độ tiết kiệm dữ liệu/giảm chuyển động chỉ tải metadata và chờ người dùng bấm phát.
- Nút Bỏ qua bỏ qua toàn bộ intro chung. Âm lượng lưu trên trình duyệt. Rời World sẽ dừng âm thanh. Nếu trình duyệt chặn autoplay có nhạc, hiện nút Phát intro có nhạc.
- Tải trước giúp giảm chờ; mạng, chính sách cache và bộ nhớ của trình duyệt vẫn quyết định khả năng sẵn sàng. Không phát âm thanh nền khi chưa vào World.
- Các nhân vật lấy từ kho hệ thống hiện có, gộp theo tên. Chỉ hiển thị trạng thái mở khóa riêng của tài khoản đang đăng nhập.
- Hiện chỉ Selene có chương đã triển khai; các nhân vật khác hiện khóa/Sắp ra mắt. Xem intro hoặc bỏ qua không mở khóa chương và không tạo bản sao nhân vật.
- Khi hết video hoặc video lỗi, vẫn vào bản đồ. Video không ghi hay quyết định trạng thái cốt truyện.

### Chất lượng, lời dẫn và ngôn ngữ của intro chung

- Bản HQ: image/worlds/hub/video/world_intro_8d7a5c753dea_hq.webm, VP9 CRF22, khoảng 50.8 MB; mặc định phát. Bản tiết kiệm 9.06 MB vẫn chọn được ở mục Chất lượng.
- Nguồn gốc là 1280×720. HQ giảm mất chi tiết do nén; không phải video 1080p thật. Để nâng độ phân giải thật, cần thay nguồn 1080p/4K rồi chuyển lại.
- CMS World → Thế giới & giọng nói → chọn Provider TTS và giọng người kể VI/EN; intro dùng các cấu hình này.
- Mục Intro trang chủ · lời dẫn & phụ đề quản lý 6 đoạn, thời gian bắt đầu/kết thúc, 7 bản phụ đề và các mức phối âm. Có nút Lưu lời dẫn intro chung riêng.
- Timeline mẫu: 8–16s, 19–27s, 30–38s, 41–49s, 52–60s, 63–70s. Đoạn đầu chừa nhạc và dòng đeo tai nghe. Kịch bản không tiết lộ bí mật/chương chưa chơi.
- Phụ đề và toàn bộ giao diện bản đồ/intro có VI, EN, ZH, JA, KO, MY, KM. Bản UI được viết riêng trong frontend/src/worlds/worldHubCopy.ts, không gọi dịch từng từ khi user mở trang.
- Ngôn ngữ phụ đề theo ngôn ngữ giao diện. Ngôn ngữ thuyết minh chọn VI/EN riêng; không mặc định ép giọng EN đọc tiếng Nhật/Khmer.
- Phối âm mặc định: nhạc 45% mức master, giảm còn 14% khi giọng đang đọc; giọng 100% mức master. Master 0 tắt cả nhạc lẫn lời dẫn.
- Các câu TTS được tạo từ nội dung CMS qua provider có sẵn; cache theo nội dung/model/provider/Voice ID/credential fingerprint tại DATA_DIR/world_intro_audio. Không tạo lại mỗi lượt xem. Client chuẩn bị 2 câu song song; voice chưa có vẫn hiện đúng phụ đề.
- Pause/skip/replay/đổi chất lượng/rời World sẽ ngắt hoặc đồng bộ lời dẫn theo thời gian video. Giọng không quyết định tiến trình truyện.
- Chưa có cấu hình TTS hoặc provider lỗi: hiển thị phụ đề và thông báo giọng chưa khả dụng, không chặn bản đồ.

## Kịch bản và hàng đợi thoại

Kịch bản intro đã biên tập lại: [INTRO_NARRATION_SCRIPT.md](INTRO_NARRATION_SCRIPT.md). Người vận hành tự cấu hình API key/model TTS và chọn narrator trong CMS; không có audio do dịch vụ khác tạo sẵn hay Voice ID ngoài CMS bị ép vào cấu hình.

Trong chapter, các khối DẪN TRUYỆN và Tên nhân vật · lời thoại có kiểu trình bày riêng; lời thoại đặt trong ngoặc kép. Giọng narrator/nhân vật vẫn do backend phân vai. Một hàng đợi dùng chung cho nút Nghe và chế độ Tự đọc: không chen/cắt giọng giữa câu. Gợi ý và chuyển trạng thái không dừng câu đang phát. Nút dừng, tắt tự đọc, đổi ngôn ngữ hoặc rời World mới hủy hàng đợi.

Bản đồ dùng cùng MoonfallSound/playlist với chapter và chat thường. Mặc định bật nếu user chưa lưu lựa chọn; nút nhạc lưu bật/tắt trong trình duyệt. Playlist không chạy trong intro để tránh chồng với nhạc có sẵn trong video.

## Cập nhật đọc thoại và ngôn ngữ (18/10/2026)

- Intro trang chủ giữ tự đọc: VI dùng giọng VI; các ngôn ngữ client khác mặc định giọng EN. Phụ đề luôn dùng ngôn ngữ client.
- Trong chương: lời dẫn không tự đọc và không gọi TTS ngầm cho video. Có nút Nghe để yêu cầu đọc thủ công. Lời nhân vật vẫn tự đọc nếu bật chế độ này.
- Chương chỉ hiện nút Nghe và điều khiển giọng khi client là VI hoặc EN. JA/ZH/KO/MY/KM có đầy đủ chữ, không có nút nghe hoặc tự gọi TTS.
- Lời dẫn trong clip hiển thị trên video và vẫn nằm trong transcript. Khi nghe lời nhân vật, chữ cũng xuất hiện trên khung cảnh. Skip/kết thúc clip ngắt lời dẫn thủ công.
- Âm thanh hành động dùng cùng thư viện /v1/roleplay/action-sounds và trigger/clip/âm lượng do CMS chat thường quản lý. Đi vào cảnh có tiếng bước chân; xem tài liệu phù hợp có tiếng lật trang. Sự kiện mới chỉ chạy một lần; tải lại, bấm lại item đã xem không đọc/phát lại. Clip không có thì im lặng, không chặn tiến độ.
- Bản dịch truyện chuẩn bị sẵn tại character_chat/story_data/moonfall_arc/translations.json, đối chiếu cả nội dung VI và EN. CMS ghi bản dịch riêng được ưu tiên. Sửa nguồn VI/EN làm bản dịch cũ không còn khớp; cần cập nhật các ngôn ngữ tương ứng.
- Snapshot cũ vẫn tra được bản dịch nếu nội dung nguồn còn khớp. Không sửa dữ liệu tiến độ, ký ức hoặc nội dung chat thường.
- Công cụ tạo phần dịch thiếu: python -m modal run scripts/translate_moonfall_story.py. Dùng secret LLM hiện có trên Modal, không đưa key vào source. Test phủ ngôn ngữ: test_story_translations_cover_all_chapters_and_preserve_cms_overrides.

## Cập nhật: quyền biên tập CMS và xem lại chương

- Nội dung World/chapter, cảnh nối và lời dẫn intro do người có quyền CMS biên tập không đi qua bộ lọc hội thoại. Tránh lỗi “CMS chapters: Content requires moderation” khi lưu JSON truyện.
- CMS vẫn yêu cầu xác thực, cấu trúc hợp lệ, đường dẫn asset an toàn, model có sẵn và revision hiện tại. Tin nhắn người dùng, câu trả lời AI và bản dịch được AI sinh vẫn được kiểm duyệt.
- Chương đã mở không bị khóa lại vì thiếu điểm của lần vào đầu. Chương đã hoàn thành có chế độ xem lại, tự do di chuyển giữa các cảnh, trò chuyện, xem kho ký ức và phát lại clip đã được phép xem.
- Khi quay lại chương hoàn thành, màn kết không tự mở. Sau lần hoàn thành đầu tiên có thêm nút “Ở lại chương này”; nút quay về chat vẫn có sẵn.
- Xem lại không reset vật phẩm, thay lựa chọn/kết truyện hay cộng thưởng lần nữa. Video của kết ẩn vẫn cần đúng kết đã mở.

### Chơi lại để tìm kết khác

Sau khi hoàn thành cả 8 chương, người dùng chọn **Chơi lại từ chương 1**, xác nhận **Bắt đầu lượt chơi mới**. Các manh mối, điểm truyện, cờ, puzzle và lựa chọn bắt đầu lại. Bộ sưu tập kết cũ vẫn giữ riêng theo user và nhân vật.

Lượt mới phải hoàn thành chương 1→8 và các lựa chọn của chính lượt đó. Không dùng vật phẩm/cờ từ lượt cũ để mở kết ẩn. Lượt chơi lại không yêu cầu kiếm lại điểm chat giữa các chương đã từng mở, nhưng không được nhảy qua chương. Dừng giữa chừng rồi quay lại tiếp tục save hiện tại.

Xem chương cũ chỉ là tham quan/đọc lại: không đổi lựa chọn hoặc kết. Mỗi loại kết chỉ mở màn tiết lộ và phần thưởng một lần. Nếu đi lại cùng đường dẫn tới cùng kết, hệ thống báo kết đã có; không tự đổi sang một kết chưa tìm được và không phát lại màn kết. Bộ sưu tập chỉ hiện tên kết đã khám phá, kết chưa có hiện “???”.

Save cũ đã hoàn tất sẽ được nhận diện kết đang có khi chuyển sang lượt mới. Không xóa card, prompt/lore CMS hoặc lịch sử chat. Ký ức đồng bộ từ lượt chơi lại mang nhãn nhánh truyện thay thế, không ghi đè kết của lượt trước.

Kiểm thử bổ sung: các lượt chơi đầy đủ sinh hai kết khác nhau; trùng kết không phát lại/không thưởng thêm; lưu dở không nhảy chương 8; API restart có kiểm quyền user, revision và chống gửi lặp; Edge xác nhận xem lại chương 1/8 không bị ép về chat và khởi động lượt mới từ chương 1.

Nghiệm thu bản sửa: 67 bài backend đạt (Moonfall, 8 chương, nhịp mở chương, replay và BG nhúng); 1 kiểm thử Edge desktop đạt cho xem lại, trở về chat, bắt đầu lượt mới, reload và lưu âm lượng CMS. Build đạt, 716 chuỗi UI đủ 6 bản dịch bên cạnh VI. Test LLM dùng mock, không nghiệm thu provider thật trong lần này.

## Chương 1: cổng, tải trước tài nguyên và cuộn giấy

Luồng mới: khám phá hai khu vực → đủ manh mối → giải rune → chọn lời hứa với Selene → trở về cổng và hiện chỉ dẫn mở cổng → chỉ cổng nhận click → video đi qua cổng → ký ức M01 → chuyển trắng → câu kết và cuộn giấy giới thiệu Moonbrook. Không bỏ M01 vì đó là dữ kiện cốt truyện được lưu.

Trạng thái gate_ready/gate_cinematic/memory được lưu độc lập với video. Bỏ qua hoặc lỗi clip đi qua cùng hành động kết thúc, không tạo thưởng hai lần. Các mục khác không nhận click trong bước mở cổng. Nội dung chỉ dẫn, lời kết và cuộn giấy nằm ở **World & giọng đọc → Chương 1 · mở cổng và cuộn giấy**.

Các polygon tương tác hoàn toàn trong suốt, kể cả hover/focus: không viền, không tên nổi, không dấu sao, không tooltip. Chỉ con trỏ bàn tay; tên vẫn tồn tại qua aria-label cho công cụ hỗ trợ truy cập.

Mỗi chương có bước chuẩn bị tài nguyên và phần trăm tải. Ảnh/BG, lớp nền sạch và portrait được giải mã trước; các clip sắp dùng trong chương được tải đủ dữ liệu thành blob trước khi mở thao tác. Không tải toàn bộ video của các chương sau. Chế độ tiết kiệm dữ liệu/giảm chuyển động dùng fallback. Media tùy chọn lỗi không được khóa tiến trình; video lỗi có thể bỏ qua. Đây là preload media, không phải sinh sẵn mọi câu trả lời LLM hoặc giọng đọc mới.

Trong chương, lời dẫn vẫn có thể hiện trên màn hình/video, nhưng nút nghe chỉ nằm trong transcript chat. Giọng nhân vật giữ cơ chế tự đọc cũ; không trộn lời Selene vào đoạn video dẫn.

Admin mặc định vào preview riêng, có menu chọn cả 8 chương, không cần đi qua gate điểm của user. Mở lại trang tiếp tục preview của chính admin; lưu cấu hình CMS phiên bản mới sẽ tạo preview mới. Preview không ghi ký ức sang chat, không thay lượt chơi thật, không xuất hiện trong danh sách save của user thường. Quyền đọc vẫn kiểm tra owner và admin còn hoạt động.

Bản cập nhật này đã có bản dịch tĩnh cho lời chỉ dẫn, câu kết và cuộn giấy ở VI/EN/JA/ZH/KO/MY/KM. Sửa lời trong CMS thì điền các bản dịch tương ứng; giao diện không tự gọi LLM để dịch trong lúc bấm mở cổng.

Kiểm thử bản cổng: 70 bài backend riêng biệt đạt (38 bài adventure/pacing/replay/gate, 35 bài Moonfall/BG/gate, trùng 3 bài gate). Edge kiểm tra video mở từ blob đã tải, gate-only, nút nghe không có trên video, skip → M01 → cuộn giấy; không gọi LLM/TTS thật trong kiểm thử.

### Tải theo giai đoạn và quay về chat (18/10/2026)

- Sau đăng nhập: giữ màn chờ con mèo theo theme, không hiện phần trăm. Chờ cấu hình assistant/model, danh sách nhân vật, reaction audio đã có và hai bản nhạc đầu playlist tải xong. Lỗi tải bắt buộc giữ màn chờ và cho thử lại.
- World ở nền chỉ tải metadata và module giao diện. Không tải cả bộ video hay cả 8 chương lúc đăng nhập.
- Khi mở bản đồ World: màn chờ có phần trăm tải intro, narration đã chuẩn bị và ảnh bản đồ. Khi vào/chuyển chương: màn chờ con mèo và phần trăm riêng, chuẩn bị tài nguyên của chương đó. Media đã tải trong phiên được dùng lại.
- Không tạo sẵn mọi câu trả lời hay TTS tương lai: nội dung chat mới vẫn cần provider. Trình duyệt có thể yêu cầu thao tác để cho phép phát âm thanh.
- Nút **Sang chương tiếp theo** chỉ hiện nếu chương đó thực sự mở. Lượt chơi lại không cần tích điểm chat lại; lượt đầu vẫn theo pacing CMS.
- Biểu tượng quyển sách cạnh ổ khóa hiển thị điều kiện thực: hoàn thành chương trước, số lượt chat hợp lệ tối thiểu và điểm mở chương. Điểm thưởng theo chủ đề và tăng trust giúp mở sớm hơn; không có ngưỡng cảm xúc bổ sung được tự đặt.
- Khi đồng ý mang ký ức về chat, lời nhắn trở về có sender là nhân vật. Nếu provider lỗi, dùng câu Selene được biên soạn và dịch sẵn.
- Mỗi chương thật được chia sẻ lần đầu cộng tối đa trust +0.02, affinity +0.01, familiarity +0.01, respect +0.005 (mỗi mức tăng còn bị giới hạn bởi relationship_delta_cap trong cấu hình; tổng chỉ số chặn ở 1). Nhật ký thưởng theo user/nhân vật/chương ngăn cộng lại khi retry hoặc replay. Không thay prompt hay tính cách chat thường.
- Admin mặc định vào preview riêng: có thể chuyển chương nhưng không xuất ký ức/lời nhắn/phần thưởng World sang lượt chơi thật.


### Sửa thời gian vào trang chủ (18/10/2026)

Trang chủ chỉ chờ cấu hình assistant và model; giữ màn con mèo không phần trăm.
Không chờ font, clip reaction hay tải trọn nhạc. Sau khi vào, tải nền tối đa một
nhân vật và một bài nhạc, chạy song song. Lỗi audio không khóa trang chủ.
Phòng chat vẫn chuẩn bị audio của đúng nhân vật khi mở; lần đầu có thể cần chờ audio.
World giữ nguyên cơ chế tải theo màn/chương kèm phần trăm.

### Vào sảnh và playlist World (18/10/2026, bản cập nhật tiếp)

- Trang chủ trở về cơ chế chỉ chờ xác thực; các tác vụ chuẩn bị chạy nền và không khóa sảnh.
- Màn chờ mở sảnh World có con mèo và thanh chờ, không phần trăm.
- Màn tải tài nguyên chương giữ phần trăm, thêm câu thân thiện đã dịch đủ bảy ngôn ngữ.
- Số bài tải trước là ngân sách mạng, không phải danh sách phát. Danh sách phát thật lấy toàn bộ các bài được chọn trong CMS Nhạc nền.
- Nhạc World tiếp tục trong lúc khám phá/chat; hết bài chuyển bài tiếp theo trong playlist và quay vòng. Nếu chỉ chọn một bài thì lặp bài đó.
- Âm lượng World theo mixer/CMS và lựa chọn người dùng; nhạc giảm khi thoại hoặc cinematic rồi phục hồi. Intro sảnh vẫn dùng nhạc trong video.

### Chuẩn bị sẵn giọng nói các chương

1. Mở World Studio → **World & giọng đọc**. Chọn provider TTS và giọng dẫn VI/EN từ danh sách API. Giọng dẫn phải khác giọng Selene.
2. Giọng Selene tiếp tục chỉnh ở card trong CMS chat thường. Nếu dùng thoại nhân vật phụ, chọn VI/EN cho Selene trong ký ức, Elarion và cô gái trong ký ức ở World Studio. Không gán thì nhân vật phụ giữ text-only.
3. Lưu cấu hình. World tự chuẩn bị thoại cố định VI/EN ở nền. Có thể bấm **Chuẩn bị VI/EN cả 8 chương**, hoặc chọn chương trong tab **8 chương** rồi chỉ chuẩn bị chương đó.
4. Xem bộ đếm **đã sẵn sàng / tổng số đoạn**. Có lỗi provider thì sửa cấu hình và bấm chuẩn bị lại; các clip đã tạo được dùng lại.
5. Audio nằm tại DATA_DIR/world_chapter_audio trên volume. Đổi lời, voice, provider, model hoặc key tạo cache khác; không ghi key vào file audio hay gửi key xuống client.
6. Khi vào một chương, client tải và giải mã các clip của chương trước khi mở tương tác. Audio lỗi tải/giải mã giữ màn chờ và cho thử lại, không báo 100% sẵn sàng giả. Ngôn ngữ không hỗ trợ TTS không tải thoại.
7. Lời dẫn vẫn chỉ đọc khi bấm nút trong transcript; thoại nhân vật tự đọc theo hàng đợi. Clip cố định đã chuẩn bị không gọi lại TTS khi câu xuất hiện. Thoại LLM phát sinh mới vẫn cần tạo audio.
8. Nhạc playlist CMS tiếp tục trong video chuyển cảnh ở mức nhạc đã chọn; chỉ giảm khi có giọng đọc. Intro sảnh giữ nhạc được dựng trong video.
9. Khi đổi giọng Selene ở CMS chat thường, bấm chuẩn bị lại ở World Studio trước khi nghiệm thu. Cache được lưu lâu dài; việc chuẩn bị không tạo phòng, tăng điểm, tiết lộ kết ẩn hay ghi tiến trình cho người chơi.

### Trục thư đủ 8 chương và phần trăm vào World

- Mỗi chương hoàn thành có trục thư dùng chung hiệu ứng mở giấy. Chương 1 giữ nội dung CMS hiện có.
- Chương 2–7 dùng tiêu đề ký ức, tóm tắt và lời hồi tưởng đúng chương; bản dịch lấy từ nội dung đã biên soạn và dịch sẵn.
- Chương 8 dùng tiêu đề và lời dẫn của đúng kết đã chọn, không dùng nội dung kết ẩn cho kết khác.
- Sửa nội dung chương 2–7 qua mục Memory và các trường localization trong CMS; sửa chương 8 qua cấu hình kết truyện. Không cần thay prompt chat thường.
- Bấm vào World từ sảnh lại hiện con mèo, thanh tiến độ có số phần trăm và câu chờ thân thiện đủ bảy ngôn ngữ. Chỉ số lấy từ quá trình tải thật; không đặt thời gian chờ giả. Trang chủ sau đăng nhập vẫn không chờ tải cả World.

- Chương 1: mở cổng → video vào di tích → video ký ức → đọc hết hàng đợi lời thoại kết chương → trục thư. Tắt giọng hoặc ngôn ngữ không hỗ trợ TTS vẫn kết thúc bình thường; lỗi audio không khóa tiến trình.
- Thanh tải chương cố định cao 6px, không giãn theo chiều dọc.

### Sửa quay về và thứ tự thoại/video (18/10/2026)

- Rời World nhúng đóng trục thư và các hộp modal; không để lớp modal ẩn khóa trang chat.
- Nút quay về dùng lời mở đầu đã biên soạn và dịch sẵn, không chờ provider tạo lời. Quyền chia sẻ ký ức, điểm một lần và chế độ preview vẫn được giữ.
- Lời Selene trước chuyển cảnh đọc xong mới chạy video. Thoại trong clip vẫn tách khỏi giọng dẫn; trục thư chờ thoại kết và hàng đợi outro.
- Video mới có URL phiên bản theo hash file, để thay nội dung cùng tên không phát nhầm bản cũ.
- Danh sách asset đang dùng và bản cũ đã bỏ: xem MEDIA_ASSET_AUDIT.md.

### Phép thuật và dọn video trùng

- Màn chơi 8 chương đã gắn WorldEffects vào đúng khung cảnh; rune, manh mối và thought bubble được định vị theo đối tượng.
- Khi phát sinh magic event mới, dùng biểu cảm selene_magic trong thời gian ngắn; tải lại lịch sử không tự diễn lại phép.
- Chương 3/7 dùng seal_activation, chương 6 dùng deep_vault_awaken sau khi giải đúng câu đố. CMS chủ động tắt video vẫn được tôn trọng.
- Đã xóa 16 MP4 trùng với WebM sau đối chiếu thời lượng và ba khung hình, giảm 60.329 MB. Log tại artifacts/moonfall-acceptance/redundant-video-cleanup.json.

### Rà nhịp phát cả 8 chương

- Mỗi lượt tương tác tối đa một lời dẫn và một thoại nhân vật trong khung chính. Các thoại phụ vẫn lưu trong lịch sử nguồn, không tự phát nối.
- Hàng đợi giọng không đọc bù các câu cũ sau phim; lượt mới thay phần đang chờ.
- Chương 2 chỉ dùng memory_02 khi thực sự vào ký ức; mặt dây chuyền dùng glow, không mở movie. Chương 2–7 không nối memory_exit hoặc clip mái hiên kết chương.
- Chương 3/7 vẫn có clip phong ấn sau câu đố; chương 6 có clip hầm sâu. Chương 8 chỉ dùng mái hiên với kết ẩn phù hợp; nhánh không có clip riêng tự đi tiếp bằng chữ.
- Video chính dùng đúng URL có phiên bản giống bước preload, không tải lại bằng URL thứ hai.
- Ma trận đầy đủ ở MEMORY_ADVENTURE_8_CHAPTERS.md.


## Admin xem trực tiếp kết truyện
Trong World, thanh ADMIN PREVIEW có mục “Xem thử kết truyện”.
Chọn một trong bốn kết, gồm kết ẩn, để phát trực tiếp mà không cần chơi đủ
tám chương, tích điểm hoặc chờ lựa chọn cuối xuất hiện.

Mỗi lần chọn tạo lại lượt preview riêng của admin. Có thể xem lại cùng một
kết nhiều lần. Không ghi vào bộ sưu tập kết thật, không đồng bộ ký ức hoặc
cộng chỉ số sang chat thường. Backend kiểm tra quyền admin và chủ sở hữu;
user thường không dùng được action preview_ending.

Trong luồng chơi preview thông thường, kết ẩn hiện ngay khi đủ bước giải đố
chương 8; admin không phải chờ hiệu ứng mở lựa chọn như user thường.
