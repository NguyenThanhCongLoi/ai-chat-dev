# Cấu trúc code và cách sửa từng luồng

## 1. Phạm vi refactor
Thực hiện trong repo cá nhân và workspace hiện tại. Tách vị trí implementation, chuẩn hoá imports/formatting và thêm tài liệu/comment. Không đổi endpoint, schema SQLite, prompt/policy, cấu hình Modal, cơ chế tính phí, thứ tự stream hay quy tắc autoplay.

Backend main.py từ 4.218 dòng còn khoảng 685 dòng: phần lớn là imports tương thích, cấu hình và lắp ráp. 249 hàm chuyển sang 37 module API/service. Main giữ các tên cũ để worker Modal, SentenceSpeech và test dependency overrides tiếp tục hoạt động.

Frontend CMS tách 92 handler thành 11 controller. Roleplay tách 9 view, kiểu dữ liệu và helper presentation; hooks/effects, request và audio orchestration vẫn ở RolePlayApp để giữ vòng đời React.

## 2. Sơ đồ trách nhiệm

```text
HTTP / UI event
   |
   +-- Backend: main.py -> api/ -> services/ -> engine/gateway/db/media modules
   |
   +-- CMS: admin.ts -> admin/controllers/ -> API
   |
   +-- Roleplay: RolePlayApp.tsx -> views/ + hooks audio/cache -> API
```

## 3. Backend: API
| Module | Chức năng |
| --- | --- |
| api/authentication.py | Đăng ký/đăng nhập/profile/avatar/logout |
| api/localization.py | API dịch UI |
| api/documentation.py | Docs/OpenAPI và phân loại API tags |
| api/frontend.py | Phục vụ UI/CMS và các đường dẫn ứng dụng |
| api/assistant_memory.py | Memory/reminder của assistant |
| api/assistant_rooms.py | Assistant rooms/files/model/profile endpoints |
| api/assistant_chat.py | Trả lời assistant, nonstream và SSE |
| api/characters.py | Tạo/sửa/lấy/xoá nhân vật, avatar/biểu cảm |
| api/community.py | Nhân vật public, clone/rating/reaction/follow |
| api/rooms.py | Phòng, nhóm, public rooms, favorites, history |
| api/roleplay_chat.py | Chat roleplay, SSE, regenerate, memory endpoint |
| api/documents.py | Upload/URL/discovery/nhân vật từ tài liệu |
| api/tasks.py | Daily tasks |
| api/voice_admin.py | CMS voice catalog, upload/clone/reference |
| api/voice_preferences.py | Tuỳ chọn voice và âm lượng |
| api/voice_playback.py | Speech stream/cache/listen/timing |
| api/admin_overview.py | Dashboard CMS |
| api/admin_accounts.py | Account/maintenance/access control |
| api/admin_settings.py | Cấu hình, credential/vault |
| api/admin_characters.py | Preset/system character/avatar/expressions CMS |
| api/admin_models.py | Model registry, assignments và assistant purposes |

Tên thư mục api/ không đổi URL: endpoint vẫn là /v1/... hoặc các path hiện có.

## 4. Backend: services
| Module | Chức năng |
| --- | --- |
| services/authentication.py | DB dependency, password/session/account guard |
| services/model_registry.py | Runtime settings, model profiles, credential, vault |
| services/lifecycle.py | Startup/lifespan và đóng transport |
| services/audit.py | Middleware cache/timing và audit events |
| services/gateway_resilience.py | Circuit breaker, deadline/remote chunks |
| services/assistant_history.py | Giới hạn history và liên kết ảnh |
| services/assistant_inference.py | Model chain/fallback assistant |
| services/characters.py | Ownership/spec/presets, định danh/social metadata |
| services/expressions.py | Tạo/cache/deduplicate/backfill ảnh cảm xúc |
| services/deletion.py | Purge dữ liệu và reset cảm xúc, giữ archive logic cũ |
| services/rooms.py | Locale/greeting và quy tắc share phòng |
| services/roleplay_context.py | Trích memory |
| services/chat_logs.py | Snapshot/model options/AI log |
| services/roleplay_inference.py | Stream model và suggest roleplay |
| services/documents.py | Parse tài liệu, kiểm URL/download |
| services/speech.py | TTS catalog, chọn voice, signature, PCM/cache |

