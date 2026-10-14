# Báo cáo toàn hệ thống AI Companion

Ngày rà soát: 13/10/2026, Asia/Saigon. Phạm vi: nhánh update tích hợp kiến trúc module từ d3d2882 và companion video từ a90ff58. Báo cáo mô tả implementation; không chứng nhận production, chất lượng model hoặc sức chịu tải.

Tài liệu gồm tính năng, luồng, thuật toán, cấu trúc code, lưu trữ, đóng gói và giới hạn. Phụ lục chức năng ở cuối giữ danh mục Assistant/Roleplay/CMS được cập nhật từ báo cáo trước. Không chứa secret, mật khẩu hoặc nội dung người dùng thật.

## 1. Phiên bản và phạm vi

| Nhánh | Nội dung |
| --- | --- |
| main/ver1/integration/service-ver1 | Kiến trúc module, gói service, chưa có video companion |
| update | Kiến trúc module và video normal/talk cho elf |
| v1.0.0/v1.0.0-service.1 | Tag source đóng băng để khôi phục |

Phần module tổ chức lại vị trí code, giữ route/schema và các hành vi cũ. Companion là tính năng riêng của update. SSO, billing AIBox, migration PostgreSQL và kiểm duyệt bổ sung chưa được triển khai trong tác vụ này.

## 2. Danh mục tính năng chính

| Khối | Chức năng |
| --- | --- |
| Platform | Account/session/profile/avatar, theme, locale, sidebar, lịch sử gần đây, workspace iframe và điều hướng |
| Assistant | Tổng quát, tâm lý, sức khỏe, học tập, Tarot/tử vi; chat, stream, attachments, images, suggestions, memory, reminder |
| Character | Preset/system/private/community; tạo từ thông tin hoặc nguồn/tài liệu, edit, avatar, expressions, publication, clone, rating/reaction/favorite/follow |
| Rooms | Chat đơn/nhóm, public room, share/start, member selection, topic/title, history và regenerate |
| Roleplay | Persona/context, group selection, dialogue/action beats, turn language, gợi ý user, relationship/state/memory/reflection |
| Voice | Clone/API catalog, gender/list, target vi/en/shared, capability ngôn ngữ, nghe lại/autoplay theo loại phòng, TTS theo đoạn/cache |
| Reaction | Reference riêng hoặc clone sample, generate/delete/recreate/missing-only, bộ clip theo emotion/voice/language |
| Action sound | Thư viện/rules/volume CMS, detect streaming trên client, một sound mỗi câu trả lời, tối đa 3 giây |
| Music | Playlist chung CMS, chọn/upload/cắt đoạn, trang chủ/chat, mute/volume client |
| Companion update | Nút mắt, full sidebar, normal loop và talk theo voice thật, elf phòng đơn |
| CMS | Dashboard, characters/sections, models/connections/credentials/prompts/purpose assignments, assistants, voice/audio, logs, database viewer, accounts/maintenance |
| Operations | Modal workers, Docker/compose, service entrypoint, backup/verify/restore, API contract và smoke checks |

Tạo Assistant tùy ý vẫn có giới hạn registry/backend; không coi UI create là bằng chứng mọi purpose mới chạy hoàn chỉnh. Chất lượng và khả năng đọc ảnh/file phụ thuộc model được phân công.

## 3. Luồng khởi động và request

modal_app.py chuẩn bị UI, đóng gói character_chat/frontend/dist/image và tài nguyên cấu hình. main.py tạo FastAPI và runtime, bind các API/service theo thứ tự gốc, gắn middleware/router/static. services/lifecycle.py khởi tạo DB, đọc settings/model/credential CMS, áp dụng preset theo điều kiện và đóng transport khi shutdown.

```text
UI event → endpoint → authentication/ownership → service/domain helper
                                                 ↓
                                       database / gateway / TTS
                                                 ↓
                                 JSON hoặc SSE → state/hooks → view

CMS event → controller → request → admin API → service/database → UI
```

Shared runtime là module main. Modules nhận runtime qua bind_* và gán hàm rõ ràng. runtime.helper đọc helper hiện tại; giữ monkeypatch/worker facade và identity FastAPI Depends. Đây là lớp tương thích, chưa phải dependency injection hoàn toàn độc lập. Không đổi thứ tự bind hoặc tạo current_user/db_session mới tùy tiện.

### 3.1 Roleplay

1. Mở phòng: tải members/history/preferences và chuẩn bị tài nguyên media.
2. Gửi tin: xác thực, kiểm quyền phòng và kiểm nội dung theo cơ chế hiện có.
3. plan_room lập GroupPlan gồm speakers/interaction/reason/scores.
4. Lưu tin user; assemble context riêng của speaker, bổ sung instruction nhóm.
5. Chọn model/options; gọi gateway; gửi delta/metadata qua SSE.
6. SentenceSpeech có thể chuẩn bị voice theo đoạn; hooks client cập nhật audio/reaction/action.
7. Lưu answer/log, cập nhật quan hệ; phân tích memory/state/reflection chạy nền.
8. Speaker tiếp theo có thể đọc reply vừa lưu; suggestion nhóm chỉ ở speaker cuối.
9. Cancel/rời phòng/tắt âm: module stream/audio dừng hoặc bỏ callback cũ theo state/epoch.

Endpoint nonstream và stream có orchestration/deadline riêng; không coi mọi branch sinh suggestion cùng một thời điểm. Xem api/roleplay_chat.py và services/roleplay_inference.py.

### 3.2 Assistant

Xác thực → purpose/model được phép → file/history/memory → prompt purpose → model chain/fallback → JSON/SSE → lưu history/log → suggestion/reminder. assistant_pipeline xử lý extraction; assistant_history giới hạn history; assistant_inference gọi model. User chỉ chọn model khi CMS cho phép.

### 3.3 CMS

admin.ts giữ state/request/navigation/wiring; wrapper chuyển xử lý sang controller miền. API kiểm docs_auth trước đọc/ghi quản trị. AdminRuntime getter/setter đọc state hiện tại, tránh snapshot cũ sau save/reload. Controller import type-only, không tạo vòng import runtime.

## 4. Thuật toán: rule, retrieval và model

| Tác vụ | Kỹ thuật | Model call |
| --- | --- | --- |
| Dialogue/Assistant | Prompt + LLM gateway | Có |
| Character compilation | Schema và LLM extraction trên source | Theo pipeline |
| Speaker local | Rule, cosine từ vựng, topic, fairness | Không |
| Speaker decision | Laya/Jev-compatible A/B probabilities | Worker riêng |
| Knowledge retrieval | Counts/L2/cosine trên token Unicode | Không embedding |
| Memory retrieval | Similarity + importance + recency + pinned | Không ở retrieval |
| Suggest | LLM prompt + parser/validation/fallback | Có |
| Affect nhanh | Regex và state smoothing | Không |
| Turn analysis | TurnAnalysis JSON/confidence | Có |
| Action detector | Streaming parser/rule CMS | Không |
| Companion normal/talk | State audio đúng speaker | Không |
| Reaction generation | Reference → Chatterbox worker | Khi generate |
| Creation moderation | Classifier JSON đa ngôn ngữ | Có |
| Chat moderation | Keyword gate + contextual classifier | Khi gate khớp |

Không có pipeline train model online từ user trong routing hiện tại. Phần lớn orchestration là code cố định kết hợp các model tích hợp.

### 4.1 Speaker local: group_routing.py

