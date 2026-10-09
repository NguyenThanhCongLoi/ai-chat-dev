# CMS character voice cloning

CMS → Nội dung → Nhân vật → Sửa → Clone giọng cho nhân vật.

Select WAV, MP3, FLAC, OGG or M4A up to 20 MB. Set a voice name, gender, sample language (Vietnamese/English), optional transcript and noise reduction. Submit Upload và gán giọng. An empty transcript is transcribed by the provider.

The backend POSTs multipart name/audio/gender/language/ref_text/enhance_audio/infer_ref_text_if_empty to the assigned TTS model API base + /api/v1/voices. Configure that TTS model base as https://innovations-cup-displayed-ata.trycloudflare.com/v1 to use the supplied service and retain its configured API key. Bearer credentials never go to the browser. No source sample was uploaded during development.

On success the voice ID is persisted in the character spec. Preset updates synchronize existing copies. Audio cache signatures include the voice ID, so future playback uses the newly assigned voice. Source samples and voice data live on the cloning provider; the platform retains the selected voice ID.

Reference: the supplied service openapi.json, Upload Voice endpoint. The upstream limits reference audio to under 10 seconds after preprocessing.

The CMS previews the original audio and the selected segment. Set start/end with numeric inputs or sliders (up to 10 seconds). The browser decodes the source, exports only that segment as mono PCM16 WAV and uploads voice-reference.wav. Closing the editor stops previews.

## Stored references by assignment
CMS displays the current reference file and audio preview when the assignment target is selected.
Shared, Vietnamese and English references are separate rows in character_voice_samples.
Only the trimmed file sent to Upload Voice is stored. New uploads replace only their target slot.
These CMS-only endpoints require authentication; reference audio uses private/no-store responses.
Changing target or character clears unsaved files and stops previews. Existing voices without
a stored reference retain their voice ID and require one new upload to display a saved file.
Manual voice-ID reassignment hides a reference that belongs to a different voice ID.

## Clone or API catalog
The CMS assignment selector (shared / vi / en) is followed by a voice source selector.
Clone shows reference upload, trimming, previews and cloning. API catalog hides cloning controls
and shows gender plus a voice select populated from the authenticated API catalog.
Options are filtered by gender and the selected assignment language. The current assignment
remains visible even when it is not in the filtered catalog; filtering never silently replaces it.
tts_voice_source, tts_voice_source_vi and tts_voice_source_en persist editor choices independently.
Legacy auto sources are inferred as clone when a stored reference is available.
Cloning saves its target source as clone. Catalog choices save the matching voice ID through
the normal Save character action. Choosing a source alone does not upload a voice or call TTS.
In the create form, clone upload is available after the character has been created.
