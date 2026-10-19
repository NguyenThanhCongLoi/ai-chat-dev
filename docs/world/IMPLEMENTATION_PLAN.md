# Kế hoạch nâng cấp sau audit

Ngày 17/10/2026. Bản này phân biệt thay đổi **đã làm theo yêu cầu mới cho chat thường** và đề xuất **chưa triển khai**. Không tự chuyển traffic/deploy.

## A. Đã triển khai: chat thường, gồm chat đơn

| Thay đổi | File | Migration/API/Frontend/Prompt | Test và hiệu quả mong đợi |
|---|---|---|---|
| Recall BM25 + accent/alias đa ngôn ngữ hữu hạn | character_chat/roleplay_recall.py; retrieval.py | Không migration, không endpoint mới, không UI mới | Query tương đương lấy lại memory đúng; ACL trước score; không nhét unpinned unrelated |
| Confidence và provenance memory | retrieval.py; roleplay_continuity.py | Thêm source_message_id trong memory payload của prompt | Facts mơ hồ vẫn được gắn confidence; không coi quotation là canon |
| Dedupe bảo toàn phủ định | retrieval.py | Không sửa dữ liệu cũ; exact case/whitespace normalization | Positive/negative memory không bị fuzzy-merge thành một |
| Match lore đúng từ | roleplay_continuity.py | Reuse keywords CMS; không semantic auto-translation | art không kích hoạt bởi heart; VI bỏ dấu; scope vẫn lọc trước |
| Unique short name và cap decision | group_routing.py | Không đổi speaker_mode contract | Selene/Ren/@Name; ambiguous names không force; max 2 auto, everyone explicit giữ |
| Policy regression cập nhật | tests/test_group_decision.py | Expected automatic count đổi 3→2 | Test theo hành vi policy mới, provider vẫn chỉ gọi 1 lần |
| Single chat end-to-end | tests/test_roleplay_recall_upgrade.py | CMS → POST chat → real assemble → mocked gateway → Message/Trace | CMS V1→V2 áp dụng lượt kế, memory/scene cùng được truyền |

Không thêm inference, model/GPU hoặc dependency. Thời gian CPU/DB của BM25 chưa benchmark với kho lớn.

## B. P0: provenance/context đáng tin — đề xuất, chưa làm

- **Files:** retrieval.py, models.py, memory_routes.py, services/deletion.py, api/roleplay_continuity.py; thêm module memory_lifecycle.py.
- **Migration:** source_revision/source_hash, supersedes_id/status; giữ legacy fields, backfill có thể thiếu nguồn. Không rewrite hoặc xóa dữ liệu cũ tự động.
- **API:** đề xuất extend PATCH memory với revision; inspector trả stale/conflict metadata; owner checks giữ nguyên.
- **Frontend:** inspector hiển thị “cần xác minh” và nguồn; người dùng xác nhận fact mới thay fact cũ.
- **Prompt:** memory dẫn xuất fallible; pin AI là quotation; không dùng fact stale như canon.
- **Tests:** source edit/delete, contradiction/negation/numbers, cross-user/room/character, consent toggle, replay.
- **Expected:** ít tự nhận nhớ sai; không phá public/private character identity.
- **Difficulty/cost:** vừa; đọc/ghi CPU, không thêm call bắt buộc.

## C. P0 World: gameplay context + secrets ổn định — đề xuất, chưa làm

- **Files:** academy.py, api/ai_world.py, frontend/src/worlds/AcademyApp.tsx/types hiện có.
- **Migration:** version aggregate, actor→story_role map lưu khi tạo; secret owner/unlock/discovered_by/event/source; migrate bằng ID, không index hiện tại.
- **API:** act giữ whitelist; say trả proposed_actions nếu có; confirm action vẫn server-authoritative với revision/request_id. Không tự hoàn thành quest từ text AI.
- **Frontend:** action card hiện đúng vật phẩm/người nhận/địa điểm; confirm một chạm.
- **Prompt:** nhận allowed inventory, active objective, completed flags được phép, accessible locations và action IDs. Không gửi locked truth.
- **Tests:** đổi cast/thứ tự không đổi secret; người vắng mặt không biết clue; model không cấp vật phẩm; illegal action/replay/CAS; hai ending có hậu quả riêng.
- **Expected:** nói chuyện giúp tiến triển truyện có kiểm soát, không chỉ sinh lời hứa.
- **Difficulty/cost:** vừa–cao; không cần director call mỗi turn.