Ưu tiên: phòng một người → nhắc tên/@ một người → chọn character:id → everyone → nhắc nhiều người (tối đa hai ở nhánh này) → follow-up ngắn → score ranking. History tối đa 60 messages. Query <=8 từ ghép message user trước tối đa600 ký tự.

Profile gồm description/role/backstory/goals/likes/support. Vector tần suất chuẩn hóa L2. relevance là cosine; topic_fit là giao tập topic. affinity thêm empathy×0.18 khi comfort và humor×0.12 khi fun.

```text
score = 0.5×relevance + 0.5×topic_fit + affinity
        + 0.07/(1+số lượt trong 6 turn gần)
        - 0.045 nếu vừa nói cuối
```

Xếp điểm giảm dần, số lượt tăng dần, roster order. Đôi tự phát cần >=2 turns, không có đôi trong hai turn gần, score người thứ hai>=0.18, chênh<0.28 và khác topic/role. Pair/exchange request kích hoạt trực tiếp. everyone lấy toàn roster. exchange/complement luân phiên theo số cặp trước. Đây là heuristic, chưa chứng minh hiểu ngữ nghĩa/công bằng tuyệt đối.

### 4.2 Decision thử nghiệm: group_decision.py

Mặc định GROUP_ROUTER_MODE=local. decision bỏ qua explicit selection/follow-up. Request: user<=1200 ký tự, topic<=300, room name<=100, bốn dialogue cuối<=180 mỗi dòng, tối đa sáu character profiles ngắn.

Mỗi người hỏi A=should speak, B=remain silent. Transport HTTP /v1/systemone hoặc Modal GroupRouter. Kiểm xác suất hữu hạn [0,1], A+B sai lệch<=0.02. Chọn P(A)>=0.65 mặc định. Chênh toàn nhóm<0.05, không ai đạt, timeout/lỗi → local fallback. Timeout default1.5s, clamp0.2–5s. Giữ roster order cho người được chọn.

Cold call Modal timeout có thể tiếp tục để làm ấm worker. Đây là adapter decision tương thích kiểu Jev; chưa tích hợp mọi harness/UHP. Có thể tăng latency/cost và chưa được chứng minh tốt hơn local.

### 4.3 Knowledge/memory: retrieval.py

Token Unicode \w+, counts/L2, cosine tích vô hướng. Chunks mặc định750 từ, overlap80, step670. Knowledge lọc character/room link và cutoff page/chapter; top4, mỗi text<=1800 ký tự, score>0.02 hoặc query rõ về document.

Memory lọc visibility USER_GLOBAL/CHARACTER_PRIVATE/ROOM_SHARED và ownership. Score:

```text
0.48×similarity + 0.20×importance + 0.14×recency
+ emotional_bonus + 0.06×pinned
recency = 1/(1+age_days/30)
emotional_bonus = 0.12 cho event/preference/llm_extracted
```

Pinned xếp trước unpinned; top5. Duplicate content casefold equal hoặc cosine>0.9 gộp, tăng importance nếu cần. Đây là lexical RAG, không vector DB/semantic embedding. Quét chunk/memory có thể chậm khi dữ liệu lớn; cắt từ/ký tự chưa phải token budgeting chính xác.

### 4.4 Persona, context, ngôn ngữ: engine.py

assemble dùng tối đa24 recent messages, character core, story context, knowledge/memory, relationship/state, năm tasks, ba reflections và năm relationship events. Turn instruction khóa ngôn ngữ cho dialogue, action beats và narration.

Detector dùng Unicode script + từ vựng; message mới ưu tiên, history/preference fallback khi không rõ. Không phải detector ML có benchmark đầy đủ. Mixed-language/câu ngắn/model không tuân thủ vẫn có thể sai. UI locale và message language có fallback khác nhau.

### 4.5 Suggest đúng ngôi

Context bốn dialogue cuối, speaker labels HUMAN_USER/CHARACTER. Dòng dài>240 giữ đầu/cuối120; latest user>600 giữ đầu/cuối300. Description<=240, role<=120, strengths3, previous suggestions3; nhóm thêm topic/title khi relevant.

Prompt khóa USER là speaker, CHARACTER là receiver; I/my thuộc user, you/your thuộc character. Anh/em, chị/em theo xưng hô của latest user, không đoán từ gender. Output @@question1|question2|question3. Parser/validation phát hiện định dạng/ngôn ngữ/viewpoint và fallback. Chưa có giải quyết đại từ hoàn hảo.

suggestion_stream.post_stream_suggestion_wait trả2.5s cho phần chờ sau stream, kèm budget/deadline độc lập. Không kết luận mọi endpoint luôn sleep đúng2.5s.

### 4.6 Quan hệ và cảm xúc

Khóa user+character; các user không dùng chung score. familiarity mới=min(1,f+0.0035+0.0065×(1-f)). Mốc0.06/0.16/0.32/0.52/0.75 đổi stranger/acquainted/familiar/trusted/close/deeply close. Trust/affection/tension cập nhật theo regex personal/positive/repair/negative.

Affect nhanh VI/EN: sad/tired/angry/anxious/happy/apologetic. Mood smoothing0.58 cũ+0.42 target; intensity0.5 cũ+0.5 target. Inertia giữ hurt/sulking qua vài lượt; nghỉ12h/48h giảm intensity, hồi energy, turn length tiêu energy. Đây là mô phỏng, không phép đo cảm xúc thật.

Background TurnAnalysis ghi mood/event khi confidence>=0.6, memory_worthy>=0.68 và summary<=400. Sau model call kiểm lại source message để không hồi sinh dữ liệu đã xóa. thinking dùng lúc chờ và expression được nhận diện. CharacterFeelings hiển thị tên/%/bar.

## 5. Media và companion

### 5.1 TTS lời thoại

CMS chọn clone/catalog, gender/list và targetvi/en/shared; capability ngôn ngữ mở rộng có cấu hình. API xác thực message/character, spoken_text tách phần đọc, chọn voice/provider, signature cache. SentenceSpeech chuẩn bị từng segment; client streamSpeech/backgroundSpeech điều phối audio/cancel.

Chat đơn autoplay nếu voice capability hợp lệ; nhóm thoại manual. Greeting có luồng autoplay riêng, không thêm reaction đầu greeting. Nút Nghe replay. Browser/iPhone có thể yêu cầu tương tác unlock AudioContext. Gain Web Audio có thể tăng tiếng nhưng nguồn lớn có thể clipping. Nhịp ngắt nghỉ phụ thuộc TTS/model, không chỉ CSS/UI.

### 5.2 Reaction clips

CharacterVoiceSample hoặc CharacterReactionReference riêng → signatureSHA256 voiceID+content → worker character-reactions → CharacterReactionAsset. Có generate/delete/recreate/missing-only; version/token chống ghi kết quả cũ.

Backend validate PCM16 mono/stereo WAV0.15–4s, <=2MB/clip; reference upload<=20MB. Mẫu ngắn có tùy chọn repeat2–3 lần với overlap để vượt5s; dưới khoảng2s có thể vẫn fail. Repeat không bổ sung đa dạng giọng. Reference sạch dài8–15s là hướng dẫn thực hành, không bảo đảm model quality.

Client preload/cache theo voice/language/signature. Reaction beat có thể chạy trước spoken voice; nhóm theo người trả lời. Playback cached clips không dùng GPU; generate mới cần worker. Reaction mute cũng tắt action sound.

### 5.3 Action sound

actionSoundDetector tích text<=32768, parser * hoặc ** và span chưa đóng; tách clause theo dấu câu. NFD/bỏ dấu Latin/đ/lower-case. Trigger '+' cần mọi token cùng clause. Negation VI/EN trong45 ký tự trước match bỏ sound.

