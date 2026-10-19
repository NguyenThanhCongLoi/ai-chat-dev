# Asset mapping — Echoes of Moonfall

Runtime authority: character_chat/story_data/echoes_of_moonfall.json or the versioned CMS configuration.

Originals remain unchanged. Optimized WebP/WebM derivatives are served by manifest ID, never raw paths in scene components.

| ID | File relative to image/worlds/selene/moonfall | Status |
| --- | --- | --- |
| moonfall_overview | backgrounds/moonfall_overview.webp | Present |
| moonfall_outer_ruins | backgrounds/moonfall_outer_ruins.webp | Present |
| ancient_gate | backgrounds/ancient_gate.webp | Present |
| inner_ruins | backgrounds/inner_ruins.webp | Present |
| ancient_archive | backgrounds/ancient_archive.webp | Present |
| moonfall_past | backgrounds/moonfall_past.webp | Present |
| blackwood_forest | backgrounds/blackwood_forest.webp | Present |
| witch_area | backgrounds/witch_area_witch_house.webp | Present |
| underground_chamber | backgrounds/underground_chamber.webp | Present |
| deep_vault | backgrounds/deep_vault.webp | Present |
| moon_temple | backgrounds/moon_temple.webp | Present |
| memory_space | backgrounds/memory_space.webp | Present |
| silver_pendant | props/silver_pendant.webp | Present |
| ancient_journal | props/ancient_journal.webp | Present |
| moon_rune | props/moon_rune.webp | Present |
| broken_tablet | props/broken_tablet.webp | Present |
| crystal_fragment | props/crystal_fragment.webp | Present |
| seal_stone | props/seal_stone.webp | Present |
| ancient_key | props/ancient_key.webp | Present |
| elarion_letter | props/elarion_letter.webp | Present |
| witch_symbol | props/witch_symbol.webp | Present |
| moonstone | props/moonstone.webp | Present |
| moonfall_intro | video/intro/moonfall_intro.webm | Present |
| ambient_ruins_wind | audio/ambient/ruins_wind.ogg | Optional audio missing |
| ambient_underground_hum | audio/ambient/underground_hum.ogg | Optional audio missing |
| ambient_forest_night | audio/ambient/forest_night.ogg | Optional audio missing |
| ambient_archive_room | audio/ambient/archive_room.ogg | Optional audio missing |
| ambient_memory_space | audio/ambient/memory_space.ogg | Optional audio missing |
| ambient_moon_temple | audio/ambient/moon_temple.ogg | Optional audio missing |
| sfx_rune_activate | audio/sfx/rune_activate.ogg | Optional audio missing |
| sfx_magic_pulse | audio/sfx/magic_pulse.ogg | Optional audio missing |
| sfx_stone_move | audio/sfx/stone_move.ogg | Optional audio missing |
| sfx_stone_door | audio/sfx/stone_door.ogg | Optional audio missing |
| sfx_clue_found | audio/sfx/clue_found.ogg | Optional audio missing |
| sfx_memory_trigger | audio/sfx/memory_trigger.ogg | Optional audio missing |
| sfx_memory_reveal | audio/sfx/memory_reveal.ogg | Optional audio missing |
| sfx_secret_reveal | audio/sfx/secret_reveal.ogg | Optional audio missing |
| sfx_location_unlock | audio/sfx/location_unlock.ogg | Optional audio missing |
| sfx_chapter_complete | audio/sfx/chapter_complete.ogg | Optional audio missing |
| sfx_seal_break | audio/sfx/seal_break.ogg | Optional audio missing |
| map_world_select | backgrounds/map_background_world_select.webp | Present |
| chapter_complete_background | backgrounds/chapter_complete_background.webp | Present |
| enter_ruins_video | video/locations/enter_ruins.webm | Present |
| memory_space_video | video/memories/memory_space.webm | Present |
| memory_transition | video/memories/memory_transition.webm | Present |
| memory_exit | video/memories/memory_exit.webm | Present |
| chapter_complete_video | video/reveals/chapter_complete.webm | Present |
| seal_activation | video/reveals/seal_activation.webm | Present |
| deep_vault_awaken | video/reveals/deep_vault_awaken.webm | Present |
| selene_happy | characters/selene_happy.webp | Present |
| selene_sad | characters/selene_sad.webp | Present |
| selene_angry | characters/selene_angry.webp | Present |
| selene_surprised | characters/selene_surprised.webp | Present |
| selene_laughing | characters/selene_laughing.webp | Present |
| selene_crying | characters/selene_crying.webp | Present |
| selene_winking | characters/selene_winking.webp | Present |
| selene_playful | characters/selene_playful.webp | Present |
| selene_thinking | characters/selene_thinking.webp | Present |

## Cinematic bindings

| Story / presentation event | Asset | Chapter 1 use |
| --- | --- | --- |
| WORLD_INTRO | moonfall_intro | Opening, once per saved run |
| LOCATION_ENTER: outer_ruins | enter_ruins_video | Entering ruins; other locations do not reuse it |
| CHAPTER_COMPLETE | chapter_complete_video | One clip despite multiple typed completion events |
| Memory reveal dialog | memory_space_video | Optional looping backdrop; close/skip independent of saved state |
| MEMORY_RECONSTRUCTION_START | memory_transition | Registered for future chapters, not triggered in Chapter 1 |
| MEMORY_RECONSTRUCTION_END | memory_exit | Registered only |
| MAGIC_SEAL_ACTIVATE | seal_activation | Registered only |
| MAJOR_REVEAL / VAULT_AWAKEN | deep_vault_awaken | Registered only |

Only the next likely scene clip preloads metadata. Intro completion is a stored UI acknowledgment, not a video-ended callback. Location/clue/completion state already exists before cinematic playback.

## Conversions

Run python scripts/prepare_world_images.py for new PNG/JPEG background derivatives. For white-background props add --remove-white-props. Originals are read-only; --overwrite replaces generated WebP derivatives only.

Run python scripts/prepare_world_videos.py (FFmpeg on PATH or --ffmpeg, or the project-local .tools/media-python installation). Produces silent VP9, up to 1280×720 at 24 fps, CRF 36, and validates decoding. Original MP4s are preserved.

14 backgrounds: 110,136,363 → 2,451,380 bytes. Eight videos: 23,005,115 → 8,574,555 bytes. WebM is not inherently smaller; these savings come from the selected codec, quality, dimensions and frame rate.

Nine transparent expression derivatives reuse the supplied elf sheet via imagegen background removal and grid crops; the original image/react/elf.webp and ordinary Chat portrait pipeline are untouched. Neutral maps to happy; shy to winking; missing cutout falls back to existing expression loading.

World media is public presentation content. Never put credentials, private user uploads or hidden story scripts in these directories.
