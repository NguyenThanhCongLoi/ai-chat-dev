# Module structure

This project keeps its public URLs and existing import paths while moving independent code into focused modules.

## Backend

- `character_chat/main.py` owns FastAPI startup, authentication dependencies, the existing chat and character endpoints, and router registration.
- `character_chat/admin_observability.py` owns the read-only CMS database, conversation, chat, voice, and action log routes.
- `character_chat/memory_routes.py` owns manual Role Play memory, relationship, and prompt trace routes.
- `character_chat/gateway.py` owns the LLM HTTP client, deadline, retries, fallback, and structured responses. `engine.py` still exports `LLM`, `TokenLimitError`, and `llm` for existing imports.
- `character_chat/models.py` defines SQLAlchemy tables. `db.py` owns the engine, sessions, and migrations, and re-exports model classes for existing imports.

For a new route, put request and response handling in the matching router and keep model calls or database operations in a service module when they are reused. Register new routers in `main.py`. Do not change existing URL paths when moving a route.

## Frontend

- `frontend/src/main.tsx` only selects the platform, Assistant, or Role Play entry.
- `frontend/src/roleplay/RolePlayApp.tsx` coordinates Role Play state. `api.ts`, `EmotionPortrait.tsx`, `CharacterCards.tsx`, and `types.ts` own independent behavior and display.
- `frontend/src/assistant/AssistantApp.tsx` coordinates Assistant state. `config.ts` holds modes and UI copy; `types.ts` holds its data types.
- `frontend/src/admin.ts` coordinates the CMS. `admin/logs.ts` owns log views and `admin/types.ts` holds CMS data types.

Before moving more stateful UI, preserve request cancellation, local storage keys, and event order. Keep each module move small enough to verify with the backend tests and `npm run build`.
