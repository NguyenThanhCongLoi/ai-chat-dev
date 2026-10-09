# Independent suggestion events

## Protocol

Both streaming chat endpoints now generate answers and suggestions concurrently.

Assistant emits:
- delta: incremental answer content.
- answer_done: persisted answer payload with its stable id; answering is finished.
- suggestions: message_id and three normalized suggestions; can arrive before or after answer_done.
- done: stream finished after suggestion persistence.

Role Play keeps character_message as the persisted final answer per character.
- suggestions carries message_id, character_id, suggestions.
- answer_done signals all selected characters finished answering.
- done closes the turn after suggestion logs are saved.
- Suggestions for one character do not delay the next selected character's answer.

An early suggestions event reserves a reply ID. The client caches the options and attaches them when the answer with that ID arrives. An answer that fails or becomes partial may discard these options.

## Deadline

SUGGESTION_BUDGET_SECONDS defaults to 12 seconds, bounded to 1–90 seconds.
It bounds the suggestion model chain independently of the answer duration; it is not an additional grace period after the answer.

To configure on Modal, add "SUGGESTION_BUDGET_SECONDS":"12" to the env dictionary of web() in modal_app.py and deploy.
Local execution can set the environment variable before starting the server.

Per-model HTTP connect/read timeouts remain active. Network/model errors or deadline exhaustion can still use local fallback. Canceling a running thread is not guaranteed to cancel gateway billing.

## UI and logs

After answer_done, the send button is enabled. Old streams continue receiving suggestions for their own message IDs even after a new turn starts in the same chat.
Switching chats/workspaces or unmounting aborts all tracked streams.
Late old-stream events cannot overwrite a new answer or clear its busy state.

Client first-chunk timing is reported after answer persistence.
Suggestion receipt timing is captured when suggestions arrives, then reported at done after suggestion logs exist.
Role Play suggestion runtime is captured inside the model task; it no longer includes waiting for the main answer.
Early options are persisted with the completed turn, and partial/error paths retain their existing behavior.

## Verification

98 tests passed across streaming events, parser, chat, gateway/fallback, archive, roleplay formatting and voice.
TypeScript and Vite production build passed.
Event tests use controlled fake upstreams: early/late suggestion ordering, answer persistence before slow suggestions, independent timeout and group chat progress.
No production deployment or live gateway benchmark was performed.
