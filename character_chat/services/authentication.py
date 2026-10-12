"""services.authentication: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_db_session(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def db_session():
        with runtime.Session() as db:
            yield db

    runtime.db_session = db_session

    def _password_hash(password: str, salt: bytes | None = None):
        salt = salt or runtime.secrets.token_bytes(16)
        digest = runtime.hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
        return (
            runtime.base64.urlsafe_b64encode(salt).decode()
            + "."
            + runtime.base64.urlsafe_b64encode(digest).decode()
        )

    runtime._password_hash = _password_hash

    def _password_valid(password: str, stored: str):
        try:
            salt_encoded, _ = stored.split(".", 1)
            salt = runtime.base64.urlsafe_b64decode(salt_encoded.encode())
            return runtime.secrets.compare_digest(
                runtime._password_hash(password, salt), stored
            )
        except Exception:
            return False

    runtime._password_valid = _password_valid

    def _new_session(db, user_id):
        token = runtime.secrets.token_urlsafe(32)
        token_hash = runtime.hashlib.sha256(token.encode()).hexdigest()
        expires = (
            runtime.datetime.now(runtime.timezone.utc) + runtime.timedelta(days=30)
        ).isoformat()
        db.add(
            runtime.UserSession(
                token_hash=token_hash, user_id=user_id, expires_at=expires
            )
        )
        db.commit()
        return token

    runtime._new_session = _new_session

    def access_control(db):
        def enabled(key, default=False):
            row = db.get(runtime.AppSetting, key)
            value = row.value if row else ("true" if default else "false")
            return value.strip().lower() in ("1", "true", "yes", "on")

        return {
            "maintenance_mode": enabled("access:maintenance_mode"),
            "registration_enabled": enabled("access:registration_enabled", True),
        }

    runtime.access_control = access_control

    def assert_account_access(db, user_id):
        account = db.get(runtime.UserAccount, user_id)
        control = runtime.access_control(db)
        if not account:
            if control["maintenance_mode"]:
                raise runtime.HTTPException(
                    503,
                    "Hệ thống đang bảo trì. Chỉ tài khoản quản trị được phép truy cập.",
                )
            return None
        if (
            account.status == "suspended"
            and account.suspended_until
            and account.suspended_until <= runtime.now()
        ):
            account.status = "active"
            account.suspended_until = None
            account.ban_reason = ""
            account.updated_at = runtime.now()
            db.commit()
        if account.status != "active":
            detail = "Tài khoản đã bị tạm khóa"
            if account.ban_reason:
                detail += f": {account.ban_reason}"
            if account.suspended_until:
                detail += f" (đến {account.suspended_until})"
            raise runtime.HTTPException(403, detail)
        if control["maintenance_mode"] and not account.is_admin:
            raise runtime.HTTPException(
                503, "Hệ thống đang bảo trì. Chỉ tài khoản quản trị được phép truy cập."
            )
        return account

    runtime.assert_account_access = assert_account_access

    # Keep the same dependency object exported on the runtime for dependency_overrides.
    def current_user(
        authorization: str | None = runtime.Header(default=None),
        x_demo_user_id: str = runtime.Header(default="demo"),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(None, 1)[1].strip()
            token_hash = runtime.hashlib.sha256(token.encode()).hexdigest()
            session = db.get(runtime.UserSession, token_hash)
            if (
                not session
                or session.expires_at
                <= runtime.datetime.now(runtime.timezone.utc).isoformat()
            ):
                raise runtime.HTTPException(
                    401, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn"
                )
            runtime.assert_account_access(db, session.user_id)
            return session.user_id
        if runtime.os.getenv("DEMO_AUTH_ENABLED", "true").strip().lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            raise runtime.HTTPException(401, "Vui lòng đăng nhập để tiếp tục")
        if not runtime.re.fullmatch(r"[\w-]{1,80}", x_demo_user_id):
            raise runtime.HTTPException(400, "Invalid demo user ID")
        if runtime.access_control(db)["maintenance_mode"]:
            raise runtime.HTTPException(
                503,
                "Hệ thống đang bảo trì. Vui lòng đăng nhập bằng tài khoản quản trị.",
            )
        if not db.get(runtime.User, x_demo_user_id):
            db.add(runtime.User(id=x_demo_user_id))
            db.commit()
        return x_demo_user_id

    runtime.current_user = current_user

    def account_out(db, user_id, token=None):
        account = db.get(runtime.UserAccount, user_id)
        profile = db.get(runtime.UserProfile, user_id)
        result = {
            "id": user_id,
            "username": account.username if account else user_id,
            "display_name": account.display_name if account else user_id,
            "theme": account.theme if account else "light",
            "is_admin": bool(account and account.is_admin),
            "bio": profile.bio if profile else "",
            "language": profile.language if profile else "vi",
            "reduced_motion": bool(profile and profile.reduced_motion),
            "avatar_url": (
                f"/v1/users/{user_id}/avatar"
                if db.get(runtime.UserAvatar, user_id)
                else None
            ),
        }
        if token:
            result["token"] = token
        return result

    runtime.account_out = account_out
