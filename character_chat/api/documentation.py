"""api.documentation: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_docs_auth(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def docs_auth(
        credentials: runtime.HTTPBasicCredentials = runtime.Depends(
            runtime.docs_security
        ),
    ):
        expected_user = runtime.os.getenv("DOCS_USERNAME", "")
        expected_password = runtime.os.getenv("DOCS_PASSWORD", "")
        valid = (
            bool(expected_user and expected_password)
            and runtime.secrets.compare_digest(
                credentials.username.encode(), expected_user.encode()
            )
            and runtime.secrets.compare_digest(
                credentials.password.encode(), expected_password.encode()
            )
        )
        if not valid:
            raise runtime.HTTPException(
                status_code=runtime.status.HTTP_401_UNAUTHORIZED,
                detail="Sai tài khoản tài liệu API",
                headers={"WWW-Authenticate": "Basic"},
            )

    runtime.docs_auth = docs_auth

    @runtime.app.get("/docs", include_in_schema=False)
    def api_docs(_: None = runtime.Depends(runtime.docs_auth)):
        return runtime.HTMLResponse(
            """<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Avibi API Docs</title><style>*{box-sizing:border-box}body{margin:0;background:#f4f7f5;color:#17231e;font-family:Inter,Segoe UI,sans-serif}main{width:min(1050px,calc(100% - 32px));margin:70px auto}header{margin-bottom:34px}small{color:#13815d;font-weight:800;text-transform:uppercase;letter-spacing:.12em}h1{margin:10px 0;font-size:42px}p{color:#6e7d75}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}a{display:block;padding:24px;border:1px solid #dce6e1;border-radius:16px;background:white;color:inherit;text-decoration:none;box-shadow:0 8px 25px #173d2b0b}a:hover{border-color:#13815d;transform:translateY(-2px)}a b{display:block;margin-bottom:8px;font-size:19px}a span{color:#748179;font-size:13px;line-height:1.5}@media(max-width:700px){main{margin:35px auto}.grid{grid-template-columns:1fr}h1{font-size:32px}}</style></head><body><main><header><small>Avibi Platform</small><h1>Tài liệu API</h1><p>Chọn đúng miền sản phẩm để chỉ xem các endpoint liên quan.</p></header><section class="grid"><a href="/docs/assistant"><b>✦ AI Assistant API</b><span>Chat, streaming, upload file, model và gợi ý.</span></a><a href="/docs/role-play"><b>◉ AI Role Play API</b><span>Nhân vật, phòng chat, memory, tài liệu và cộng đồng.</span></a><a href="/docs/admin"><b>⚙ CMS API</b><span>Truy cập, model, prompt, nội dung, logchat và database.</span></a><a href="/docs/all"><b>▦ Toàn bộ API</b><span>Tất cả endpoint, được thu gọn theo nhóm nghiệp vụ.</span></a></section></main></body></html>""",
            headers={"Cache-Control": "no-store"},
        )

    runtime.api_docs = api_docs


def bind_section_docs(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/docs/{section}", include_in_schema=False)
    def section_docs(section: str, _: None = runtime.Depends(runtime.docs_auth)):
        config = runtime.DOC_SECTIONS.get(section)
        if not config:
            raise runtime.HTTPException(404, "API documentation section not found")
        return runtime.get_swagger_ui_html(
            openapi_url=f"/openapi/{section}.json",
            title=config["title"],
            swagger_ui_parameters={
                "docExpansion": "none",
                "filter": True,
                "displayRequestDuration": True,
                "persistAuthorization": True,
                "tagsSorter": "alpha",
            },
        )

    runtime.section_docs = section_docs

    def section_openapi(section):
        config = runtime.DOC_SECTIONS.get(section)
        if not config:
            raise runtime.HTTPException(404, "API documentation section not found")
        tags = config["tags"]
        routes = [
            route
            for route in runtime.app.routes
            if getattr(route, "include_in_schema", False)
            and (
                tags is None
                or any(tag in tags for tag in getattr(route, "tags", []) or [])
            )
        ]
        tag_metadata = [
            item
            for item in runtime.app.openapi_tags
            if tags is None or item["name"] in tags
        ]
        return runtime.get_openapi(
            title=config["title"],
            version=runtime.app.version,
            routes=routes,
            tags=tag_metadata,
        )

    runtime.section_openapi = section_openapi

    @runtime.app.get("/openapi/{section}.json", include_in_schema=False)
    def protected_section_openapi(
        section: str, _: None = runtime.Depends(runtime.docs_auth)
    ):
        return runtime.section_openapi(section)

    runtime.protected_section_openapi = protected_section_openapi

    @runtime.app.get("/openapi.json", include_in_schema=False)
    def protected_openapi(_: None = runtime.Depends(runtime.docs_auth)):
        return runtime.section_openapi("all")

    runtime.protected_openapi = protected_openapi


def bind_api_tag(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def api_tag(path):
        if path == "/health":
            return "System"
        if path.startswith(("/v1/auth/", "/v1/users/", "/v1/i18n/")):
            return "Identity & localization"
        if path.startswith("/v1/assistant/"):
            return "AI Assistant"
        if path.startswith("/v1/admin/access-control") or path.startswith(
            "/v1/admin/accounts"
        ):
            return "CMS — access"
        if path.startswith(
            (
                "/v1/admin/models",
                "/v1/admin/assistant-models",
                "/v1/admin/settings",
                "/v1/admin/credentials",
            )
        ):
            return "CMS — AI configuration"
        if path.startswith(
            (
                "/v1/admin/overview",
                "/v1/admin/database",
                "/v1/admin/conversations",
                "/v1/admin/chat-logs",
                "/v1/admin/action-logs",
            )
        ):
            return "CMS — observability"
        if path.startswith("/v1/admin/"):
            return "CMS — content"
        if (
            path.startswith(("/v1/documents", "/v1/character-sources"))
            or "/knowledge" in path
        ):
            return "Documents & knowledge"
        if path.startswith(
            ("/v1/memories", "/v1/daily-tasks", "/v1/debug/")
        ) or path.endswith(("/memories", "/relationship")):
            return "Memory & state"
        if path.startswith(("/v1/rooms", "/v1/roleplay/")):
            return "Role Play"
        if path.startswith(
            (
                "/v1/characters",
                "/v1/public",
                "/v1/presets",
                "/v1/home-sections",
                "/v1/system-characters",
            )
        ):
            return "Characters"
        return "System"

    runtime.api_tag = api_tag