Một sound mỗi message, một action đang phát tại một thời điểm, tối đa3s. Cùng rule có variants chọn random, tránh vừa dùng. File chưa decode/no match không consume allowance. useActionSounds preload<=120 entries, hai slots, timeout, user/url/version cache, clip dài cắt3s, fade; gain=master×entry.

Không thêm LLM detect riêng. Sound có thể chạy cùng reaction/voice; vẫn phải chờ token hành động xuất hiện. Không có khả năng chắc chắn phát sound trước khi model viết. Narration không đúng marker/trigger có thể không phát.

### 5.4 Music

Playlist chung CMS cho trang chủ/chat; không nhạc riêng từng character. Client speaker mute/slider và preferences. Web Audio hỗ trợ control mobile; cache/range/preload giảm chờ. Network/tệp lớn/background suspension vẫn có thể gián đoạn. Original music chuyển riêng ngoài Git. Giới hạn reference/action khác nhạc.

### 5.5 Companion update

Phòng đơn match preset elf/tên Selene Moonbrook hoặc elf/avatar elf. companionVisible ở RolePlayApp reset false khi room.id đổi. ChatView nút mắt cùng hàng collapse, bật thay toàn bộ nội dung cột phải, tắt trả profile/feelings/menu.

companionTalking chỉ true khi speakingId match message đúng character; xét history/greeting/automatic speech. Text stream/thinking/speechLoading không bật talk. ElfCompanion dùng normal/talk webm, muted/playsInline/loop; active play, inactive pause; unmount/visibility hidden/frame aria-hidden pause; retry load và resume khi tương tác.

Desktop sidebar khoảng38%, max480px/<=44%, chat phần còn lại. object-fit contain giữ đủ khung cảnh, có thể có khoảng trống. Mobile giữ drawer. Không lip-sync phoneme/generate video realtime/multi-companion nhóm.

## 6. Tạo nội dung, bảo mật và kiểm duyệt

Password PBKDF2-HMAC-SHA256210000 vòng/salt16bytes. Token random, DB lưu SHA256 và expiry; API kiểm quyền. CMS docs_auth, maintenance/account guard. Credential Fernet dùng DOCS_PASSWORD trong derivation: chuyển phải giữ password cũ hoặc nhập/rekey credential.

Character policy đọc mọi trường nội dung, bỏ technical voice/media/ID. Không đổi nội dung có thể bỏ recheck. Classifier ANY language/mixed/obfuscation với JSON allow/block/uncertain. Cấm politics/religion/explicit sexual/minor sexual/harmful; nonsexual under18 không cấm chỉ vì tuổi. Missing config/timeout/uncertain503; block400; quá lớn413. Prompt đa ngôn ngữ chưa chứng minh không false positive.

Chat moderation khác creation: keyword gate VI/EN + contextual classifier. Chuẩn hóa ASCII giảm coverage CJK/Khmer. Chưa có output moderation đồng nhất trước mọi SSE/TTS. Crisis handling assistant tâm lý không đồng nghĩa Roleplay có cùng gate. Prompt boundaries không thay hard enforcement.

Chưa có age verification/guardian consent, reminder2h, detector dependency toàn diện hoặc chứng nhận luật thị trường. URL/download helpers có guards/timeouts nhưng cần review SSRF/DNS khi đổi môi trường. Ownership không tương đương multi-tenant isolation hoàn chỉnh.

Delete room reset cảm xúc/quan hệ và xóa liên quan theo service, nhưng archive logs giữ thiết kế cũ. Full erasure cần retention/purge/export xuyên bảng/archive; manual memory ngoài phạm vi reset có quy tắc riêng.

## 7. Dữ liệu, backup và đóng gói

SQLite/SQLAlchemy: accounts/profile/session; character/spec/version/publication/assets; room/member/story/messages/alternatives/suggestions; document/chunk/knowledge; memory/relationship/state/event/reflection; speech/run/part/voice-log; model/settings/request/audit; references/reactions/actions/music. Asset upload/cache có thể là BLOB; original media/filesystem ở DATA_DIR/thư mục riêng.

Git không tự chuyển CMS data/secrets. VoiceID external vẫn cần đúng provider/account. service_data.py backup qua SQLite backup API, ZIPmanifest/checksum/table counts, integrity/restore staging vào target chưa tồn tại. Download Modal phải snapshot nhất quán, tránh bỏ WAL. Giữ DOCS_PASSWORD, data/music và accounts là điều kiện bàn giao.

Docker multistage buildUI/Python runtime/nonroot/healthcheck; compose một web process và persistentDATA_DIR, envfile ngoài Git. entrypoint kiểm UI/credential/write permission. Reaction generate disabled nếu chưa worker nhưng saved clips vẫn dùng.

Modal hiện min1/max1 web, concurrent20/target12, scaledown2s; SQLite Volume single-writer. Workers min0 theo nhiệm vụ. Chưa chứng minh200–500 concurrent users hoặc auto scale web nhiều instances. PostgreSQL cần adaptation connect_args/migrations, không chỉ đổi URL. Tăng tải cần shared transactional DB/queue/objectstorage/pooling và benchmark.

## 8. Module và nguyên tắc sửa

249 backend functions →21API+16service modules. API HTTP/dependency/orchestration; service business/data/model/media; main composition/facade. Domain cũ engine/gateway/retrieval/group/audio/policy giữ riêng. Vẫn có shared runtime và functions lớn; đây không phải xóa hết coupling.

CMS92handlers→11controllers: dashboard/characters/homeSections/models/assistants/assignments/logs/database/access/presentation/bootstrap. admin.ts state/request/event wiring; typed getters tránh stale values. Các voice/music/editor modules giữ riêng.

Roleplay9pure views: HomeBackdrop/Home/Discover/Characters/System/Create/Chat/Settings/Memory. Hooks/effects/request/audio ở RolePlayApp và dedicated hooks; presentation/types tách. Companion truyền typed props, không gọi TTS trong view. Assistant giữ frontend chuyên trách hiện có.

Bản đồ đầy đủ: [CODE_STRUCTURE.md](CODE_STRUCTURE.md). Các layer đều chạy cùng web app, không tự thêm network call do tách file. Muốn sửa feature: giữ ownership/policy trước mutation; không đổi Depends identity/order bind; giữ cancellation/audio order; API fixture chỉ cập nhật khi contract thực sự đổi.

## 9. Gateway, logs và latency

Registry/assignments chọn model purpose, options/fallback. gateway/chat_transport direct/remote có timeout/deadline/circuit handling. AIRequestLog ghi product/purpose/model/room/message/character/timing/error/usage theo call. Nhóm phải đối chiếu từng speaker, không coi một log là toàn roster.

SSE cải thiện thời gian thấy text đầu, không tự giảm generation. Coldstart/queue/network/proxy buffering/media decode khiến client timing lớn hơn upstream. Suggest/TTS/analysis có call/phí riêng. Usage logs chưa là billing reconciliation.

Đo server preparation/upstream header-firstcontent/client-firstchunk/full answer/suggestion/TTSfirstaudio/cache/router/media-range. Cancellation không tự chứng minh quá tải. MediaGET dài cần xem bytes/range/network. Không cam kết latency cố định hay autoplay mọi browser.

## 10. Tích hợp AIBox và bàn giao

Same-domain có thể reverse proxy /companion/ và /api/companion/; hiện có URLs root nên cần base-path/API config và asset/SSE tests. Chưa tích hợp đầy đủ SSO/external user mapping/tenant/quota/payment. AIBox quản identity/billing; companion cung cấp usage/request_id, reserve/settle/release idempotent khi có contract BE.

