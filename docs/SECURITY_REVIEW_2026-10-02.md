# Security review - 2026-10-02

## Scope and limits

Reviewed the current local authentication, CMS, character/catalog, expression cache, chat/voice ownership, upload/download, credentials, and browser session paths. Used synthetic users and an in-memory SQLite database; no production requests, credentials, or user content were used. No application code was changed. This is a source review, not a full penetration test or proof that production has been compromised. Deployed environment, proxy controls, Git history, dependencies and provider retention were not independently audited.

## Reproduced findings

### S1 - Critical if enabled: demo authentication trusts an arbitrary user ID

Location: character_chat/main.py:507-517; modal_app.py:233.

When DEMO_AUTH_ENABLED is missing, its default is true. A caller without a bearer token can supply X-Demo-User-Id for an existing user and obtain that identity. UUID secrecy is not authorization. This can expose that user's chat, files and voice through otherwise owner-protected endpoints.

Important: the current Modal web function explicitly sets DEMO_AUTH_ENABLED=false. This finding does not prove the deployed Modal app is vulnerable. Other deployments with the variable omitted are vulnerable.

Patch: default to false; remove demo identity impersonation in production and isolate demos. Require server-issued sessions. Explicitly configure false on every API deployment. Regression: missing/false setting plus forged header must return 401; a real user requesting another user's resource must return 404/403.

### S2 - High: private character avatars are anonymously downloadable

Location: character_chat/main.py:1861 (public_character_avatar), :1174 (character_out).

GET /v1/public/characters/{id}/avatar fetches CharacterAsset without checking publication or ownership. It also sets public, max-age=31536000, immutable. Knowing a private character ID is sufficient; an ID need not be guessable for the missing authorization to be a defect.

Patch: public route must verify a public publication or an explicitly public canonical preset. Introduce an owner-authenticated private image route with Cache-Control: private, no-store. Update frontend avatar fetching: an img src alone cannot attach a bearer header, so use authenticated blob fetch or same-origin authenticated cookies. Avoid breaking private images by changing only the server route. Use new URLs and invalidate controlled caches after changing visibility; already downloaded copies cannot be recalled.

### S3 - High: global expression cache leaks images across accounts

Locations: main.py:1094-1145, :1255, :1315-1353, :1518, :1828.

Expression identity is derived from character name/title without owner scope. register_expression_identity stores private images under a global __identity__ key. A different user creating a same-name character can receive an alias to those images. The final expression endpoint checks ownership of the new character, but not ownership/public status of the aliased source. Sibling matching by preset_type and generated-character name matching also need review during the fix.

Patch: scope private cache keys to owner + character/source image revision; share only explicit public/system assets. Validate authorization on every alias resolution, not just the requested character. Do not trust a user-supplied preset_type to grant shared-asset access. Migrate existing global aliases, preserve rightful owners' images, and rebuild ambiguous private mappings. Changing only future creation leaves old leaks intact.

### S4 - Medium, or High for confidential character cards: catalog exposes internal prompt fields

Locations: main.py:1273, :1846, :1867; schemas.py:45-80.

Public catalog uses the entire CharacterSpec.model_dump(), including system_prompt, persona_knowledge and behavior_rules. A normal registered user can inspect these in the browser network panel. This is not anonymous access when demo authentication is disabled. If full-card sharing is intended, disclose it clearly; otherwise publishing an avatar/card should not implicitly publish its internal prompt.

Patch: define an allowlisted public DTO (ID, name, description, avatar, social display fields). Keep hidden prompt/persona fields server-side. Apply the boundary to presets, clones and character listing, not only the catalog: clones currently copy the full spec. Full editing data should be limited to the original author/admin, with server-side template references for other users. Prompt instructions saying 'do not reveal' cannot protect data already sent by an API. Never put credentials in prompts.

## Other material risks and patch guidance

### S5 - Docs credentials also authorize CMS administration

Location: main.py:360; character_chat/admin_observability.py.

The same HTTP Basic docs_auth protects Swagger and administrative endpoints. Sharing docs credentials gives access to administrative logs/database/configuration, not merely documentation. These endpoints do have an authentication check; this is a privilege-separation problem, not a demonstrated anonymous bypass.

Patch: separate docs-reader and administrator permissions, enforce server-side roles on every admin route, use individual admin accounts with revocation/MFA where available. UI-only contributors should receive mock data and source access, not production CMS credentials.

### S6 - API-key encryption is coupled to the docs password

Location: main.py:156.

_vault_cipher prefers DOCS_PASSWORD over ADMIN_ENCRYPTION_KEY. A person obtaining both the encrypted database and docs password can derive the encryption key. Simply rotating the docs password can also break stored provider keys.

