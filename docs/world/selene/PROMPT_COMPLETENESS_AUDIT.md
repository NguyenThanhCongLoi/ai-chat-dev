# Kiểm tra Echoes of Moonfall so với prompt gốc

Ngày 17/10/2026. Phạm vi: attachment 00f60f1e-7882-4e61-80a5-8360bfabdbdb và các bổ sung về cinematic, giọng kể, hiệu ứng, CMS, không đổi chat thường. Đây là audit, không sửa runtime trong lượt này.

## Kết luận

Chưa đầy đủ theo toàn bộ prompt. Bản hiện tại có đường đi chơi được qua 8 chương và bốn kết, nhưng vẫn là demo về độ sâu trải nghiệm, runtime event, công cụ tác giả và âm thanh. Không đồng nghĩa với bản hoàn thiện production hoặc đủ 80–110 phút.

Đã đọc lại prompt và dữ liệu 8 chương; chạy lại tests/test_memory_adventure.py: 8 passed. Có thêm ba phép tái hiện độc lập bên dưới. Tests hiện có chưa phủ các lỗi mới phát hiện.

## Lỗi xác nhận, ưu tiên sửa

### P1 — Mapping kết truyện phụ thuộc thứ tự mảng CMS

character_chat/adventure/engine.py, nhánh choice chương 8, zip ba lựa chọn với ba phần tử đầu của adventure.endings. Validator chỉ kiểm tập ID, cho phép đảo thứ tự.

Tái hiện: reverse endings trong seed rồi validate vẫn thành công. Restore the Memory bị map sang between_memory_and_moonlight; nhánh này không kiểm gate của lựa chọn ẩn vì ID lựa chọn vẫn là lựa chọn thường.

Hệ quả: chỉnh thứ tự hiển thị trong CMS có thể dẫn tới sai kết hoặc bỏ qua điều kiện kết ẩn. Seed mặc định chưa đảo vẫn cho bốn kết đúng.

Cần dùng ending_id tường minh trên từng lựa chọn và kiểm hidden gate lần nữa trước khi xác nhận kết; validator kiểm target, không phụ thuộc thứ tự.

### P1 — Lựa chọn chương 8 bỏ effects/tags/events đã cấu hình

engine.py: nhánh chương 8 chỉ đặt proposed_ending. confirm_ending thêm choice bằng ID ending rồi bắt đầu memory; không áp dụng dữ liệu effects, flags, tags, events của option.

Tái hiện Restore: expected truth +1; actual delta cả bốn stat bằng 0; tag restore không được thêm. Câu phản ứng riêng của lựa chọn cũng không chạy. Có ảnh hưởng context cá nhân hóa cho chronicle.

Cần giữ option_id/proposed_choice, chỉ áp dụng hệ quả đúng một lần khi confirm; reconsider không cấp hệ quả.

### P1 — Nhiều event được schema nhận nhưng engine chưa thực thi

schema.py khai báo state_update, conditional, goto, item_removed, background_change, foreground_change, wait, bgm, ambient_audio, sfx, voice...; engine.emit chủ yếu đổi thành một dòng SYSTEM.

Tái hiện emit state_update với trust +3: state trust vẫn 0. Đây là event được nhận tên, chưa phải interpreter có ngữ nghĩa hoàn chỉnh.

Seed 8 chương đi được vì phần lớn luật được thực thi bằng action inspect/solve/choice riêng. Người viết CMS không thể tin rằng mọi event trong danh sách prompt đã dùng được.

### P1 — Return to Chat có thể lỗi nếu LLM không sẵn sàng

api/moonfall.py lưu memory và tạo/tìm phòng trước khi gọi support.post_chat. adventure_support.generate có thể trả 503 khi thiếu model/provider lỗi. Khi đó response điều hướng thất bại dù phần dữ liệu trước đã được lưu.

Cần tách điều hướng khỏi tác vụ viết lời chào; có fallback/retry idempotent và giữ một phòng đích ổn định.

## Cốt truyện từng chương