Bàn giao: source branch/tag, build/container/runbook, envtemplate, privateDBZIP/media, secret kênh riêng, password decrypt cũ, provider accounts và acceptance checklist. Chưa deploy Modal trong tác vụ này.

## 11. Kiểm chứng và các giới hạn

Bản module trước video đã đối chiếu AST249backend/92CMS/9views,434dependency, API/routeorder; backend292pass23fail, frontend65pass3fail đều lỗi baseline. Build và Edge CMS/catalog smoke đạt. Không gọi live model/GPU/TTS.

Bản update build thành công (528 chuỗi × 6 locale), hai test elf detection/talk theo đúng audio speaker đạt. Edge với phòng giả xác nhận nút mắt bật/tắt, profile được thay/khôi phục, video normal muted/loop/playsInline phát thực tế và contain. Sidebar 449px trên workspace1182px (khoảng38%). API contract + backup/restore + startup đạt7/7. Backend/Modal/Docker/compose giống d3d2882. Không coi smoke video là kiểm thử voice provider thật hoặc iPhone thật.

Frontend update chạy toàn suite: 67 passed, 3 failed; ba failure vẫn là reaction metadata/slots và animation gate đã có trước. Lỗi backend baseline: moderator fixture thiếu; greeting expectation cũ; voice fake thiếu spec. Không đổi policy/cache để ép test pass trong tích hợp. Ưu tiên tiếp: staging provider/audio, testfixtures, moderation output/multilingual/age, loadbenchmark, DBscale, SSO/billing và retention.

## 12. Inventory và cách tái xuất

[AI_COMPANION_API_INVENTORY.csv](AI_COMPANION_API_INVENTORY.csv) liệt kê decorator method/path/handler/source toàn cây backend. [AI_COMPANION_MODULE_INVENTORY.csv](AI_COMPANION_MODULE_INVENTORY.csv) liệt kê module/classes/functions/handlers và dòng. Inventory static không chứng nhận endpoint production.

Chạy python -X utf8 scripts/export_system_report.py để tái xuất inventories và reports/AI_Companion_System_Report_2026-10-13.docx từ báo cáo Markdown này. Script không mở database hoặc lấy secrets.


## Phụ lục A. Danh mục chi tiết chức năng Assistant, Roleplay và CMS

Các mục sau được cập nhật từ bản kiểm kê trước. Với module/algorithm/video/safety và version, ưu tiên phần chính của báo cáo này.

# BÁO CÁO CHỨC NĂNG HIỆN TẠI — AI COMPANION

Ngày rà soát cập nhật: 13/10/2026 (Asia/Saigon).
Tên dự án trong báo cáo: AI Companion. Tên hiển thị hiện có trong sản phẩm: Avibi Platform / Avibi CMS.

## 1. Mục tiêu và phạm vi

AI Companion là nền tảng đồng hành AI kết hợp trợ lý theo tác vụ, nhân vật nhập vai, hội thoại bằng văn bản và giọng nói, ký ức, quan hệ tiến triển và công cụ quản trị. Assistant hỗ trợ nhu cầu thực tế; Roleplay cung cấp trải nghiệm đồng hành theo nhân vật; CMS điều hành nội dung, model, âm thanh và giám sát.

Báo cáo phản ánh mã nguồn trong workspace tại ngày rà soát. “Có triển khai” nghĩa là có mã xử lý hoặc giao diện tương ứng; không đồng nghĩa đã deploy, đã cấu hình gateway hoặc đã kiểm thử trực tiếp trên production. Các tính năng cần API key, model, file mẫu hoặc worker chỉ hoạt động khi phụ thuộc đã sẵn sàng. Báo cáo không công bố khóa API, thông tin đăng nhập hay dữ liệu hội thoại thật.

| Khối | Vai trò | Điểm vào |
| --- | --- | --- |
| Platform | Đăng nhập, tài khoản, điều hướng, đồng bộ hai ứng dụng | /avibi-platform |
| Assistant | Trợ lý tổng quát và các tác vụ chuyên biệt | /ai-assistant?workspace=1 |
| Roleplay | Nhân vật, cộng đồng, chat riêng và phòng nhiều nhân vật | /role-play-ai?workspace=1 |
| CMS | Quản trị nội dung, cấu hình và quan sát vận hành | /admin |
| Backend | API, prompt, model, lưu trữ và các công việc nền | character_chat |
| Worker | Xử lý avatar và tạo bộ clip phản ứng khi cần | modal_app.py / modal_reactions.py |

## 2. Nền tảng và tài khoản

| Chức năng | Cách dùng và phạm vi hiện tại |
| --- | --- |
| Đăng ký, đăng nhập, đăng xuất | Tài khoản người dùng, phiên xác thực; CMS có cơ chế xác thực quản trị riêng. |
| Hồ sơ | Tên hiển thị, giới thiệu, avatar; đổi mật khẩu bằng mật khẩu hiện tại. |
| Theme | Sáng/tối; lưu lựa chọn tài khoản và đồng bộ giao diện. |
| Ngôn ngữ | Chọn locale có gói dịch hỗ trợ; màn chờ khi chuẩn bị dữ liệu, thông báo khi thiếu bản dịch. |
| Khung workspace | Sidebar chung; Assistant và Roleplay chạy trong iframe, có điều hướng bằng postMessage. |
| Lịch sử gần đây | Danh sách chat theo ứng dụng; mở lại, xóa lịch sử và cập nhật danh sách. |
| Thu gọn sidebar | Điều chỉnh bố cục, có ghi nhớ trạng thái tại client. |
| Nhắc nhở | Toast và thông báo trình duyệt khi đã cấp quyền; kiểm tra nhắc đến hạn. |
| Responsive và giảm chuyển động | CSS cho các kích thước màn hình và một số hiệu ứng tôn trọng reduced motion. |

## 3. Assistant

### 3.1. Các tác vụ

| Tác vụ | Mục đích | Lưu ý |
| --- | --- | --- |
| Trợ lý tổng quát | Hỏi đáp, soạn thảo, lên kế hoạch, giải thích, tóm tắt | Chất lượng phụ thuộc model và dữ liệu đầu vào. |
| Tâm lý | Lắng nghe, hỗ trợ gỡ rối cảm xúc | Prompt hướng đến đồng cảm, không chẩn đoán. |
| Sức khỏe | Giải thích thông tin sức khỏe thận trọng | Không thay thế chuyên gia y tế. |
| Học tập | Giải bài, hướng dẫn từng bước, dùng tài liệu người gửi | Không suy diễn phần tài liệu không đọc được. |
| Tarot & Tử vi | Nội dung tham khảo, chiêm nghiệm; xử lý câu hỏi và dữ liệu minh họa | Không bảo đảm dự đoán tương lai. |

### 3.2. Hội thoại và dữ liệu