Các module miền có sẵn vẫn giữ riêng: engine.py (persona/relationship/context), moderation.py + character_policy.py (kiểm duyệt), db.py/models.py/schemas.py, reaction_sounds.py, action_sounds.py, background_music.py, memory_routes.py, incremental_voice.py, group_routing.py/group_decision.py, gateway.py/chat_transport.py.

### Runtime và thứ tự bind
- main.py tạo shared runtime là chính module ứng dụng, rồi gọi bind_* theo đúng thứ tự gốc.
- Module API/service nhận runtime làm dependency; không import main để tạo vòng phụ thuộc.
- Hàm xử lý được gắn bằng tên rõ ràng, ví dụ runtime.current_user = current_user. Không dùng exec để tải implementation.
- Tham chiếu runtime.helper luôn đọc helper hiện tại. Điều này giữ monkeypatch/dependency overrides và worker facade tương thích.
- Không hoán đổi thứ tự bind hoặc tạo thêm một current_user/db_session độc lập: FastAPI overrides dùng identity của function.
- Helpers còn re-export từ main là lớp tương thích có chủ đích. Code mới nên nằm trong module đúng miền và nhận dependency rõ.

## 5. Frontend CMS
admin.ts giữ state chung, request primitive, layout/navigation, các helper trình bày nhỏ và wiring. AdminRuntime có kiểu; getter/setter đọc state hiện tại, tránh giữ snapshot cũ sau một lần lưu hoặc reload.

| Controller | Chức năng |
| --- | --- |
| dashboard.ts | Dashboard |
| characters.ts | Character editor/create/avatar |
| homeSections.ts | Section trên trang chủ |
| models.ts | Model/connection/credential editor |
| assistants.ts | Assistant profiles/tabs/create/save |
| assignments.ts | Purpose assignment |
| logs.ts | Chat/action logs |
| database.ts | Database viewer |
| access.ts | Account/access control |
| presentation.ts | Modal, format thời gian, generation notice |
| bootstrap.ts | Load và deferred loading |

Handler gốc vẫn có wrapper ở admin.ts, giữ điểm đăng ký DOM event. Import AdminRuntime từ controller là type-only nên không tạo vòng import lúc chạy.

Các editor/audio chức năng đã có vẫn nằm ở admin/voiceSettings.ts, voiceClone.ts, voiceSources.ts, reactionSounds.ts, actionSounds.ts, music.ts, audioClip.ts và logs.ts. Các contract editor/view đặt trong admin/types.ts.

## 6. Frontend Roleplay
| File | Chức năng |
| --- | --- |
| RolePlayApp.tsx | Shared state, effects, async handlers và orchestration |
| presentation.tsx | Render văn bản, payload editor, role labels/tags |
| types.ts | DTO và contract trang |
| views/HomeBackdropView.tsx | Lớp nền/âm lượng trang chủ |
| views/HomeView.tsx | Trang chủ |
| views/DiscoverView.tsx | Cộng đồng |
| views/CharactersView.tsx | Nhân vật của tôi |
| views/SystemView.tsx | Nhân vật hệ thống |
| views/CreateView.tsx | Form tạo nhân vật |
| views/ChatView.tsx | Chat và cột nhân vật |
| views/SettingsView.tsx | Dialog profile/account/preferences |
| views/MemoryView.tsx | Dialog memory |

Các view là hàm render thuần nhận props, không thêm hooks hay React component wrapper vào cây cũ. Điều kiện hiển thị vẫn ở RolePlayApp. Request/TTS/action/reaction không chạy bên trong view.

Voice/music/reaction giữ các module chuyên trách đã có: backgroundSpeech, streamSpeech, voicePreferences, useReactionSounds, useActionSounds, reactionCache, useBackgroundMusic. UI feelings vẫn ở CharacterFeelings.tsx.

Assistant UI vẫn ở assistant/ và dùng pipeline/component chuyên trách hiện có; backend assistant đã được tách endpoint/inference/history/memory.

