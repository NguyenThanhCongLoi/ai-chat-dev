# Role Play background music

- Source audio lives in music_backgr/mp3 (currently 28 tracks, about 160 MB).
- Modal packages that directory separately from the frontend. The music is served as range-capable audio, not included in JavaScript.
- The hero has a music toggle. Music is enabled by default (unless the browser remembers an explicit off preference). The same player continues from home/catalog into chat. It stops on creation pages. If autoplay is blocked, the first user interaction retries playback.
- Playback uses a shuffled queue, plays every track once per cycle, reshuffles when exhausted and avoids immediately repeating the last song across cycles.
- The home enabled preference is local to the browser. Chat has a mute/unmute button below Character information in the right panel. Muting affects only the current chat visit; entering another chat enables music again without changing the saved home preference. Music pauses when leaving the visible Role Play frame or hiding the tab, and becomes quieter during character speech.
- CMS → Nhạc nền lists all 28 bundled tracks and uploaded tracks. Set volume (default 30%), select playable tracks, listen to previews, and save. One selected track loops; multiple tracks shuffle. Empty selection disables music.
- Upload MP3/OGG/WAV/M4A up to 20 MB each through CMS. Uploads and settings persist in the application database on the deployed volume and survive redeployment. Bundled MP3s remain packaged separately. Changes apply on reloading Role Play; no gateway calls.
- Add more MP3 files to music_backgr/mp3 and redeploy, or upload from CMS without redeploying.
- The supplied AlkaKrab license permits app use and does not require attribution. It restricts redistribution of the original tracks and open-source inclusion without permission. The MP3 directory is ignored by Git while remaining included in the Modal image.

- CMS also deletes tracks: uploaded audio is removed from the database; bundled audio is permanently excluded by saved server settings. Deleted tracks leave the playlist and are not restored by redeployment.

- CMS offers optional trimming and preview before uploading. Source files larger
  than 20 MB may be cut locally; the uploaded output must fit 20 MB.
- Per-character music settings, uploads, playback endpoints and client caches
  have been removed. Chats use the shared CMS playlist and its volume.
  Previously stored character audio is not erased by this code cleanup.
- Opening chat loads its messages without a separate music settings request or
  a music readiness gate. The shared audio element uses automatic preloading;
  moving between home and chat preserves its current track and buffered audio.
