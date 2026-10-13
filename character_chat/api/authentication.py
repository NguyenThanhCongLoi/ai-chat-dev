"""api.authentication: domain-specific application implementation.

Account HTTP endpoints; password/session rules are supplied by the authentication service.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_register_account(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/auth/register")
    def register_account(
        data: dict, db: runtime.DBSession = runtime.Depends(runtime.db_session)
    ):
        control = runtime.access_control(db)
        if control["maintenance_mode"]:
            raise runtime.HTTPException(
                503, "Hệ thống đang bảo trì, đăng ký mới đang tạm đóng"
            )
        if not control["registration_enabled"]:
            raise runtime.HTTPException(403, "Đăng ký tài khoản mới đang tạm đóng")
        username = str(data.get("username") or "").strip().lower()
        password = str(data.get("password") or "")
        display_name = str(data.get("display_name") or username).strip()
        if not runtime.re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
            raise runtime.HTTPException(
                400,
                "Tên đăng nhập cần 3–32 ký tự: chữ thường, số, dấu chấm, gạch ngang hoặc gạch dưới",
            )
        if len(password) < 6:
            raise runtime.HTTPException(400, "Mật khẩu cần ít nhất 6 ký tự")
        if db.query(runtime.UserAccount).filter_by(username=username).first():
            raise runtime.HTTPException(409, "Tên đăng nhập đã tồn tại")
        user_id = runtime.uid()
        db.add(runtime.User(id=user_id))
        db.add(
            runtime.UserAccount(
                user_id=user_id,
                username=username,
                display_name=(display_name or username)[:80],
                password_hash=runtime._password_hash(password),
            )
        )
        db.commit()
        return runtime.account_out(db, user_id, runtime._new_session(db, user_id))

    runtime.register_account = register_account

    @runtime.app.post("/v1/auth/login")
    def login_account(
        data: dict,
        request: runtime.Request,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        started = runtime.time.perf_counter()
        username = str(data.get("username") or "").strip().lower()
        password = str(data.get("password") or "")
        account = db.query(runtime.UserAccount).filter_by(username=username).first()
        if not account or not runtime._password_valid(password, account.password_hash):
            runtime.write_audit_event(
                request=request,
                username=username,
                category="auth",
                action="login",
                status_code=401,
                latency_ms=round((runtime.time.perf_counter() - started) * 1000),
                error="Invalid username or password",
            )
            raise runtime.HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
        try:
            runtime.assert_account_access(db, account.user_id)
        except runtime.HTTPException as exc:
            runtime.write_audit_event(
                request=request,
                user_id=account.user_id,
                username=username,
                category="auth",
                action="login",
                status_code=exc.status_code,
                latency_ms=round((runtime.time.perf_counter() - started) * 1000),
                error=str(exc.detail),
            )
            raise
        runtime.write_audit_event(
            request=request,
            user_id=account.user_id,
            username=username,
            category="auth",
            action="login",
            status_code=200,
            latency_ms=round((runtime.time.perf_counter() - started) * 1000),
        )
        return runtime.account_out(
            db, account.user_id, runtime._new_session(db, account.user_id)
        )

    runtime.login_account = login_account

    @runtime.app.get("/v1/auth/me")
    def auth_me(
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        return runtime.account_out(db, user)

    runtime.auth_me = auth_me


def bind_update_account(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.patch("/v1/auth/me")
    def update_account(
        data: dict,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        authorization: str | None = runtime.Header(None),
    ):
        account = db.get(runtime.UserAccount, user)
        if not account:
            raise runtime.HTTPException(
                404, "Tài khoản demo cũ chưa có hồ sơ đăng nhập"
            )
        if "display_name" in data:
            account.display_name = (
                str(data["display_name"]).strip()[:80] or account.display_name
            )
        if "theme" in data:
            if data["theme"] not in ("light", "dark"):
                raise runtime.HTTPException(400, "Theme không hợp lệ")
            account.theme = data["theme"]
        profile = db.get(runtime.UserProfile, user)
        if not profile:
            profile = runtime.UserProfile(user_id=user)
            db.add(profile)
        if "bio" in data:
            bio = str(data["bio"]).strip()[:500]
            runtime.ensure_safe_content(bio)
            profile.bio = bio
        if "language" in data:
            if not runtime.re.fullmatch(
                r"[a-z]{2,3}(?:-[A-Z]{2})?", str(data["language"])
            ):
                raise runtime.HTTPException(400, "Ngôn ngữ không hợp lệ")
            profile.language = data["language"]
        if "reduced_motion" in data:
            profile.reduced_motion = int(bool(data["reduced_motion"]))
        if data.get("new_password"):
            if not runtime._password_valid(
                str(data.get("current_password") or ""), account.password_hash
            ):
                raise runtime.HTTPException(400, "Mật khẩu hiện tại không đúng")
            if len(str(data["new_password"])) < 6:
                raise runtime.HTTPException(400, "Mật khẩu mới cần ít nhất 6 ký tự")
            account.password_hash = runtime._password_hash(str(data["new_password"]))
            sessions = db.query(runtime.UserSession).filter_by(user_id=user)
            if authorization and authorization.lower().startswith("bearer "):
                current_hash = runtime.hashlib.sha256(
                    authorization.split(None, 1)[1].strip().encode()
                ).hexdigest()
                sessions = sessions.filter(
                    runtime.UserSession.token_hash != current_hash
                )
            sessions.delete(synchronize_session=False)
        profile.updated_at = runtime.now()
        account.updated_at = runtime.now()
        db.commit()
        return runtime.account_out(db, user)

    runtime.update_account = update_account

    @runtime.app.post("/v1/auth/me/avatar")
    def update_user_avatar(
        file: runtime.UploadFile = runtime.File(...),
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        content = file.file.read(3 * 1024 * 1024 + 1)
        mime = (file.content_type or "").lower()
        if len(content) > 3 * 1024 * 1024:
            raise runtime.HTTPException(413, "Avatar tối đa 3 MB")
        if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            raise runtime.HTTPException(400, "Chỉ hỗ trợ JPG, PNG, WEBP hoặc GIF")
        row = db.get(runtime.UserAvatar, user)
        if row:
            row.mime_type = mime
            row.content = content
            row.updated_at = runtime.now()
        else:
            db.add(runtime.UserAvatar(user_id=user, mime_type=mime, content=content))
        db.commit()
        return {"avatar_url": f"/v1/users/{user}/avatar"}

    runtime.update_user_avatar = update_user_avatar

    @runtime.app.get("/v1/users/{user_id}/avatar")
    def user_avatar(
        user_id: str, db: runtime.DBSession = runtime.Depends(runtime.db_session)
    ):
        row = db.get(runtime.UserAvatar, user_id)
        if not row:
            raise runtime.HTTPException(404, "Avatar not found")
        return runtime.Response(
            row.content,
            media_type=row.mime_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    runtime.user_avatar = user_avatar

    @runtime.app.post("/v1/auth/logout")
    def logout_account(
        request: runtime.Request,
        authorization: str | None = runtime.Header(default=None),
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        account = db.get(runtime.UserAccount, user)
        runtime.write_audit_event(
            request=request,
            user_id=user,
            username=(account.username if account else ""),
            category="auth",
            action="logout",
            status_code=200,
        )
        if authorization and authorization.lower().startswith("bearer "):
            row = db.get(
                runtime.UserSession,
                runtime.hashlib.sha256(
                    authorization.split(None, 1)[1].strip().encode()
                ).hexdigest(),
            )
            if row:
                db.delete(row)
                db.commit()
        return {"logged_out": True}

    runtime.logout_account = logout_account