| Chức năng | Triển khai hiện tại |
| --- | --- |
| Trang chủ Assistant | Thẻ tác vụ, lời giới thiệu, câu chào và câu bắt đầu; tiếp tục các cuộc chat. |
| Tạo và quản lý chat | Tạo cuộc hội thoại theo tác vụ, đọc lịch sử, xóa chat. |
| Trả lời streaming | SSE đẩy nội dung tăng dần; lưu câu trả lời và ID ổn định. |
| Gợi ý tiếp theo | Ba gợi ý tin nhắn user; sinh song song và gửi event riêng, có deadline và fallback. |
| Chọn model | Chỉ hiện và chấp nhận lựa chọn user khi CMS cho phép từng tác vụ; còn lại dùng phân công của tác vụ. |
| Model theo tác vụ | Model chính và chuỗi fallback; tham số sinh lấy theo cấu hình model. |
| Tài liệu đính kèm | Upload, liệt kê, đọc nội dung và xóa file trong chat; trích xuất nội dung theo định dạng hỗ trợ. |
| Đầu vào hình ảnh | Có xử lý ảnh đính kèm và tối ưu ảnh; đọc ảnh cần model có khả năng phù hợp. |
| Ghi nhớ cá nhân | Bật/tắt ghi nhớ; thêm, sửa, xóa mục ghi nhớ làm ngữ cảnh. |
| Nhắc nhở | Tạo, sửa, xóa và báo đến hạn; tùy lựa chọn thông báo trên client. |
| Prompt tác vụ | Prompt chung và prompt riêng từng tác vụ; có quản trị nội dung trong CMS. |
| Quan sát | Ghi log lượt gọi, model/gateway, lỗi, runtime và thời gian client nhận nội dung/gợi ý. |

Không diễn giải nút “Tạo trợ lý” trong CMS là bằng chứng đã có nền tảng tác vụ tùy ý hoàn chỉnh. Giao diện tạo hiện có, nhưng API lưu profile chỉ nhận các purpose nằm trong registry prompt hiện tại. Cần mở rộng registry/backend trước khi khẳng định mọi trợ lý mới tự tạo đều chạy trọn luồng.

## 4. Roleplay — nhân vật và khám phá

| Nhóm | Chức năng hiện có |
| --- | --- |
| Trang chủ | Slogan “Bước vào câu chuyện. Sống cùng nhân vật.”, ảnh giới thiệu và carousel. |
| Carousel | Dùng avatar nhân vật có sẵn; tự dịch chuyển khoảng 5 giây, có nút trái/phải; hiệu ứng phản chiếu; bỏ nhân vật thiếu avatar ở phần giới thiệu. |
| Bộ sưu tập | Nhân vật của tôi, nhân vật hệ thống, cộng đồng. |
| Tìm và lọc | Tìm theo tên/mô tả/tag; bộ lọc hiển thị, loại; các mục nhỏ như tất cả, trending, yêu thích, phòng nhóm. |
| Danh mục trang chủ | Cấu hình danh mục, bố trí nội dung và trạng thái hiển thị từ CMS. |
| Thẻ nhân vật | Avatar, tên, mô tả/giới thiệu, số lượt sử dụng, phản ứng và các nút thao tác. |
| Yêu thích | Lưu lựa chọn yêu thích của user; phân biệt với các reaction công khai. |
| Cộng đồng | Nhân vật công khai, clone vào bộ sưu tập, đánh giá và theo dõi tác giả. |
| Phòng công khai | Có API công khai phòng và bắt đầu hội thoại từ phòng được chia sẻ. |
| Thông tin nhân vật | Xem thông tin card, vai trò, mô tả, thành viên liên quan và thao tác hiện có. |

### 4.1. Tạo và quản lý nhân vật

| Chức năng | Triển khai |
| --- | --- |
| Tự sáng tạo | Nhập thông tin nhân vật, vai trò, tính cách, cách nói, lời chào và các yếu tố card. |
| Sinh nhân vật bằng AI | API generate hỗ trợ tạo card từ yêu cầu; phụ thuộc phân công model. |
| Tạo từ truyện/tài liệu | Upload hoặc lấy nguồn từ URL, khám phá nhân vật, tạo từ tài liệu và gắn tri thức. |
| Tạo bản sao | Luồng mirror riêng; mô phỏng theo thông tin đầu vào và quy tắc an toàn. |
| Tạo phòng chat | Chọn nhân vật trong bộ sưu tập, cấu hình tên/phòng và thành viên. |
| Công khai/riêng tư | Có cập nhật publication của nhân vật và phòng. |
| Chỉnh sửa/xóa | Cập nhật card, avatar và trạng thái; xóa theo quyền. |
| Avatar và biểu cảm | Upload avatar, xử lý tài sản và truy vấn ảnh biểu cảm/trạng thái; phụ thuộc worker/model tương ứng. |
| Nhân vật hệ thống | Admin tạo/sửa preset; người dùng sử dụng bản sao phù hợp luồng preset. |

### 4.2. Hội thoại Roleplay

| Chức năng | Triển khai |
| --- | --- |
| Chat một nhân vật | Stream nội dung, lưu lịch sử và dùng card cùng ký ức/quan hệ làm ngữ cảnh. |
| Chat nhiều nhân vật | RoomMember, chọn/định tuyến nhân vật trả lời và xử lý từng phản hồi. |
| Câu chào | Chuẩn bị voice câu đầu và tự phát khi mở phòng; không phát clip phản ứng mở đầu trước câu chào. Quyền autoplay của trình duyệt vẫn áp dụng. |
| Gợi ý | Gợi ý cho phản hồi sinh sau; gợi ý ở câu chào đầu đã được ẩn/bỏ. |
| Dừng/ngắt | Hủy luồng, đánh dấu câu chưa hoàn tất và dọn audio phù hợp. |
| Sinh lại | Regenerate phản hồi, lưu alternative; voice chuẩn bị theo phản hồi thay thế. |
| Mở sau xóa lịch sử | Nếu nhân vật còn tồn tại thì luồng tạo/mở phòng mới được dùng; tránh giữ room ID đã xóa. |
| Ngôn ngữ từng lượt | Detect tin nhắn user, inject output language cho lời thoại, action beat, mô tả và phản ứng. Không dùng thêm LLM chỉ để detect ngôn ngữ. |
| Tài liệu và tri thức | Document, chunk, knowledge của nhân vật/phòng; truy xuất ngữ cảnh trước khi gọi model. |
| Ký ức | Xem/quản lý ký ức của nhân vật hoặc phòng; có dữ liệu pinned, importance và ngữ cảnh gần đây. |
| Trạng thái chuyện | Lưu RoomStoryState và dùng thông tin diễn biến để giữ tính liên tục. |
| Nhắc việc | Có API daily tasks; cần phân biệt với nhắc nhở riêng của Assistant. |
| Prompt inspector | Có endpoint xem trace lớp prompt, ký ức và trạng thái; không được suy ra là công khai toàn bộ prompt hoặc secret. |

### 4.3. Quan hệ và cảm xúc

Backend lưu familiarity, trust, affinity, tension và respect theo user–nhân vật; lưu emotion, energy, mood, intensity. Trạng thái được đưa vào prompt để điều chỉnh biểu đạt và tiến triển quan hệ. Đây là trạng thái mô phỏng, không phải phép đo cảm xúc tâm lý thực của user.

Cột thông tin trong phòng một nhân vật hiện có cụm mới:

| Icon | Ý nghĩa | Dữ liệu |
| --- | --- | --- |
| 🥰 | Thân thiết | familiarity |
| 🤝 | Tin tưởng | trust |
| 💗 | Thiện cảm | affinity, trả qua trường affection |
| 😤 | Căng thẳng | tension, trả qua trường conflict |
| 😊 / 😔 / 😠 … | Biểu cảm hiện tại | emotion |

Các chỉ số có thanh nhỏ; tên và phần trăm trong tooltip theo locale. Tải qua API relationship riêng, cập nhật sau lượt chat, không thêm lượt LLM. Các nút ❤️ 😂 🔥 👍 😮 có sẵn là lượt phản ứng cộng đồng, không phải chỉ số quan hệ riêng này.

