# Official Moonfall media review — 2026-10-19

## Applied

- Runtime aliases now resolve the supplied backgrounds under
  `image/worlds/selene/moonfall/backgrounds/echoes_bg_16x9/`.
  Old CMS/run asset identifiers remain valid; their obsolete paths no longer
  block chapter preparation.
- Official cinematic bindings resolve
  `image/worlds/selene/moonfall/backgrounds/echoes_videos/videos/final/`.
- Converted `events/academy_collapse_selene.mp4` and
  `events/ev_ch1_arrow_trap_v6.mp4` to VP9 WebM beside their sources.
  Original uploads are retained for future editing; runtime uses WebM.
- Retired generic magic/transition/outro movies from the ordinary event mappings.
  Chapter completion no longer plays the hidden-ending movie.
  Rune/puzzle events keep their realtime effects.
- Chapter 7 retains its dedicated manifestation and memory-07 clips. They are
  different files with similar purple-fragment imagery. Neither is proof that
  a gameplay action succeeded; structured inspections and puzzle state decide.
- Chapter 4: aged intact corridor, click cracked ceiling, authored collapse
  cinematic, settled aftermath. The inspected ceiling persists across reload.
  Both corridor stages are one physical map.
- Chapter 5 security now uses its distinct security room painting.
- Chapter 7 final inspection uses pale-moon space rather than repeating the
  manifestation painting.
- The hidden final outcome has its own secret chamber background.
- Missing cinematic playback has a prepared fallback image; no old clean patch
  is painted over a different new background.
- Regular clue glimmers are brighter. Optional hidden-ending clues remain unmarked.

## Preparation and loading

The observed remote 409 responses came from two fixed chapter-1 speech clips
that were not prepared. The existing maintenance operation prepared missing
clips and reported all eight chapters ready in VI and EN.

The client now explains missing fixed audio separately from image/video/network
errors and rechecks the catalog. Entering a chapter does not generate TTS.
Modal startup can prepare missing fixed chapter speech after credentials load;
existing content-hash cache entries are reused.

The current chapter prepares its visual variants, cinematic fallbacks and fixed
audio. Previously decoded/downloaded media are reused across ordinary map changes.

## Asset availability

All supplied official backgrounds have manifest entries. Most are direct scene
backgrounds; trap-passage/collapsing-corridor are cinematic fallback images.
Between-memories is also available through the atlas-background alias.
This does not add an independent exploration quest for every supplied painting.

No missing chapter-7 clip was found for the existing authored route. A more
visually distinct new clip would be an artistic replacement, not a missing file
needed to unblock the current chapter.

No original video uploads were deleted in this pass. Retired clips are removed
from gameplay bindings; deletion of physical sources needs a separate reference
audit including CMS and saved configurations.

## Verification

- Browser: World entry and gate-then-key sequence pass against official BGs,
  with mocked ready speech (not a live provider audio-quality test).
- Node: 9 preparation/glimmer tests pass.
- Strict UI translation/build check: 727 strings across six translated locales
  plus Vietnamese source; TypeScript and Vite build pass.
- Backend coverage includes all eight chapter manifests, persistent corridor
  change, no retired chapter-7 interstitial, item order, exploration, and audio
  startup preparation. See test run output for counts.
