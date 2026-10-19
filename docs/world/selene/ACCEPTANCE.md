# Chapter 1: implementation and acceptance

## 1. Files and components

Backend:
- character_chat/moonfall.py: pure deterministic state machine, validation, projection and spoiler firewall.
- character_chat/moonfall_store.py: owner-scoped persistence, unlock gate and verified shared-memory lookup.
- character_chat/api/moonfall.py: separate CMS, story/actions, explicit memory bridge, voice and media endpoints.
- character_chat/story_data/echoes_of_moonfall.json: authored chapter, planned chapter slots and manifest.
- character_chat/engine.py and retrieval.py: optional invitation and provenance-checked shared memories in normal Chat.

Frontend:
- frontend/src/worlds/MoonfallApp.tsx: playable scene, intro, exploration, typed transcript, hints, memory and return.
- MoonfallAdmin.tsx: separate /worlds/admin CMS; models/voices, localized copy, clues/reactions/items, memory, registry and manifest.
- WorldCinematics.tsx / worldCinematics.css: reusable manifest-driven player, skip, one-time intro, failure and accessibility fallbacks.
- WorldEffects.tsx / worldEffectRegistry.ts / worldEffects.css: reusable CSS/SVG effects, scoped targets, deduplication and reduced motion.
- MoonfallSound.tsx: shared ordinary Chat playlist, crossfade, separate channels; cinematics duck music while preserving ambient.
- MoonfallHook.tsx: invitation in ordinary single-character Selene chat.
- moonfallTypes.ts / moonfall.css: typed contracts and World-only theme/layout.
- RolePlayApp.tsx and AssistantApp.tsx: opening World and navigating back to an owned Chat room.

Assets/tools:
- image/worlds/selene/moonfall/: optimized user-supplied art, clips and transparent Selene portraits.
- scripts/prepare_world_images.py and scripts/prepare_world_videos.py: repeatable imports, originals preserved.
- .dockerignore: excludes large source originals from runtime Docker images; optimized derivatives included.
- pyproject.toml: packages story JSON.
- Tests: tests/test_moonfall.py and opt-in tests/test_moonfall_browser.py.

The old Academy frontend was archived under artifacts/moonfall-replacement before replacement. Legacy backend saves remain intact.

## 2. Asset manifest

See ASSET_MAPPING.md for all 58 IDs and exact relative paths: 14 backgrounds, 10 props, 9 expressions, 8 video clips, 17 optional audio slots. All 41 visual entries exist. No new placeholder art is required.

Current scene uses supplied overview/outer ruins/gate backgrounds, rune/moonstone/tablet props, supplied map and chapter-complete backgrounds, and transparent elf expressions. Future scenery and reveal clips remain registered without unlocking Chapters 2–8.

Runtime media resolve through /v1/moonfall/assets/{id}. User-provided originals remain untouched; code never needs raw MP4 names.

## 3. Story state

Owner-hashed run key in AppSetting; immutable config snapshot plus config revision, owner, character ID, current chapter/location, intro acknowledgment, discovered clue IDs, story flags, meaningful text signatures, hint level/cooldown, bounded emotional access, typed events, memory rewards and sync status.

CAS revision rejects stale actions with 409. Request receipts prevent duplicate retry rewards. Reload/restart resumes structured state. No video callback modifies clues, unlocks, completion or rewards.

Only Chapter 1 is implemented. Seven later chapter slots stay disabled. Numeric trust gates stay private.

## 4. Clues

Stable IDs rune, statue, inscription. Rune/statue are in outer_ruins; inscription is at the gate. Gate unlocks after one clue. Any two distinct clues complete the chapter.

Inspect actions validate current location/flags. Freeform matching uses accent/case normalization and keyword phrase boundaries against currently available clues; a model response cannot grant clues. Duplicate clue inspection gives no extra progress/trust.

Hints progress through three authored levels with cooldown, idle/stalled-turn checks. Different text locales use stable clue IDs and authored VI/EN fallback.

## 5. Shared memory

Reward ID: SELENE_KNOWS_MORE_ABOUT_MOONFALL.
Scope: NORMAL_CHAT_SHARED.
Fact: You and Selene explored the ruins around the newly awakened runes at Moonfall, comparing the traces you actually found. Her unusual hesitation suggested she knows more than she has shared; the reason remains unknown.

This does not claim the player saw the inscription when they completed rune + statue. No hidden mentor, cause or future event is revealed.

The reward persists inside World immediately on completion. Export to ordinary Chat requires the user's share checkbox and Return action. Export creates one deterministic Memory row with type world_shared and visibility CHARACTER_PRIVATE for the same owner and Selene; replay is idempotent. Chat retrieval additionally checks completed + synced provenance. No transcripts or social graph are copied. Room memory must be enabled for recall.

## 6. Narrator / speech / thought / system

NARRATION: narrator text and optional dedicated narrator VI/EN voice.
CHARACTER_SPEECH: original Selene persona, normal Chat TTS provider and character Voice ID.
CHARACTER_THOUGHT: visibly distinct thought, never TTS.
SYSTEM: progress/unlock feedback, never TTS.
USER input is stored separately from those four output kinds.

