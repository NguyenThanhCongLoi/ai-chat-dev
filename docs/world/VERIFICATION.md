# Verification — Moonfall Academy

Date: 2026-10-16.

- `python -m pytest tests/test_ai_world.py tests/test_worlds.py tests/test_api_contract.py -q`: **33 passed**.
- Frontend `npm run build`: passed TypeScript and Vite. Existing main-app bundle warning (>500KB) remains; Worlds is a separate lazy-loaded chunk.
- Edge headless, real isolated FastAPI service / SQLite: passed four-character selection, five map nodes, three missions, relationship choice, unlock, ending modal, timeline, reload persistence, mobile horizontal-overflow check, and embedded AIBox entry.
- Final screenshots: `artifacts/academy/c1729e0b/home.png`, `scene.png`, `ending.png`, `mobile.png`, `embedded.png`.
- Browser regression checks explicitly assert NPC panel is static in layout and does not inherit the global full-height sidebar rule.
- Dialogue adapter tested with mocked moderation/provider: correct original persona, correct Roleplay wire model, at most two present speakers, no locked secrets in context, failure leaves revision unchanged.
- Pair relationship keys tested with real-format colon-containing preset IDs.
- No paid provider calls. Actual LLM character quality, production TTS voice IDs and latency remain unverified.
- No push, merge or Modal deployment performed.

## World/chat isolation verification

- 63 additional tests passed: roleplay continuity, episodic notes, speech language and JEV. Together with the 33 above: 96 selected tests passed (not the entire repository suite).
- Database snapshot regression: all non-World tables/settings identical after World CMS save, gameplay, gift, model dialogue and deletion.
- Existing ordinary model assignment and editable prompt unchanged; ordinary private room/history/memory absent from World context.
- Admin auth and stale CMS revision guarded.
- Dedicated CMS browser check passed: actual Basic auth, form load, save and reload. Screenshot: artifacts/academy-cms/8fec4892/cms.png.
- Frontend production build passed. No real provider test or deployment performed.

## Shared background music update

- Frontend production build passed.
- 54 selected backend tests passed: music catalog/CMS, ordinary lorebook/continuity, AI World and API contract.
- Real Edge test with isolated DB and generated quiet WAV passed: no autoplay, shared playlist playback, independent volume storage, TTS ducking to 25% and restoration, mobile overflow check, and music stop when embedded World is hidden. TTS response was a synthetic fixture, not a real provider call.
- Screenshot: artifacts/world-music/a2d0ab79/music.png.
- Ordinary chat music hook and its storage keys were not edited. The host passes the active World state so hidden panels cannot continue music/voice.
- No push or deployment performed.
