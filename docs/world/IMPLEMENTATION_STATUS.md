# AI World delivery status

## Implemented

- Replaced normal Worlds entry with one Moonfall Academy demo.
- Private persistent instances, own instances list, delete/reopen.
- Existing character ID reuse; 2–4 members, four default; add/remove through cast picker.
- Original SVG map, five locations, lock/event indicators, cast portraits.
- Scene-based conversation, local relevant-speaker router, max two replies.
- Existing CMS Roleplay persona/model and TTS voice integration.
- Witness-scoped memories, unlocked-only secret context and UI.
- User-character trust/affinity/respect/rivalry; character-character trust/rivalry consequences.
- Three linked missions, five items, ten authored event definitions.
- Gifts, two persistent finale outcomes, ending reader.
- Timeline filters by type and character, deterministic return-day invitation, progress.
- CAS and bounded replay receipts, ownership checks, strict text moderation.
- VI/EN, responsive baseline, reduced motion, lazy WorldApp route.

## Partial / not shipped

- Not a persistent autonomous society: scene membership is authored, not physical movement simulation.
- Two secret tiers, not the entire five-tier taxonomy.
- No autonomous LLM proposals, reflection jobs, romance/jealousy/fear model, sophisticated learned router or randomized rarity director.
- Shared ordinary-chat background playlist connected: explicit play/pause, World-only volume, TTS ducking, hidden-panel pause. Location-specific ambience remains deferred.
- No custom theme/description/cover authoring, public worlds, marketplace or real human co-play.
- No ordinary MessageSpeech cache for academy lines, SSE dialogue or exactly-once provider billing.
- Dedicated World CMS at /worlds/admin edits World-only dialogue direction, public lore and chat/TTS model assignments. Missions and gated secrets remain authored in academy.py; full story authoring is future work.
- Current storage is existing AppSetting JSON; normalized PostgreSQL schema is a design mapping, not a migration.
- Original Lastlight data/routes remain archived; default UX hides them. Nothing deletes old progress implicitly.

See RESEARCH.md, ARCHITECTURE.md, UX.md and USER_ACTION_REQUIRED.md for sources, operational steps and scope.

## Isolation update

See [ISOLATION.md](ISOLATION.md). World settings never update ordinary-chat assignments or editable prompt. Memory remains separate; no automatic import/export. Shared infrastructure and provider quotas are not operationally isolated.

## Setup guide

See [SETUP_FOR_BEST_DEMO.md](SETUP_FOR_BEST_DEMO.md) for required provider, character, voice, prompt/lore and music settings.