Voice is optional. Use Voices to enable automatic reading, or individual Listen controls. The opening narrator and Selene speech support the same opt-in reading setting. Missing TTS does not block play; no forced character voice substitution for the narrator. Unsupported text languages require explicit EN/VI audio selection.

## 7. Missing audio

See ASSET_MAPPING.md: six ambient OGGs and eleven SFX OGGs are optional and currently absent. Exact paths are listed there. BGM uses the existing Chat library, not a duplicated World folder.

Narrator uses provider synthesis, so no prerecorded narrator file is required. Configure separate VI/EN narrator Voice IDs and enabled TTS credentials in /worlds/admin. Selene voice stays in the existing character CMS. Missing audio is silent/text fallback.

## 8. Run and test

Use the existing application environment with WORLD_DEMO_ENABLED=true.
Build: cd frontend; npm ci; npm run build.
Start existing backend: python -m uvicorn character_chat.main:app --host 127.0.0.1 --port 8000.
Sign in through /avibi-platform. Configure /worlds/admin using existing CMS authentication.

Keep the existing Selene system card, assign the World dialogue model and moderation credentials. Default entry gate is two meaningful completed single-chat turns, zero minimum trust and zero day requirement. Admin may set meaningful-turn gate to zero for a controlled demo.

Play: open Selene Chat → invitation → enter World → intro/skip → walk to ruins → inspect rune → chat freely / request hints → inspect statue (or visit gate for inscription) → completion/memory dialog → share → Return → ask Selene about Moonfall. Reopening resumes without replaying intro.

Automated unit/regression checks in PowerShell:
$env:DATABASE_URL='sqlite://'
python -m pytest tests/test_moonfall.py tests/test_character_social.py tests/test_roleplay_continuity.py tests/test_roleplay_episode.py tests/test_roleplay_recall_upgrade.py tests/test_api_contract.py -q

Browser acceptance after build:
$env:RUN_MOONFALL_BROWSER='1'
python -m pytest tests/test_moonfall_browser.py -q

This browser test uses a temporary file DB, mocked generation/moderation/localization, and headless Edge. It checks the full invitation/play/return path, real WebM decoding, rune VFX, thought voice exclusion, selected memory import and actual ordinary Chat SSE prompt/response, saved resume, video failure and reduced-motion behavior. It does not call paid providers.

Screenshots/results: artifacts/moonfall-acceptance/.

Verified: frontend production build; 74 selected unit/regression tests passed, including 19 Chapter 1 tests; browser end-to-end passed with mocked providers. Final artifacts are in artifacts/moonfall-acceptance.

## 9. Known limits / blockers

No blocker for the authored Chapter 1 path. Live LLM/TTS/moderation credentials and real voice playback still need staging verification; tests use mocks. This is not a production load/security certification.

Only VI/EN story text is authored; remaining UI language support uses existing locale handling with EN story fallback. Frontend build reports 31 existing/new UI strings awaiting provider translation and the existing main JS chunk-size warning.

Config changes apply to new playthroughs, not an already saved snapshot. The prototype resumes the existing run for the same character; no automatic reset or destructive migration is performed. Existing CMS configurations saved before the new manifest require reviewing/importing the updated asset registry; do not overwrite author edits or active saves.

The current backend remains SQLite and retains the original deployment concurrency constraints. Do not increase Modal containers or DB writers based on this UI work.

## 10. Recommended next step

Run staging with the real Selene card and provider accounts, configure narrator VI/EN voices, enable voice playback and verify the entire flow manually. Check licenses for supplied/generated art and video. Then tune pacing, hint timing and narration from one user playtest before implementing Chapter 2.

No deployment or push was performed.

## Home intro / Memory Atlas acceptance (2026-10-17)

- Home intro integrated from image/video/moonfall_final_rock.mp4; original retained.
- Optimized WebM: 9,058,509 bytes vs 26,079,913 bytes; 71 seconds, 1280x720/24fps, VP9 + Opus stereo.
- WorldEntry warms the first video while on the home page; WorldHub reuses that HTMLVideoElement. Public media metadata only; no user memory is prefetched. Reduced motion/save-data requests metadata only.
- Current/next media pool is bounded. Exit, hidden World and failed catalog loading pause intro sound. Browser autoplay denial shows a play button.
- Home map uses existing public system catalog only, deduplicates names, excludes hidden/unpublished presets. Unlock status is private to the authenticated owner. Unimplemented character stories stay locked.
- Browser acceptance passed: normal chat → chapter 1 → clues/freeform → memory → normal chat recall → home intro/audio volume → skip → 11-character fixture atlas → shared chapter dialog → resume → return to map → replay/ended → video failure fallback.
- Home intro playback/skip/failure does not write story state or unlock characters.
- Browser screenshots: artifacts/moonfall-acceptance/06-home-intro.png, 07-memory-atlas.png.
- Verification: frontend build passed; 25 Moonfall/API contract tests passed; one end-to-end Edge test passed with isolated SQLite and mock generation providers.
- No deployment or production data changes performed.
