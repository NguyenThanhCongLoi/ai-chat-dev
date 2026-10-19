# User actions — AI World demo

## ACTION 1 — Local/Modal preview

Need: rebuild UI and restart/redeploy the web application.
Why: old deployed frontend does not receive local file changes.
Required: yes to see this version on your existing deployment.
Commands:
- cd frontend; npm ci; npm run build
- cd ..; python -m modal deploy modal_app.py

Use the existing deployment workflow/secrets. No new GPU function deployment is needed.

## ACTION 2 — Real dialogue

Need: existing CMS Roleplay model assignment with valid API base/key.
Why: world characters call the same Roleplay provider through direct_completion.
Required: only for free-text AI dialogue; map/choices/hints work without it.
Destination: CMS model registry / existing Roleplay model assignment. No new world key.
Need also strict moderation: configured JEV key via existing CMS Typesafe connection or JEV_API_KEY; alternatively existing WORLD_MODERATION_API_KEY / OPENAI_API_KEY with WORLD_MODERATION_API_BASE if appropriate.
Do not put private keys in frontend or Git.

## ACTION 3 — Voice

Need: CMS model whose purposes includes tts, valid provider credentials, compatible original-character voice selection.
Why: Listen calls the same configured speech provider.
Required: only for real voice tests.
Destination: existing CMS model/provider key and character voice configuration. There is no new TTS_API_KEY setting introduced by this demo.
Replay currently incurs another provider request; persistent audio cache is deferred.

## ACTION 4 — Characters and art

Need: at least two accessible existing characters, ideally four.
Why: academy scenes use existing IDs, not duplicate demo characters.
Required: yes for starting. Existing system presets can satisfy this.
Artwork: optional; see ASSET_REQUIREMENTS.md. No proprietary artwork is required.

## ACTION 5 — Production expansion

Need: separate decision and implementation for normalized persistence, publication/multiplayer permissions, wider localization and load tests.
Required: no for this personal demo. Current private prototype must not be described as the entire production specification.

## World CMS

/worlds/admin now controls only AI World. Choose explicit chat/TTS models there for separate assignments; otherwise existing assignments are inherited. Character/provider keys remain managed centrally. No automatic memory synchronization is enabled or implemented.