| Chương | Nội dung chính so với prompt | Độ hoàn thiện |
| --- | --- | --- |
| 1 | Cổng cổ, Outer Ruins, chìa khóa, MOON–MEMORY–BLOOD, giọng gọi chưa rõ danh tính, M01 | Có. Mở đầu và phản ứng sau inspect đang lặp. Text memory nói sunlight trong khi clip mới mang cảnh đêm/trăng; cần đồng bộ mỹ thuật và lời dẫn. |
| 2 | Pendant, journal, moonflower tùy chọn, người tặng chưa rõ danh tính, M02 | Có. Tìm kiếm chủ yếu bấm hotspot, lời phản ứng trùng. |
| 3 | Circle, blood rune, burned letter, Council seal, suy luận Selene tự nguyện vào nghi lễ, M03 | Có. Cùng một câu phản ứng lặp 5 lần trong dữ liệu. |
| 4 | Moonfall sụp đổ, quan sát ký ức, echo tùy chọn, crystal/tablet, cảnh báo của Selene trẻ, M04 | Có. Theo Selene và cứu echo chưa thành nhánh chơi có hệ quả cảnh rõ rệt; vẫn là hotspot tùy chọn. |
| 5 | Hồ sơ sửa sau 3 ngày, chứng cứ mực/dấu/ngày/chữ ký-vết cháy, thư Elarion, M05 | Có đủ mạch khám phá. Phân tích tài liệu còn đơn giản. |
| 6 | Timeline 23:47 → 23:52 → 00:03 → 00:16; mirror shard; tự nguyện quên nhưng để đường trở lại, M06 | Có. Điều tra và dựng timeline vẫn là chọn token theo thứ tự. |
| 7 | Altar 4 vật phẩm, Pale Moon tồn tại qua ký ức, Selene là vật dẫn, inscription có điều kiện, M07 | Có. Cơ chế ghép đồ đúng; cần dàn cảnh và phản ứng vật phẩm mạnh hơn. |
| 8 | Review archive, 3 cơ chế, xác nhận kết, điều kiện AND/OR cho lựa chọn thứ tư sau 1.8 giây, M08 chỉ kết ẩn | Có ở seed mặc định. Hai lỗi mapping/effects nêu trên; reveal lựa chọn thứ tư thiếu chuỗi pendant/fragment/glitch/SFX đầy đủ. |

Mạch lý do từ điều tra ký ức → phát hiện hồ sơ bị sửa → phát hiện tự nguyện quên → Pale Moon → lựa chọn cách mang ký ức là liền mạch. Ba kết thường và kết giữ ký ức tách biệt có đúng ý nghĩa gốc. Không phát hiện mâu thuẫn cốt lõi buộc đổi toàn bộ cốt truyện qua việc đọc dữ liệu.

## Trải nghiệm chưa đạt yêu cầu đầy đủ

- Mỗi chương có 1–2 scene, 4–5 hotspot, một puzzle, một lựa chọn lớn; khoảng 302–362 từ tiếng Anh trong localization/chương, đã bao gồm câu lặp và phần tóm tắt. Chưa có cơ sở xác nhận 8–15 phút/chương hoặc 80–110 phút toàn arc.
- Nhiều scene dùng lại cùng câu Selene sau mọi inspect: chương 3 và 4 lặp 5 lần. Cần lời riêng theo chứng cứ, diễn tiến cảm xúc và tương tác đã xảy ra.
- Puzzle artifact_slot hiện kiểm tập vật phẩm, UI chọn token; chưa có các ô ghép trực quan hoặc thử nghiệm vật thể sâu. Không phải cả sáu loại puzzle đều có tương tác riêng rõ rệt.
- Character action được lưu trong event nhưng UI không diễn hoạt look_away/touch_pendant/raise_staff... theo danh sách prompt. Expression có renderer/fallback nhưng không thay thế được action.
- Chưa hoàn chỉnh whisper distort, shake cảnh, fade trắng kết và chuỗi reveal kết ẩn; 8 ảnh location chuyên dụng vẫn chưa được upload ở lần kiểm tra trước.
- UI vẫn có chuỗi VI/EN hardcode. Story VI/EN + EN fallback; chưa bản địa hóa đầy đủ mọi ngôn ngữ đang hỗ trợ.

## Engine, công cụ, lưu trữ

