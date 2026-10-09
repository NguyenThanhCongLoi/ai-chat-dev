# Roleplay background voice

New streamed replies receive a durable message ID before the first text delta. For Vietnamese/English spoken content, completed sentences or clauses around 240 characters are queued for TTS while text generation continues. Action spans are excluded.

A separate bounded worker processes sentences in order through SSE PCM and stores each arriving PCM chunk on the server before the sentence finishes. Preparation never starts an audio player. Listen can replay existing parts and follow new parts while text is still streaming. The combined audio sends one final done event.

Completed audio is compacted into a WAV MessageSpeech cache. Future Listen requests reuse that cache. Configuration signatures reject audio from a previous voice or gateway. Interruption, regeneration and room deletion invalidate unfinished preparation. Greeting autoplay is unchanged. Regeneration currently returns complete text before voice preparation.

Limits: eight preparation workers per process, 4000 spoken characters, 12 MB PCM, 180-second preparation deadline. Busy/unconfigured TTS does not block text; existing whole-message preparation remains available. Each sentence makes a separate upstream TTS request and can have a prosody boundary. Temporary parts and completed WAV are durable database records accessible to other application workers.

Voice eligibility is based on spoken content, independently of UI locale. CMS supports separate Vietnamese/English voices and volume up to 200%.

Client preparation retains completed WAV/audio blobs and the incoming PCM sequence.
Listen subscribes to the existing preparation job, replays received chunks and follows new
chunks without a second generation request. Finished jobs replay locally without downloading
the same audio again. Local cache is limited to 64 MB / 32 completed jobs; account or voice
configuration changes clear it. The durable server WAV remains available after a page reload.
A failed/incomplete stream never becomes a completed cached clip. Gateway errors such as
"Missing request, possibly due to expiry or cancellation" still require provider-side request
logs for diagnosis; removing client waits does not repair an expired upstream request.

Runtime settings are selected by known setting keys in SQL, so voice/model selection
does not load unrelated translation or asset records. Speech cache signatures reuse
the TTS model, profile and credential already selected within the current request.
This avoids repeated configuration reads without caching CMS settings across requests.

Queued sentences in the same language are now combined up to 480 characters,
without adding a batching timer or waiting for more text. A carried language
change and the final queue sentinel retain their order. SSE PCM limits runs of
near-silent samples (absolute PCM16 amplitude <= 64) to 60 ms at the onset and
240 ms after speech. It does not wait for a complete clip or modify voiced
samples. This cannot remove gaps caused by waiting for upstream generation, or
repair pronunciation/prosody produced by the clone model itself. Updated cache
signatures prevent previous long-pause audio from being replayed as new audio.

Character-card navigation automatically reads the greeting in a room with no
user messages, including a reused room. In-room language changes reload the
localized greeting and clear the client audio cache. Short translated greetings
reuse their persisted translation language rather than relying only on text
heuristics. Existing conversations do not replay the greeting automatically.


## Automatic voice replies (2026-10-08)
New Roleplay replies now autoplay by default, including group replies queued in
order. The send interaction primes a PCM player. The first supported incremental
delta starts one prepared speech subscription per stable message ID; final-only
responses use the completion event. Final persistence does not enqueue an already
started reply again. Vietnamese/English eligibility, voice configuration, room
cancellation and CMS volume still apply. Existing history is not replayed.
Browser autoplay policies can still require an initial user interaction.
