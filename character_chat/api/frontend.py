"""api.frontend: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_admin_app(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/admin", include_in_schema=False)
    def admin_app(_: None = runtime.Depends(runtime.docs_auth)):
        path = runtime.os.path.join(
            runtime.os.getenv("FRONTEND_DIST", "frontend/dist"), "admin.html"
        )
        if not runtime.os.path.isfile(path):
            raise runtime.HTTPException(503, "Admin frontend chưa được build")
        return runtime.FileResponse(path, headers={"Cache-Control": "no-store"})

    runtime.admin_app = admin_app

    @runtime.app.get("/avibi-platform", include_in_schema=False)
    @runtime.app.get("/avibi-platform/", include_in_schema=False)
    def platform_app():
        path = runtime.os.path.join(
            runtime.os.getenv("FRONTEND_DIST", "frontend/dist"), "index.html"
        )
        if not runtime.os.path.isfile(path):
            raise runtime.HTTPException(503, "Frontend has not been built")
        return runtime.FileResponse(path, headers={"Cache-Control": "no-store"})

    runtime.platform_app = platform_app

    @runtime.app.get("/role-play-ai", include_in_schema=False)
    @runtime.app.get("/role-play-ai/", include_in_schema=False)
    def role_play_app(request: runtime.Request):
        if request.query_params.get("workspace") != "1":
            return runtime.RedirectResponse("/avibi-platform", status_code=302)
        path = runtime.os.path.join(
            runtime.os.getenv("FRONTEND_DIST", "frontend/dist"), "index.html"
        )
        if not runtime.os.path.isfile(path):
            raise runtime.HTTPException(503, "Frontend has not been built")
        return runtime.FileResponse(path, headers={"Cache-Control": "no-store"})

    runtime.role_play_app = role_play_app

    @runtime.app.get("/ai-assistant", include_in_schema=False)
    @runtime.app.get("/ai-assistant/", include_in_schema=False)
    def ai_assistant_app(request: runtime.Request):
        if request.query_params.get("workspace") != "1":
            return runtime.RedirectResponse("/avibi-platform", status_code=302)
        path = runtime.os.path.join(
            runtime.os.getenv("FRONTEND_DIST", "frontend/dist"), "index.html"
        )
        if not runtime.os.path.isfile(path):
            raise runtime.HTTPException(503, "Frontend has not been built")
        return runtime.FileResponse(path, headers={"Cache-Control": "no-store"})

    runtime.ai_assistant_app = ai_assistant_app
