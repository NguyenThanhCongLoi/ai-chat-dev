# Roleplay voice languages and volume

CMS > Characters > Edit (or create): choose Shared clone for one ID across vi/en, or Separate voices with independent Vietnamese and English IDs. Empty IDs retain catalog/default fallback. Clone assignment target is independent of sample language. Default volume is 80%; volume changes never regenerate audio.

The existing response LLM is asked to prefix sentences or language changes with [[lang:xx]]. The server strips markers incrementally, stores language metadata, and sends speech_supported/speech_languages with deltas, completed replies and history. There is no extra LLM request. Plain-text replies use conservative local detection; script evidence overrides incorrect labels. Unknown content is not assumed to be English.

Voice and Listen depend on spoken content, independently of UI locale. Any unsupported segment hides Listen for the entire response and cancels remaining preparation. Earlier supported audio may already have been generated or played before a later unsupported segment arrives; those gateway charges cannot be undone.

Mixed vi/en sentences use their assigned voices in order. PCM is combined into a WAV cache on the server. Voice mode and both IDs participate in signatures; playback volume does not. Different PCM rates between voices produce an error rather than an invalid combined file.

Playback uses the character volume configured in CMS. Client chat has no custom volume slider and does not apply old per-user volume overrides. The CMS language selector displays only its corresponding voice slot, leaving missing slots empty. Sample language and assignment target are independent.

init_db adds messages.speech_segments without replacing history. Old messages use local detection. Metadata adds a few output tokens per sentence; TTS preparation remains independent of text generation. No live latency benchmark or production deployment has been performed.

CMS character voice volume ranges from 0% to 200% (stored as 0..2), default 80%.
Both streamed PCM and cached audio use the same Web Audio gain chain:
gain -> dynamics compressor -> bounded wave shaper -> output. Cached audio.volume remains 1.
Volume is applied at playback; it does not regenerate audio or change the server cache.
Background-music volume remains limited to 100%.