## 5. Voice và các lớp âm thanh

### 5.1. Giọng nhân vật

| Chức năng | Triển khai / điều kiện |
| --- | --- |
| Giọng API hoặc clone | CMS chọn nguồn; giọng API có danh sách theo giới tính, clone có upload và cấu hình mẫu. |
| Giọng Việt/Anh | Chế độ dùng chung hoặc gán riêng vi/en; ngôn ngữ mẫu và đích gán giọng là hai lựa chọn khác nhau. |
| File mẫu | CMS xem file đang gán đúng shared/vi/en; nghe thử và cắt đoạn trước upload. |
| Voice volume | Cấu hình tại CMS; có hỗ trợ tăng tới 200% bằng gain ở client. |
| Eligibility | Dựa trên ngôn ngữ nội dung lời nói, độc lập với ngôn ngữ giao diện. |
| Giới hạn ngôn ngữ | Voice hiện hỗ trợ tiếng Việt và tiếng Anh; nội dung ngôn ngữ khác không có nút nghe phù hợp. |
| Chuẩn bị sớm | Câu/đoạn văn bản đủ điều kiện được đưa vào hàng đợi TTS khi text còn stream. |
| SSE PCM | Đọc speech.audio.delta, decode PCM16, nối buffer trên AudioContext, hoàn tất theo event done. |
| Không tự đọc phản hồi mới | Chuẩn bị audio nền; user bấm Nghe để phát phần đã có và theo dõi phần mới. |
| Lưu server | Lưu phần speech và compact WAV hoàn tất trong database; tái sử dụng ở lần nghe sau. |
| Cache client | Giữ PCM/audio job đã nhận, giới hạn bộ nhớ; không gửi lại generation khi job còn dùng được. |
| Đổi giọng/model | Chữ ký cấu hình loại audio cũ để tránh đọc nhầm; không đồng nghĩa xóa mọi tài sản clone từ provider. |
| Tối ưu ngắt nghỉ | Ghép câu đã có và giới hạn chuỗi PCM gần im lặng; không chữa được toàn bộ prosody/vấp của model. |

Chuỗi xử lý: text delta → tách lời thoại đủ đoạn → TTS SSE → lưu PCM + client cache → bấm Nghe → phát phần đã sẵn sàng/theo stream → lưu WAV cuối. Các action beat được loại khỏi lời đọc khi phân đoạn.

### 5.2. Nhạc nền

Playlist chung do CMS quản lý phát ở trang chủ và trong hội thoại. User chỉ bật/tắt tiếng tại UI; không thay file hoặc chọn cấu hình nhạc nhân vật trong phòng. Cấu hình nhạc riêng từng nhân vật đã được bỏ.

CMS quản lý danh sách bài, upload, nghe thử, chọn phần nhạc bằng công cụ cắt, bật/tắt/chọn bài và âm lượng; có xóa bài khỏi danh sách. Audio dùng lại tài sản đã lưu. Autoplay vẫn phụ thuộc tương tác và chính sách trình duyệt.

### 5.3. Clip phản ứng theo nhân vật

| Mục | Hiện trạng |
| --- | --- |
| Nội dung | Âm ngắn như hmm, huh, sigh/chuckle tùy chất lượng model và bộ clip tạo được. |
| Tạo trước | Worker character-reactions tạo bộ clip từ reference; không chạy GPU để generate mỗi tin nhắn chat. |
| Bộ clip | Tách theo shared/vi/en và fingerprint giọng hiện tại; hỗ trợ biến thể cảm xúc. |
| CMS | Mẫu riêng hoặc dùng reference hiện có, tạo/tạo lại, tạo bù, nghe thử, âm lượng, xóa bộ hoặc clip. |
| Preload | Chuẩn bị media trước/vào phòng, dùng cache khi mở lại. |
| Trigger | Event reaction sớm và fallback từ character_message, chống lặp theo message/cooldown. |
| Mute | Nút âm phản ứng ở cột nhân vật; đồng thời tắt âm hành động. |
| Câu chào | Không phát clip phản ứng ở đầu câu chào. |

Tạo bộ clip cần worker GPU cùng thư viện/model và reference đạt yêu cầu. Phát clip đã lưu trong chat không cần chạy inference GPU mới. Cài/weight local nếu có phải theo ổ D theo yêu cầu vận hành.

### 5.4. Âm hành động

| Mục | Hiện trạng |
| --- | --- |
| Thư viện | Sound có sẵn và upload trong CMS; ví dụ lật trang, viết bút, bước chân, đặt bút, quạ kêu, vò giấy. |
| Điều khiển | Bật/tắt file, âm lượng chung và từng sound, từ khóa nhận diện, nghe thử; xóa file upload. |
| Nhận diện | Thuật toán tại client khi delta sinh ra; quét narration trong dấu *…*, không gọi LLM/ML riêng. |
| Quy tắc | Mỗi dòng là một lựa chọn; dấu + yêu cầu đủ các token trong cùng đoạn hành động. |
| Giới hạn | Tối đa một sound mỗi câu trả lời, tối đa 3 giây; không khớp thì im lặng. |
| Song song | Web Audio của sound action tách biệt với clip phản ứng; có thể phát đồng thời. Không bảo đảm luôn có cả hai âm. |
| Tải file | WAV phục vụ đoạn ngắn, cache theo phiên bản; client giữ buffer ngắn và không còn bỏ file bút 5–7 MB. |
| Không suy diễn | “fingers pause on the pen” không được tự biến thành tiếng đặt bút xuống. |
| Mute | Dùng cùng nút âm phản ứng, dừng âm đang phát và không replay âm cũ khi bật lại. |

Âm chỉ phát sau khi hành động cần thiết xuất hiện trong stream. Không thể nhận biết chính xác hành động tương lai trước khi model sinh ra mà không dự đoán; code hiện ưu tiên detect cục bộ và phát từ audio đã tải sẵn.

## 6. Đa ngôn ngữ

| Mã | Ngôn ngữ giao diện có gói dịch |
| --- | --- |
| vi | Tiếng Việt, ngôn ngữ nguồn |
| en | English |
| zh | 中文 |
| ja | 日本語 |
| ko | 한국어 |
| my | မြန်မာ — Myanmar/Burmese |
| km | ភាសាខ្មែរ — Khmer/Campuchia |

Lần build update đã kiểm tra 528 chuỗi × 6 gói dịch ngoài tiếng Việt. Đây là số chuỗi catalog, không phải chứng nhận đã thử mọi màn hình hoặc chất lượng bản dịch như người bản ngữ.

Các gói UI được đóng vào bundle, nên đổi UI không cần gọi model để dịch lại toàn bộ mỗi lần. Khi bổ sung chuỗi giao diện, script thu thập, dịch phần thiếu và lưu JSON; i18n:check xác nhận tính đầy đủ/placeholder.

Giới thiệu ngắn/mô tả thẻ nhân vật có luồng dịch theo locale và cache server, giữ nội dung gốc. Cache dùng lại khi cùng dữ liệu và ngôn ngữ; thay đổi nguồn cần bản dịch mới. Câu chào và ngôn ngữ phản hồi có luồng riêng, không nên suy ra mọi nội dung lịch sử được tự dịch. Tên riêng và character card không bị rewrite khi đổi ngôn ngữ UI.

Màn chờ chỉ cho đi tiếp khi dữ liệu bắt buộc đủ; khi thiếu/sai hoặc API lỗi thì hiện lỗi và cho thử lại/quay về vi. Đủ gói UI không bảo đảm mọi phần giới thiệu động của mọi nhân vật đã có cache cho mọi locale.

