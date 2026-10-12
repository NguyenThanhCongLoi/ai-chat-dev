"""api.admin_accounts: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_admin_account_out(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def admin_account_out(account):
        return {
            "user_id": account.user_id,
            "username": account.username,
            "display_name": account.display_name,
            "status": account.status or "active",
            "is_admin": bool(account.is_admin),
            "suspended_until": account.suspended_until,
            "ban_reason": account.ban_reason or "",
            "created_at": account.created_at,
            "updated_at": account.updated_at,
        }

    runtime.admin_account_out = admin_account_out

    @runtime.app.get("/v1/admin/access-control")
    def admin_access_control(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        return {
            **runtime.access_control(db),
            "accounts": [
                runtime.admin_account_out(row)
                for row in db.query(runtime.UserAccount)
                .order_by(runtime.UserAccount.created_at.desc())
                .all()
            ],
        }

    runtime.admin_access_control = admin_access_control

    @runtime.app.put("/v1/admin/access-control")
    def admin_update_access_control(
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        if (
            bool(data.get("maintenance_mode"))
            and not db.query(runtime.UserAccount)
            .filter_by(status="active", is_admin=1)
            .count()
        ):
            raise runtime.HTTPException(
                400,
                "Hãy tạo ít nhất một tài khoản admin đang hoạt động trước khi bật bảo trì",
            )
        for field, key in (
            ("maintenance_mode", "access:maintenance_mode"),
            ("registration_enabled", "access:registration_enabled"),
        ):
            if field not in data:
                continue
            value = "true" if bool(data[field]) else "false"
            row = db.get(runtime.AppSetting, key)
            if row:
                row.value = value
                row.updated_at = runtime.now()
            else:
                db.add(runtime.AppSetting(key=key, value=value))
        db.commit()
        return {
            **runtime.access_control(db),
            "accounts": [
                runtime.admin_account_out(row)
                for row in db.query(runtime.UserAccount)
                .order_by(runtime.UserAccount.created_at.desc())
                .all()
            ],
        }

    runtime.admin_update_access_control = admin_update_access_control

    @runtime.app.post("/v1/admin/accounts")
    def admin_create_account(
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        username = str(data.get("username") or "").strip().lower()
        password = str(data.get("password") or "")
        display_name = str(data.get("display_name") or username).strip()
        if not runtime.re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
            raise runtime.HTTPException(400, "Tên đăng nhập cần 3–32 ký tự hợp lệ")
        if len(password) < 8:
            raise runtime.HTTPException(400, "Mật khẩu quản trị cần ít nhất 8 ký tự")
        if db.query(runtime.UserAccount).filter_by(username=username).first():
            raise runtime.HTTPException(409, "Tên đăng nhập đã tồn tại")
        user_id = runtime.uid()
        db.add(runtime.User(id=user_id))
        account = runtime.UserAccount(
            user_id=user_id,
            username=username,
            display_name=(display_name or username)[:80],
            password_hash=runtime._password_hash(password),
            is_admin=int(bool(data.get("is_admin", True))),
            status="active",
        )
        db.add(account)
        db.commit()
        return runtime.admin_account_out(account)

    runtime.admin_create_account = admin_create_account

    @runtime.app.patch("/v1/admin/accounts/{user_id}")
    def admin_update_account(
        user_id: str,
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        account = db.get(runtime.UserAccount, user_id)
        if not account:
            raise runtime.HTTPException(404, "Không tìm thấy tài khoản")
        if "is_admin" in data:
            account.is_admin = int(bool(data["is_admin"]))
        if "status" in data:
            value = str(data["status"])
            if value not in ("active", "suspended", "banned"):
                raise runtime.HTTPException(400, "Trạng thái không hợp lệ")
            account.status = value
        if "suspended_until" in data:
            account.suspended_until = str(data["suspended_until"] or "") or None
        if "ban_reason" in data:
            account.ban_reason = str(data["ban_reason"] or "")[:500]
        if data.get("new_password"):
            if len(str(data["new_password"])) < 8:
                raise runtime.HTTPException(400, "Mật khẩu mới cần ít nhất 8 ký tự")
            account.password_hash = runtime._password_hash(str(data["new_password"]))
        account.updated_at = runtime.now()
        if runtime.access_control(db)["maintenance_mode"] and (
            account.status != "active" or not account.is_admin
        ):
            remaining = (
                db.query(runtime.UserAccount)
                .filter(
                    runtime.UserAccount.user_id != user_id,
                    runtime.UserAccount.status == "active",
                    runtime.UserAccount.is_admin == 1,
                )
                .count()
            )
            if not remaining:
                raise runtime.HTTPException(
                    400, "Không thể khóa hoặc bỏ quyền admin cuối cùng khi đang bảo trì"
                )
        if (
            data.get("new_password")
            or account.status != "active"
            or (runtime.access_control(db)["maintenance_mode"] and not account.is_admin)
        ):
            db.query(runtime.UserSession).filter_by(user_id=user_id).delete()
        db.commit()
        return runtime.admin_account_out(account)

    runtime.admin_update_account = admin_update_account