Patch: use a dedicated high-entropy encryption secret or managed KMS, independent of login credentials. Migrate by decrypting with the old key and re-encrypting with the new one, using backups and verification before removing the old secret. Merely setting ADMIN_ENCRYPTION_KEY is insufficient while DOCS_PASSWORD takes precedence. Protect backups with the same care as the live database.

### S7 - No application-level login/generation throttling found

Locations: main.py register_account/login_account/docs_auth and paid model endpoints.

No shared rate limiter was found in the reviewed application source. Deployment edge controls are unknown. Attackers may brute-force credentials or use ordinary registrations to consume chat/image/TTS credits without ever learning the API key.

Patch: add IP/account login limits, per-user generation concurrency and quotas, request size limits and a deployment-wide cost circuit breaker. Use a shared store across workers. Return 429 with Retry-After. Do not rely only on frontend button disabling.

### S8 - Raw upstream diagnostics reach users

Locations: main.py generate_character, stream_roleplay_answer, _prepare_message_speech; gateway.py error handling.

Raw exception strings and some provider response bodies are returned to clients. These can reveal gateway URLs/model names/internal diagnostics. This review did not establish a direct raw-key leak through errors.

Patch: return stable public error codes plus a request ID. Keep detailed exceptions in access-controlled server logs; redact Authorization, cookies, query credentials and token-like fields before storage. Apply this to JSON errors and SSE events. Limit log retention and administrative access because chat/voice logs contain user information.

### S9 - Browser session and cross-origin hardening

Locations: frontend/src/assistant/AssistantApp.tsx:15, frontend/src/roleplay/api.ts:7, main.py:357.

Bearer tokens are in localStorage. This makes a future same-origin XSS able to steal sessions; it is not proof that an XSS exists. Default CORS is '*'; CORS alone is not authorization and does not automatically bypass bearer checks.

Patch: consider HttpOnly + Secure + appropriate SameSite cookies with CSRF protection for state changes, or tightly constrain browser token exposure. Add a compatible CSP, nosniff and referrer policy; inventory scripts/iframes first. Allow only actual application origins. Do not break legitimate same-origin workspace framing by indiscriminately applying frame denial.

### S10 - Outbound URL fetching needs network-level protection

Locations: main.py:2354-2380, avatar_pipeline.py:74-81.

Document downloads validate public DNS addresses and redirects, which is useful. DNS validation and HTTP connection resolution are separate, leaving a potential DNS-rebinding gap. Provider-returned image URLs are fetched without equivalent public-target validation. Exploitation was not tested; the latter requires influence over provider output or a compromised provider.

Patch: block private/link-local/metadata targets at egress, validate each redirect and use a vetted resolver/connection strategy that preserves TLS verification. Apply the same constrained downloader to image responses, enforce content type and byte limits. Do not use naive IP URL substitution that disables TLS verification.

## Synthetic verification results

- Anonymous private avatar: HTTP 200; private marker bytes returned; public one-year cache.
- Missing demo flag: existing synthetic owner identity accepted without token.
- Demo flag false: HTTP 401.
- Direct cross-user character access using owned(): HTTP 404 (positive control).
- Different user's same-name character: expression endpoint returned original owner's private marker bytes.
- Public catalog: internal system_prompt marker present.

Only moderation was stubbed for the same-name creation test to avoid an external LLM call; permission, cache and route logic were unchanged. The avatar route was invoked through a minimal FastAPI TestClient; remaining checks invoked actual route/helper functions against RAM SQLite.

## Controls that already help

- CMS/model serialization does not return raw API keys; it exposes configured/hint fields.
- Admin database viewer masks password hashes, session token hashes and stored credential fields.
- credential_for_base matches normalized API bases and restricts the shared Avibi environment fallback to the Avibi base.
- Reviewed speech route checks both room and character ownership and sends private/no-store.
- Local character-image path resolution checks containment in the image directory.
- A limited credential-pattern scan of 65 tracked current files found no matches or tracked .env/private-key/database files. This is not a comprehensive secret scan: untracked files, historical commits, arbitrary token formats, deployed bundles and runtime logs remain outside that result.

## Recommended rollout order

1. Verify production demo auth is false; change its code default to false.
2. Fix private-avatar authorization and cross-owner expression aliases together with frontend compatibility and existing-data migration.
3. Restrict public DTOs, including clones and presets.
4. Separate docs/admin roles; migrate encryption keys safely.
5. Add error redaction, request limits, log retention and outbound network controls.
6. Run authorization regression tests for anonymous/user A/user B/admin across chat, voice, images, files, memory and streams. Check both existing and newly created records, and public-to-private changes.
7. Scan Git history and built assets with an approved secret scanner before sharing or publishing. If an actual credential leak is found, revoke/rotate the credential; deleting a file alone is insufficient.

## References

- OWASP Authorization Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- OWASP SSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- OWASP HTML5 Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html