## D. P1: memory tốt hơn và recap có hạn mức — đề xuất

- **Files:** background.py, roleplay_episode.py, services/roleplay_context.py, retrieval.py; module recap_jobs.py và recall_provider.py mới.
- **Migration:** recap job/status, source ranges/revision; durable outbox nếu yêu cầu retry qua restart. Không chỉ BackgroundTasks.
- **API:** status/retry recap theo owner; opt-in bật/tắt; không tự bật consent cũ.
- **Frontend:** dùng EpisodeNotes hiện có, trạng thái cập nhật gọn; chat composer giữ nguyên.
- **Prompt:** 1 recap hữu hạn sau mốc lượt quan trọng, không regenerate mỗi token; reconcile typed facts với source.
- **Semantic:** optional embeddings sau ACL và dataset; provider/model/env cấu hình; multilingual eval trước bật mặc định. Lexical fallback khi provider lỗi.
- **Tests:** đúng user turn/replies, canceled/deleted room, không tăng call trên cache hit, no source leak, recall@k.
- **Expected:** giảm quên khi paraphrase, không tăng latency đường stream.
- **Cost:** local fallback 0 call; embed query/fact + recap có cap, phải ghi metrics trước quyết định.

## E. P1: relationship và routing theo scene — đề xuất

- **Files:** group_routing.py, background.py, engine.py, schemas.py, api/roleplay_chat.py.
- **Migration:** event idempotency/target actor + structured deltas; persona dimension phải có kế hoạch riêng trước multi-persona.
- **API/UI:** reuse speaker mode; không thêm gameplay tab cho chat thường. Talkativeness trong advanced character editor nếu cần, default tương thích.
- **Prompt:** context relation/scene có nguồn, không dùng điểm để ép intimacy.
- **Rules:** inference đưa proposed event; server validate actor/source/cooldown/clamp rồi cập nhật; tránh phạt mọi NPC vì user tức chuyện bên ngoài.
- **Tests:** user+2 và user+5, distinct perspectives, silence của người không được chọn, talkative không độc chiếm, direct mention bypass remote, “angry at work”.
- **Expected/cost:** hội thoại tự nhiên hơn; deterministic ưu tiên, decision service chỉ khi cần.

## F. P1/P2: presence và authoring

- Shared TTS cache service: services/speech.py và api/ai_world.py dùng adapter chung; message namespace/voice/model/signature, owner checked trước cache hit. Migration metadata audio nếu chuyển blob/filesystem. Test replay không gọi provider.
- Scene soundscape: playlist tag CMS + frontend audio selector hiện có; 0 LLM call; pause hidden, opt-in, volume independent. Không sinh audio mới.
- Return policy: activity timestamps/cooldown/quiet hours/timezone/opt-in; lazy on-open trước push notification. Không dùng agent loop liên tục. Unit test no-op/day boundary/replay.
- CMS prompt preview: api/roleplay_lorebook.py và admin/RoleplayLorebook.tsx; admin-only “entry nào vào context” với test ACL. Không cung cấp raw private prompt qua public endpoint.
- Persona-specific memory: migration persona_id cho Memory/Relationship/Room với default legacy; explicit user switch, không auto-copy.
- Multiplayer và creator World publication: P2 tách luồng sản phẩm; memberships/roles/consent/moderation/version/publish approval, không mở bằng mỗi is_public.

## Gate triển khai

1. Unit/API regression trên SQLite cô lập; World isolation và old room compatibility.
2. Eval persona/lore/recall trên model thật với dữ liệu synthetic, key từ env/CMS; báo token/call và TTFT.
3. Test UI desktop hiện tại, không phát sinh thao tác bắt buộc mới cho chat thường.
4. Backup, deploy image/commit xác định, healthcheck/SSE/provider smoke; chỉ chuyển traffic theo quy trình đã được phép.

Đợt hiện tại hoàn thành A và tài liệu audit. B–F là kế hoạch, chưa được triển khai.
