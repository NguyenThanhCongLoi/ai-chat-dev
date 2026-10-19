# AI World — research, 16 October 2026

## Inspection

Existing stack: React 19 / TypeScript / Vite; FastAPI / SQLAlchemy / SQLite; bearer sessions; CharacterSpec and CMS model assignments; provider TTS; Modal web packaging. Ordinary roleplay remains the character source. Existing Worlds stored private journeys in AppSetting JSON with revision guards. The old quest demo is retired from the default UI, not deleted from user storage.

## Primary sources and decisions

| Reference | License | Lesson / reuse | Maintenance risk |
|---|---|---|---|
| [AI Town](https://github.com/a16z-infra/ai-town), [architecture](https://github.com/a16z-infra/ai-town/blob/main/ARCHITECTURE.md) | MIT | Learn input → evaluator → persistent state separation. No code copied; no Convex or simulation loop dependency. | External engine would impose a different stack. |
| [Generative Agents paper](https://arxiv.org/abs/2304.03442) | Research reference; no software imported | Separate observations, retrieval and reflection. MVP uses bounded witnessed memories; continuous planning/reflection deferred for cost. | Model cost and unreliable generated conclusions. |
| [SillyTavern](https://github.com/SillyTavern/SillyTavern), [groups](https://docs.sillytavern.app/usage/core-concepts/groupchats/), [lore](https://docs.sillytavern.app/usage/core-concepts/worldinfo/) | AGPL-3.0 | Learn selective speaker activation and context budgets. No code or dependency imported. | Copying code would introduce licensing obligations; avoid. |
| [Chronicler](https://github.com/yantrikos/chronicler), [license](https://github.com/yantrikos/chronicler/blob/main/LICENSE) | MIT | Learn retrieval-time visibility and canon distinction. No code copied. This is yantrikos/chronicler, not similarly named tabletop projects. | Young project; do not depend on its formats. |
| [Ren'Py](https://github.com/renpy/renpy) | Engine MIT, bundled components have separate licenses | Learn scene composition, choices and save continuity; no runtime/assets copied. | Desktop engine would be an unnecessary web integration. |

No new third-party dependency is introduced. CSS/SVG supply original demo artwork and animation; React state drives transitions. Motion is optional in the prompt, unnecessary for this slice. All character art remains existing authorized assets. License review here records upstream labels, not legal certification.

## Product decision

One authored Magic Academy, personal persistent instances, four existing characters, five places. Opening the instance evaluates bounded activity; no LLM calls while absent. Deterministic choices change relationships, unlocks and missions. Chat enriches the scene but cannot mint rewards. Secrets are filtered before model context. Public publishing, real multiplayer, custom world themes and continuous autonomy are deferred rather than represented by nonfunctional controls.
