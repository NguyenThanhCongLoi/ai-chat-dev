"""services.audit: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind__audit_category(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def _audit_category(path: str):
        if path.startswith("/v1/auth/"):
            return "auth"
        if path.startswith("/v1/assistant/"):
            return "assistant"
        if path.startswith(
            (
                "/v1/rooms",
                "/v1/characters",
                "/v1/public",
                "/v1/memories",
                "/v1/daily-tasks",
            )
        ):
            return "roleplay"
        if path.startswith(("/v1/documents", "/v1/character-sources")):
            return "document"
        if path in ("/", "/avibi-platform", "/ai-assistant", "/role-play-ai"):
            return "navigation"
        return "api"

    runtime._audit_category = _audit_category

    def _audit_action(method: str, path: str):
        if path == "/":
            return "open_platform"
        if path == "/ai-assistant":
            return "open_assistant"
        if path == "/role-play-ai":
            return "open_roleplay"
        tail = path.removeprefix("/v1/").strip("/").replace("/", ".") or "request"
        return f"{method.lower()}.{tail}"[:180]

    runtime._audit_action = _audit_action

    def _audit_identity(db, request: runtime.Request):
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(None, 1)[1].strip()
            token_hash = runtime.hashlib.sha256(token.encode()).hexdigest()
            session = db.get(runtime.UserSession, token_hash)
            if session:
                account = db.get(runtime.UserAccount, session.user_id)
                return (
                    session.user_id,
                    (account.username if account else ""),
                    token_hash[:16],
                )
        demo = request.headers.get("x-demo-user-id", "")
        return (demo or None), ("demo" if demo else ""), ""

    runtime._audit_identity = _audit_identity

    def write_audit_event(
        *,
        request: runtime.Request | None = None,
        user_id: str | None = None,
        username: str = "",
        category: str = "api",
        action: str = "request",
        status_code: int = 200,
        latency_ms: int = 0,
        error: str = "",
        details: dict | None = None,
    ):
        """Best-effort audit logging; logging failure must never break the product request."""
        try:
            with runtime.Session() as audit_db:
                session_hash = ""
                if request:
                    detected_user, detected_name, session_hash = (
                        runtime._audit_identity(audit_db, request)
                    )
                    user_id = user_id or detected_user
                    username = username or detected_name
                event_details = {
                    "request_id": (
                        getattr(request.state, "request_id", "") if request else ""
                    ),
                    **(details or {}),
                }
                audit_status = (
                    "partial"
                    if status_code == 206
                    else ("success" if status_code < 400 else "error")
                )
                audit_db.add(
                    runtime.AuditEvent(
                        id=runtime.uid(),
                        user_id=user_id,
                        username=username[:80],
                        session_hash=session_hash,
                        category=category[:40],
                        action=action[:180],
                        method=(request.method if request else "")[:12],
                        path=(request.url.path if request else "")[:500],
                        status=audit_status,
                        status_code=status_code,
                        latency_ms=max(0, int(latency_ms)),
                        ip_address=(
                            request.client.host if request and request.client else ""
                        )[:80],
                        user_agent=(
                            request.headers.get("user-agent", "") if request else ""
                        )[:500],
                        error=str(error)[:2000],
                        details=runtime.json.dumps(event_details, ensure_ascii=False)[
                            :4000
                        ],
                    )
                )
                audit_db.commit()
        except Exception:
            runtime.logging.getLogger("character_chat.audit").error(
                "Failed to persist an audit event"
            )

    runtime.write_audit_event = write_audit_event

    @runtime.app.middleware("http")
    async def disable_stale_frontend_cache(request, call_next):
        request.state.received_at = runtime.time.monotonic()
        started = runtime.time.perf_counter()
        response = None
        failure = ""
        supplied = request.headers.get("x-request-id", "")
        request.state.request_id = (
            supplied[:80]
            if runtime.re.fullmatch(r"[\w.-]{1,80}", supplied)
            else runtime.secrets.token_hex(12)
        )
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.state.request_id
            return response
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            path = request.url.path
            is_stream = path.endswith("/messages/stream")
            is_media_read = request.method in ("GET", "HEAD") and bool(
                runtime.re.fullmatch(
                    r"/v1/roleplay/(?:background-music|action-sounds)/[^/]+", path
                )
                or runtime.re.fullmatch(
                    r"/v1/characters/[^/]+/reactions/[^/]+/audio", path
                )
            )
            should_audit = (
                not is_media_read
                and (not is_stream or response is None or response.status_code >= 400)
                and (
                    path in ("/", "/avibi-platform", "/ai-assistant", "/role-play-ai")
                    or path.startswith("/v1/")
                )
                and not path.startswith(("/v1/admin/", "/v1/i18n/"))
                and path not in ("/v1/auth/login", "/v1/auth/logout")
            )
            if should_audit:
                status_code = response.status_code if response is not None else 500
                audit_kwargs = dict(
                    request=request,
                    category=runtime._audit_category(path),
                    action=runtime._audit_action(request.method, path),
                    status_code=status_code,
                    latency_ms=round((runtime.time.perf_counter() - started) * 1000),
                    error=failure
                    or (f"HTTP {status_code}" if status_code >= 400 else ""),
                )
                if response is None:
                    await runtime.asyncio.to_thread(
                        runtime.write_audit_event, **audit_kwargs
                    )
                else:
                    # Persist after sending the body; SQLite writes must not delay startup.
                    from starlette.background import BackgroundTasks as ResponseTasks

                    previous = response.background
                    tasks = ResponseTasks()
                    if previous is not None:
                        tasks.add_task(previous)
                    tasks.add_task(runtime.write_audit_event, **audit_kwargs)
                    response.background = tasks
            if response is not None and path.startswith("/assets/"):
                # Vite fingerprints JS/CSS/fonts. Deployments generate new URLs.
                fingerprinted = bool(
                    runtime.re.search(r"-[A-Za-z0-9_-]{8}\.(?:js|css)$", path)
                )
                response.headers["Cache-Control"] = (
                    "public, max-age=31536000, immutable"
                    if fingerprinted
                    else "public, max-age=0, must-revalidate"
                )
            elif response is not None and path == "/":
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

    runtime.disable_stale_frontend_cache = disable_stale_frontend_cache
