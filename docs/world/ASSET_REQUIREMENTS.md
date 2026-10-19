# Asset requirements

## REQUIRED NOW

None. Original SVG scenery, CSS effects, existing character avatar URLs and initial-letter fallbacks make the demo immediately usable. No generated-image/GPU pipeline.

## OPTIONAL POLISH

| Exact file | Purpose | Specification | Destination |
|---|---|---|---|
| moonfall-academy.webp | Optional replacement scene artwork | 1920×1080, WebP, opaque, preferred <500KB | frontend/public/world/moonfall-academy.webp |
| library.ogg | Optional library ambience | 30–60sec, OGG, seamless loop, normalized quiet, <1MB | frontend/public/world/ambience/library.ogg |
| garden.ogg | Optional garden ambience | 30–60sec, OGG, seamless loop, <1MB | frontend/public/world/ambience/garden.ogg |
| portrait via character CMS | Existing portrait improvement | 1024×1536 transparent WebP/PNG, preferred <400KB | Upload through existing character CMS |

These optional files are not currently loaded automatically. World already plays the existing ordinary-chat CMS playlist. Per-location ambience selection still awaits a later implementation; optional files above are not loaded automatically.

## FUTURE

Expression/idle videos are outside current scope (user excluded new GPU/video work). If later approved: per-character idle.webm and idle.mp4, 3–5sec seamless, 1080×1350, static camera, preferably <2MB, no audio, in an agreed media store. Scene uses IDs and portrait presentation so it can later accept a media adapter.