| Hạng mục | Có | Thiếu/giới hạn |
| --- | --- | --- |
| Deterministic gameplay | Action điều khiển clue/item/puzzle/choice/memory/ending; LLM không cấp phần thưởng | Interpreter event tổng quát chưa đủ |
| Save/resume | Owner scope, revision/CAS, receipts, config snapshot, memory cursor/bookmarks | Replay cấu hình allow_replay chưa được engine sử dụng; completed chapter chỉ read-only |
| KnowledgeGate | Chỉ gửi quan sát đã inspect, memory mở, lựa chọn, persona, recent events | Chưa validator tự động phát hiện lore viết lộ tương lai trong chính nội dung CMS |
| Archive | 5 nhóm, M01–M08, items/echo/lore | Echo chủ yếu là ID đổi thành nhãn; chưa có mô hình nội dung Echo phong phú |
| Reflection | Endpoint tạo/lưu theo chương + authored fallback | UI khóa thao tác khi chờ LLM, có thể chậm 25 giây; chưa nghiệm thu 1–3 câu thực tế mỗi chương |
| Post-chat | Lưu normal Message một lần khi hoàn chương và đồng ý chia sẻ | Provider lỗi có thể chặn điều hướng; cần regression test |
| Chronicle | CMS prompt 600–1000 từ, lưu theo run | Chưa kiểm độ dài/chất lượng cá nhân hóa với provider thật; 2400 token có thể thiếu với một số ngôn ngữ |
| CMS | World, voice API, chapter, scenes/hotspots, puzzles, choices, manifest, localized lines, prompt versions, endings | JSON nhiều; chưa có visual hotspot editor (prompt cho phép làm sau), chưa CRUD World/Arc/Character tổng quát |
| Debugger | Read state, eligibility, validation; API set stat/flag/items/memory/ending trên preview riêng | UI chủ yếu jump chapter/read state; thiếu scene jump, skip dialogue, test voice/text, force gate và các điều khiển đầy đủ |
| Validator | ID, asset path, bounds hotspot, reference, solution, localization, missing file warnings | Chưa phân tích scene unreachable/cycle không exit, ending bất khả thi, chapter không hoàn tất, fallback chain, leak lore |
| Asset workflow | WebM/WebP, sheet crop, hash duplicate/index | Scan còn tập trung folder Moonfall; chưa quét cấu hình thư mục tổng quát và metadata đầy đủ mọi loại media |
| Reuse thế giới khác | Data chapter/puzzle/condition tách module | Vẫn hardcode Selene, 8 chương, 4 ending, đường dẫn asset và UI expression; chưa thể thêm World/nhân vật bất kỳ chỉ bằng CMS |

Tái hiện validator: hidden condition understanding >= 1000 vẫn được validate chấp nhận dù seed hiện tại không thể tích được mức đó.

## Audio/video

- Có WebM cho đủ 8 memory, intro mới, skip/error fallback; video không ghi gameplay state.
- Có narrator và character voice tách vai, hàng đợi tuần tự, music/ambient/SFX/master mixer.
- Chưa có pipeline pre-generate/cache toàn bộ thoại cố định từng chương; endpoint voice hiện gọi TTS mỗi lần. Cache intro riêng không thay thế được yêu cầu này.
- Chọn voice language đang reset theo content_language mỗi lần đổi chapter; chưa giữ lựa chọn voice độc lập xuyên chương.
- Cần đối chiếu provider TTS của nhân vật: World đang lấy model TTS enabled đầu tiên khi không gán ID, chưa chắc đúng assignment chat thường trong mọi cấu hình nhiều provider.
- Chưa kiểm audio/provider thật. Không bảo đảm việc có endpoint/mixer đồng nghĩa âm thanh production đã hoạt động.

## Thứ tự xử lý đề nghị

1. Sửa mapping ending và áp dụng lựa chọn chương 8 idempotent; bổ sung tests reorder CMS/reconsider/confirm.
2. Làm Return to Chat không bị chặn bởi LLM, và giữ voice language qua chương.
3. Chốt subset event hỗ trợ thật hoặc hoàn thiện interpreter; không tiếp tục nhận event rồi bỏ qua.
4. Viết lại phản ứng từng hotspot, mở rộng tương tác/nhánh để tạo nhịp chơi đủ sâu; đo thời lượng thực tế.
5. Cache/pre-generate scripted TTS; hoàn thiện validator/debugger/CMS.
6. Ghép 8 location thật, hoàn thiện VFX, bản địa hóa và nghiệm thu trên trình duyệt cả bốn kết với provider thật.

Không thay runtime, prompt CMS, dữ liệu user hoặc logic chat thường trong lượt audit này.
