# Character reaction sounds

## Behavior
Reaction audio is separate from spoken-message audio and the shared music playlist.
It defaults on per character, with a saved mute toggle below Character information.
Each reply may emit one early reaction SSE event once its text shows a non-neutral
expression. Final character_message supplies a fallback reaction. Message IDs
deduplicate these events; a four-second cooldown prevents overlapping reactions
in group chats. Existing history is not replayed as reactions. Opening a room with its initial greeting plays one quiet neutral clip before the greeting voice. Muted/missing clips are skipped. Opening clips use already-prepared media, with no additional preload wait; the opening clip is capped at 850 ms. Greeting audio preparation runs concurrently.

Recent character clips prewarm on the catalog page. Opening chat loads its messages and prepares reaction media in parallel, then enters the room only after configured clips are ready. Text and voice generation do not
wait for them or call Chatterbox. A character without configured clips opens normally. A preparation failure remains on the prior page with the normal error; retrying the room entry retries preparation. A browser that blocks autoplay may prevent a reaction until playback is
allowed. Hidden tabs and leaving chat stop reactions.

## Storage and voice identity
character_reaction_assets stores 12 PCM16 WAV clips per voice assignment:
two variants for neutral, happy, sad, angry, surprised and shy.
Shared, Vietnamese and English assignments have separate sets.
System-character copies inherit the corresponding preset clips.
Public-character clones can reuse their source clips only while their assigned
voice and reference fingerprint match. CMS creation/replacement is atomic.
Audio access checks character ownership and the current reference fingerprint.
Voice changes make old clips unavailable; response events also carry the current
voice ID to prevent a client from playing a buffered clip for a previous voice.
Explicit regeneration deletes the previous set after all new clips validate.

A clip must be 0.15-4 seconds and at most 2 MB. The worker trims silence, normalizes
peaks with bounded gain and rejects silence/overlong clips rather than saving them.
Individual emotion tags can vary in quality; listen in CMS before rollout.

## CMS
Characters > Edit > Âm phản ứng nhân vật:
- Select shared/VI/EN reference assignment.
- Generate or regenerate the set; preview each clip.
- Save reaction volume (0-100%) independently of voice/music.
- Delete the assignment's set.
- Backfill missing sets for all system characters with current clone references.
  Missing references are reported, never replaced by another character's voice.

Saving a new clone queues generation automatically. A failed reaction job does
not prevent saving the cloned voice. Retry from the CMS once the worker is ready.
Duplicate jobs for the same reference within 20 minutes are suppressed.
A job that exceeds this window is shown as failed so it can be retried.

## Deployment and disk locations
No Chatterbox/Torch/model dependencies are installed into the local Python or the
main chat API image. The dedicated modal_reactions.py worker installs them on a
remote Modal L4 GPU, keeps model weights in character-reactions-models, and runs
only to generate sets. This consumes GPU time when generating sets, not when users
chat. The worker has one container and releases it after 60 idle seconds.

From PowerShell in D:\ai_chat_char:
    .\scripts\deploy_reactions.ps1

The script places local temporary and download caches under
D:\ai_chat_char\.reaction-cache. It does not install packages on C.
Use the existing Modal account/login. If the model repository requires a
Hugging Face token, create a Modal secret and set REACTION_HF_SECRET to that secret
name before deploying; do not put tokens in source files.

Deploy the main chat app after the worker, then use the CMS backfill action for
existing system characters. Models/clip generation has not been run by the
implementation tests; those tests use synthetic WAV output. Listen to a real
generated set before enabling it broadly.

## Upstream reference
Chatterbox source and generation API:
https://github.com/resemble-ai/chatterbox
The reference must be longer than five seconds; around ten seconds is recommended.
The model/version used by the worker is chatterbox-tts 0.1.7.

## First setup
1. Deploy the reaction worker with scripts/deploy_reactions.ps1 from D:\ai_chat_char.
2. Deploy the main chat app normally.
3. In CMS > Characters > Edit, select Clone voice and upload a reference longer
   than five seconds (around ten seconds recommended) for shared/VI/EN assignment.
4. In Âm phản ứng nhân vật, select the same assignment. Wait for Ready or click
   Tạo / tạo lại âm phản ứng. Preview the neutral variants and set volume.
5. For existing system voices, use Tạo bộ clip còn thiếu cho nhân vật hệ thống.
6. Open a character room without user messages. If initial greeting autoplay is
   enabled by the existing room-entry flow, a neutral reaction plays first, then
   the greeting voice. Rooms with existing user messages do not replay greetings.

## Dedicated reference and repetition
CMS offers a separate reaction reference upload for each shared/VI/EN slot.
Upload and save the reference, then generate clips. This does not clone/reassign
the speech voice or replace CharacterVoiceSample. If no dedicated reference exists,
the generator uses the matching saved speech-clone sample. Removing a dedicated
reference restores that fallback. The sample must match the currently assigned
voice; changing that voice invalidates its reference and generated clips.

The checkbox "Cho phép lặp mẫu ngắn 2–3 lần" applies to manual generation and
system backfill. In the worker, short audio is decoded and repeated two or three
times with 20 ms crossfades, until it is longer than five seconds. Original server
files are never changed. Samples of roughly two seconds or longer work with this
limit; shorter samples can still be rejected. Repetition meets the duration
requirement but does not add voice information; longer natural samples are preferred.

Both the main app and modal_reactions.py worker must be redeployed for this option.

## Delete and fill missing clips
Each preview has a delete button. Deletion invalidates the active generation token
so an old job cannot restore it. Delete-set remains available for the selected slot.
CMS reports available and missing counts out of twelve. "Tạo bù clip còn thiếu"
requests only missing emotion/variant pairs from the worker and preserves IDs and
audio of existing clips. System backfill uses the same behavior. A complete set
does not invoke the worker. "Tạo / tạo lại" explicitly replaces the whole set.
Redeploy both the worker and app for the new selective generation argument.

## Prepared playback cache
Reaction files are fetched and media players reach canplay before room entry.
Existing clips reuse the same prepared audio elements on later visits, with playback
rewound to zero each time. Room entry refreshes metadata so deleted/replaced clips
are removed and volume changes applied. The cache is bounded to sixteen characters
per account and clears when the account changes or logs out. Leaving a room stops
its reactions without discarding prepared media. This does not generate new audio.

## Download cancellation handling
Preparation uses four parallel file/media slots per character. Each HTTP request,
including reading its response body, has a 25-second limit; there is no shared
15-second deadline for the whole set. Media readiness has its own eight-second
limit. Session changes cancel pending requests and media waits without displaying
an error. Real download timeouts remain visible with a retry message.