## 7. CMS — toàn bộ nhóm quản trị hiện có

| Mục CMS | Chức năng |
| --- | --- |
| Tổng quan | Tổng hợp nội dung, tài khoản, hội thoại và số liệu sản phẩm theo dữ liệu backend. |
| Nhân vật | Danh sách, quản lý nhân vật/preset, card, công khai, ảnh, biểu cảm, voice và clip phản ứng. |
| Âm hành động | Library, upload, preview, volume, rules, bật/tắt và xóa tài sản upload. |
| Nhạc nền | Playlist chung, upload/cắt đoạn, preview, volume, lựa chọn phát và xóa bài. |
| Danh mục trang chủ | Sắp xếp/cấu hình các nhóm nội dung và bố trí nhân vật. |
| Trợ lý AI | Card, tiêu đề, slogan, giới thiệu, lời chào, starters, ẩn/hiện, user_pick và model/prompt của tác vụ. Có UI tạo trợ lý, giới hạn registry như mục 3. |
| Cấu hình AI | Model config, tên admin đặt, API base, credentials, tham số sinh và cấu hình model phù hợp luồng gọi. |
| Phân công model | Gán main/fallback theo nhiệm vụ; prompt riêng và các cài đặt liên quan. |
| Logchat | Bảng lượt hỏi/đáp và suggest, lọc sản phẩm/từ khóa/gateway, model snapshot, thời gian, lỗi và chi tiết. |
| Export CSV | Chọn số log, hôm nay/7 ngày/30 ngày/tự chọn khoảng ngày, áp dụng lọc; tải bản xuất. |
| Log voice | Tra cứu sự kiện TTS, trạng thái, lỗi, thời gian và metadata giọng. |
| Nhật ký hoạt động | Audit thao tác theo nhóm/trạng thái, xem chi tiết. |
| Truy cập | Quản lý tài khoản và access-control; tạo/chỉnh tài khoản theo endpoint quản trị. |
| Database | Danh sách bảng, cột và bản ghi phục vụ quan sát; không khẳng định là SQL editor tùy ý. |
| Làm mới | Nút làm mới theo màn quản trị để nạp dữ liệu hiện tại. |

### 7.1. Model, prompt và fallback

Mỗi ModelConfig có định danh cấu hình, tên hiển thị admin đặt, upstream model/API base và tham số riêng. User chọn model chỉ khi được CMS bật theo tác vụ. Cấu hình main và fallback giúp thử model thay thế khi lỗi; fallback tăng thời gian và có thể phát sinh thêm phí.

API key quản lý theo model/API base/gateway; quyền, hiển thị che khóa và secret môi trường cần cấu hình đúng. CMS không chứng minh gateway đang online hoặc key còn hợp lệ nếu chưa gọi kiểm tra.

Prompt gồm lớp chung, card nhân vật/tác vụ, ngữ cảnh, ký ức, state và khóa ngôn ngữ theo lượt. Có công cụ backup prompt trong backend; không trình bày nội dung prompt nhạy cảm trong báo cáo.

### 7.2. Log bền vững

AIRequestLog giữ snapshot tên model/admin, cấu hình gateway và output để đối chiếu các lượt trước khi thay phân công hoặc dùng cùng upstream model ID ở gateway khác. Xóa lịch sử chat dùng bước archive/snapshot, giữ log phục vụ CMS. Bản ghi cũ trước khi có snapshot có thể thiếu trường; không thể phục hồi chính xác metadata chưa từng được lưu.

CSV là xuất log theo yêu cầu người quản trị, không phải một hệ thống tự backup CSV theo lịch. Lưu log trong database và sao lưu volume là hai nhu cầu khác nhau.

## 8. Chỉ số thời gian và giới hạn phép đo

| Chỉ số | Mốc bắt đầu/kết thúc và cách hiểu |
| --- | --- |
| Latency client / client_first_chunk_ms | User gửi → client nhận chunk nội dung đầu. Gần trải nghiệm chờ đầu ra. |
| Chuẩn bị trên server | Phần chuẩn bị request/context trước gọi gateway theo instrumentation của luồng. |
| Gateway nhận header | Bắt đầu HTTP call ở server → upstream trả header; chưa chứng minh đã có token nội dung. |
| Gateway chunk nội dung đầu | Bắt đầu HTTP call → nhận delta nội dung đầu từ gateway. |
| Runtime / latency_ms | Thời gian thực thi tác vụ được log ở server; tên field cũ latency_ms vẫn còn. Không đồng nghĩa user → token đầu. |
| Client suggestion | Thời gian client nhận gợi ý; tách khỏi câu trả lời chính. |
| Log voice | Thời gian của sự kiện TTS theo loại event và phạm vi ghi log. |

Không cộng “nhận header” và “chunk nội dung đầu” với nhau vì đều bắt đầu từ cùng mốc call. Thời gian client còn gồm network, xử lý client, proxy và queue; runtime server có thể nhỏ hơn client_first_chunk_ms. Các lượt fallback phải đọc attempts/error và metadata mới biết phạm vi tính cụ thể.

Báo cáo không đưa số throughput production: không có benchmark lưu lượng cùng cấu hình/hardware và workload trong lần rà này. Modal max_inputs=20 là giới hạn request đồng thời cấu hình, không phải 20 req/s. Tokens/s cần số token đầu ra và thời gian sinh tương ứng; latency đơn lẻ không đủ.

## 9. Kiến trúc và luồng tổng quát

| Lớp | Công nghệ / nhiệm vụ |
| --- | --- |
| Frontend | React, TypeScript, Vite; tách Assistant, Roleplay, CMS; CSS dùng chung. |
| API | Python, FastAPI; xác thực, endpoints và SSE. |
| Engine | Prompt assembly, quan hệ/state, truy xuất, định tuyến và model invocation. |
| Gateway | HTTP streaming, timeout/retry/fallback, JSON/structured output theo từng tác vụ. |
| Storage | SQLAlchemy; SQLite mặc định trong DATA_DIR; có cấu hình DATABASE_URL. Không khẳng định mọi DB ngoài SQLite đã được kiểm chứng. |
| File/audio | Tài sản và cache trong database, các thư mục đóng gói và Modal Volume tùy loại. |
| Background | Xử lý tài liệu, các tác vụ phản chiếu/state và job/media tùy module. |
| Deploy | Backend Modal phục vụ frontend/dist; các worker được deploy/cấu hình riêng theo nhiệm vụ. |

Luồng chat: user gửi → xác thực/quyền → chuẩn bị prompt và dữ liệu → gateway stream → text delta tới client → lưu message/log → sự kiện kết thúc câu trả lời. Suggestion chạy song song; voice được chuẩn bị khi đã có đoạn; sound action detect trên client; clip phản ứng dùng bộ clip đã tạo.

Các nhóm dữ liệu chính: account/session/profile; character/card/version/publication/assets; room/member/story-state/message/alternative/suggestion; document/chunk/knowledge; memory/relationship/state/event/reflection; speech/run/part/voice-log; model/settings/request-log/audit; music/reaction-reference/reaction-asset/action-sound.

## 10. Tối ưu hiện có và các giới hạn vận hành