## 7. Muốn sửa gì thì vào đâu?
- Đăng nhập/quyền: services/authentication.py + api/authentication.py.
- Kiểm duyệt: moderation.py, character_policy.py và call sites API. Đây là thay đổi tính năng riêng, không nằm trong refactor.
- Chọn nhân vật trả lời: group_routing.py/group_decision.py.
- Prompt/suggest: prompts.py, engine.py, services/roleplay_inference.py.
- Thứ tự SSE/voice: api/roleplay_chat.py + services/speech.py + incremental_voice.py.
- Xoá phòng/reset: services/deletion.py + api/rooms.py.
- CMS model: api/admin_models.py + services/model_registry.py + admin/controllers/models.ts.
- Giao diện chat: roleplay/views/ChatView.tsx; orchestration: RolePlayApp.tsx.
- Autoplay/cache audio: giữ sửa ở các module audio, không chèn playback vào view.

## 8. Cách thêm code
1. Chọn module theo trách nhiệm; không thêm business logic vào main.py.
2. Giữ endpoint name/signature/dependency nếu chỉ refactor.
3. Bind helper trước nơi dùng nó làm default Depends hoặc truyền vào router.
4. Với CMS, khai báo state/callback cần dùng trong AdminRuntime và getter/setter ở entrypoint.
5. Với Roleplay view, truyền prop typed; giữ hook và effect ở controller/hook module.
6. Khi API thực sự thay đổi, cập nhật contract fixture có review. Không sửa fixture chỉ để che lỗi refactor.

## 9. Xác minh
```powershell
python -m pytest -q tests
cd frontend
npm.cmd run build
node --test scripts/*.test.cjs
```

- Golden OpenAPI và route order: tests/test_api_contract.py + tests/fixtures/ver1_api_contract.json.
- 249 hàm backend đã được so sánh AST với bản gốc sau chuẩn hoá dependency/import.
- 92 body CMS được so sánh AST; 9 cây React element được đối chiếu sau chuẩn hoá JSX formatting/text liền nhau.
- Frontend strict TypeScript + Vite build đạt, catalog vẫn 526 string.
- Node frontend suite: 65 passed, 3 failed; các test lỗi cache reaction và animation gate cũng lỗi ở source gốc. Không sửa logic cache/animation trong đợt refactor này.
- Edge headless với DB/tài khoản test: các tab CMS (nhân vật, model, assistant, sections, logs, database, quyền, music/action sound) và 5 trang Roleplay home/discover/characters/system/create mở thành công, không có page error.
- Gate riêng API contract + backup/restore + startup đạt. Provider thật và audio end-to-end trên production không được gọi trong đợt này.
- Suite cuối: 292 passed, 23 failed. 23 test lỗi cũng lỗi trên source gốc: fixture moderation chưa stub, kỳ vọng greeting cũ và fixture voice thiếu spec. Không đổi behavior sản phẩm để ép các test này qua.
- Bản source baseline xuất từ Git thiếu nhạc ngoài Git nên có thêm 1 test catalog lỗi do thiếu asset; đây không phải khác biệt logic.
- Refactor không khắc phục các thiếu sót safety đã ghi trong COMPANION_SAFETY_AUDIT.md.
- Kiểm chứng trên local không phải cam kết provider LLM/TTS/GPU luôn hoạt động. Không chạy migration hoặc ghi database production.

## 10. Version và dữ liệu
Giữ tag v1.0.0 và v1.0.0-service.1 làm mốc source cũ. Refactor chưa tự deploy hoặc thay database/backup. Gói CMS đã kiểm tra vẫn dùng cùng schema; không cần clone lại giọng vì đổi vị trí code.

## 11. Companion trên nhánh update
RolePlayApp quản companionVisible/reset room.id; ChatView nhận typed toggle/talking. companionState ánh xạ speakingId đúng character; ElfCompanion quản normal/talk và cleanup; elf-companion.css mở rộng sidebar. Ver1 không video. Báo cáo đầy đủ: [AI_COMPANION_SYSTEM_REPORT.md](AI_COMPANION_SYSTEM_REPORT.md).