| Kỹ thuật đang có | Tác dụng / giới hạn |
| --- | --- |
| SSE | Đẩy output tăng dần; phụ thuộc gateway/proxy không buffer stream. |
| Suggest riêng | Câu chính xong có thể dùng ngay; gợi ý còn chờ deadline độc lập. |
| Reuse kết nối và timeout | Giảm khởi tạo HTTP, chặn chờ vô hạn; fallback vẫn có thể làm chậm. |
| TTS theo đoạn | Chuẩn bị trước text hoàn tất; nhiều đoạn có thể thành nhiều lượt TTS tính phí. |
| Audio server/client cache | Giảm gọi lại/đọc lại; đổi cấu hình làm cache cũ không hợp lệ. |
| Media preload | Giảm chờ khi cần phát; có thể tăng thời gian vào phòng khi đang tải lần đầu. |
| Detect action tại client | Không thêm round-trip LLM; phụ thuộc định dạng narration và rules CMS. |
| UI dịch sẵn | Không gọi gateway dịch UI mỗi lần đổi locale; nội dung động vẫn có cache miss. |
| Một container SQLite | Modal web dùng tài nguyên mặc định, min/max container=1, concurrent max_inputs=20, target_inputs=12; tránh nhiều writer/view trên Volume. |
| Worker GPU tách | GPU để tạo clip/model cần GPU; request chat/phát clip không tải Chatterbox vào API chính. |

Không có bằng chứng trong báo cáo rằng latency đã đạt mức cố định 2–3 giây, âm thanh autoplay chạy trên mọi trình duyệt, detect language chính xác 100%, hoặc mọi callback gateway không bị tính phí sau hủy. Các khả năng này cần kiểm tra thực tế.

## 11. Tình trạng hoàn thiện và phần cần xác nhận

| Phần | Kết luận từ mã nguồn |
| --- | --- |
| Assistant cơ bản và 5 tác vụ | Có triển khai end-to-end; cần model/key cấu hình đúng. |
| Roleplay cá nhân/phòng nhóm | Có triển khai; chất lượng phụ thuộc card, routing và model. |
| CMS quản trị | Có các màn và endpoint; không thay thế xác nhận truy cập production. |
| Gói ngôn ngữ | vi + 6 locale; catalog update 528 chuỗi × 6 locale dịch; tiếng Việt làm nguồn. Nội dung động cần cache/API. |
| Chỉ số quan hệ bằng icon | Đã thêm cho sidebar phòng một nhân vật; chưa xác nhận bằng kiểm thử trên production. |
| Voice vi/en | Có incremental SSE/cache; phụ thuộc upstream TTS và quyền autoplay. |
| Reaction | Có quản trị/generate/cache/preload; phụ thuộc reference và worker GPU. |
| Action sound | Có rule-based streaming; định dạng *…*, bộ từ khóa và file phải sẵn sàng. |
| Tạo trợ lý tùy ý | Có UI; backend profile có giới hạn registry. Giữ lại để phát triển. |
| Mở rộng nhiều instance | Chưa có bằng chứng đã sẵn sàng với SQLite/Volume hiện tại; cần thiết kế DB/queue khi tăng tải. |
| Thống kê chi phí | Metadata usage/log có thể phục vụ quan sát; không chứng nhận đối soát hóa đơn provider. |
| Sao lưu và phục hồi | Có lưu persistent/backup prompt; đã có service_data.py backup/verify/restore và test restore; lịch production cần đội vận hành thiết lập. |

Ưu tiên xác nhận sau deploy: đăng nhập/đổi ngôn ngữ; chat Assistant từng tác vụ; Roleplay mới/cũ/nhóm; greeting autoplay; đổi giọng vi/en và cache; playlist/mute; clip/action; log sau xóa chat; filter gateway và CSV; quyền public/private; lỗi mạng và retry. Đây là danh sách xác nhận vận hành, không phải các phép thử đã thực hiện trong lượt lập báo cáo.

## 12. Build và triển khai

Build UI trong D:\ai_chat_char\frontend bằng npm.cmd run build. Kết quả ở frontend/dist. Kiểm tra ngôn ngữ bằng npm.cmd run i18n:check; chạy i18n:update khi có chuỗi thiếu và đã cấu hình key dịch.

Modal web đóng gói frontend/dist và source API; cần deploy sau build để cập nhật bản đang chạy. Worker reaction/ảnh phải được deploy theo tài liệu riêng và cấu hình secret/volume đúng. Báo cáo này không thực hiện deploy, không gọi live gateway và không thay các luồng sản phẩm.

## 13. Nguồn đối chiếu

| Nguồn code | Nội dung đối chiếu |
| --- | --- |
| frontend/src/assistant/AssistantApp.tsx, config.ts | Workspace, tác vụ Assistant, account và chat. |
| frontend/src/roleplay/RolePlayApp.tsx | Catalog, tạo nhân vật/phòng, streaming, greeting, sidebar. |
| frontend/src/roleplay/CharacterFeelings.tsx | Icon quan hệ và API refresh. |
| frontend/src/roleplay/backgroundSpeech.ts, reactionCache.ts, useActionSounds.ts | Audio chuẩn bị/cache/phát. |
| frontend/src/admin.ts và admin/* | Màn CMS, model, voice, playlist, reaction, log và export. |
| frontend/src/uiLocales.ts, locales/*, scripts/ui-locales.cjs | Gói dịch, kiểm tra và tạo bản dịch. |
| character_chat/main.py và memory_routes.py | API sản phẩm, profile, relationship, prompt-trace và quyền. |
| character_chat/engine.py, gateway.py, chat_transport.py | Prompt, detect language, quan hệ, transport/timing. |
| character_chat/incremental_voice.py, voice.py, reaction_sounds.py, action_sounds.py, background_music.py | Media, TTS, clip và thư viện âm thanh. |
| character_chat/admin_observability.py, log_archive.py, models.py, db.py | Log, snapshot, export, schema và persistence. |
| modal_app.py, modal_reactions.py | Cấu hình tài nguyên, container, worker và đóng gói. |

Các tài liệu docs được dùng tham khảo nhưng có chỗ đã cũ; báo cáo ưu tiên mã hiện tại. Kèm AI_COMPANION_API_INVENTORY.csv trích từ decorator toàn cây module, gồm file, dòng, method, path và hàm xử lý; không phải schema đã chạy hay bằng chứng endpoint production hoạt động.

## Cập nhật 14/10/2026: Tarot / Tử vi
Assistant có màn chọn Tarot/Tử vi huyền bí dùng ảnh có sẵn, normal/back-to-face flip rồi mở chat. Hai purpose assistant_tarot/assistant_tuvi tách prompt/model và fallback trong CMS. Backend quản bộ78lá theo room trong AppSetting; rút không hoàn lại và chiều ngược/xuôi ngẫu nhiên. Eventtarot đi trước text; kết quả lưu Message.sources và hiển thị bằng ảnh. Nút reset có xác nhận, xóa chat Tarot trong phòng và tạo bộ mới; memory thủ công/uploads/config giữ. Modelreply muộn saureset bị bỏ. Không thay schemaDB. Xem [ASSISTANT_DIVINATION.md](ASSISTANT_DIVINATION.md) cho giới hạn và kiểm thử.


## Server riêng — selfhost/dev (14/10/2026)

Xem SELF_HOSTED_DEPLOYMENT.md. Bản CPU chạy chat trực tiếp qua provider API, không có SDK Modal trong Docker, chặn transport/token cũ. GPU reaction/Laya giữ nguyên code và chưa migration. Router dùng local, clip cũ vẫn được lưu/phát, tạo reaction mới tắt. Không tự đổi SQLite sang PostgreSQL. Docker image Linux được cấu hình kiểm tra qua workflow selfhost.yml; máy phát triển hiện chưa có Docker nên chưa xác minh container locally.
