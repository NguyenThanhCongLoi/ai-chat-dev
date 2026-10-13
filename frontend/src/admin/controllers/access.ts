/** access CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import { mountLoadingCat } from "../../roleplay/loadingCatDom";
import type { AccessControl } from "../types";

export function createAccessController(runtime: AdminRuntime) {
  function renderAccess() {
    const host = document.querySelector("#access")!;
    if (!runtime.accessControl) {
      host.innerHTML = '<div class="empty" role="status">Đang tải…</div>';
      mountLoadingCat(host.firstElementChild!);
      return;
    }
    host.innerHTML = `<div class="accessLayout"><section class="settingPanel"><h2>Chế độ truy cập</h2><p>Khi bảo trì được bật, chỉ tài khoản có quyền quản trị mới dùng được sản phẩm. CMS vẫn hoạt động.</p><div class="accessSwitches"><label><input id="maintenance-mode" type="checkbox" ${runtime.accessControl.maintenance_mode ? "checked" : ""}/><span><b>Chế độ bảo trì</b><small>Khóa tài khoản thường và người dùng demo</small></span></label><label><input id="registration-enabled" type="checkbox" ${runtime.accessControl.registration_enabled ? "checked" : ""}/><span><b>Cho phép đăng ký mới</b><small>Tắt riêng việc tạo tài khoản mới</small></span></label></div><div class="editorActions"><span class="statusText" id="access-status">${runtime.accessControl.maintenance_mode ? "Đang chỉ cho phép admin" : "Sản phẩm đang mở công khai"}</span><button class="btn pri" id="save-access">Lưu chế độ</button></div></section><section class="settingPanel"><h2>Tạo tài khoản quản trị</h2><p>Tài khoản này đăng nhập trên giao diện sản phẩm và vẫn hoạt động khi bảo trì.</p><div class="fields"><label class="field">Tên đăng nhập<input id="admin-account-username" autocomplete="off"/></label><label class="field">Tên hiển thị<input id="admin-account-name"/></label><label class="field full">Mật khẩu ban đầu<div class="passwordField"><input id="admin-account-password" type="password" autocomplete="new-password"/><button type="button" class="passwordToggle" id="toggle-admin-password" aria-pressed="false">Hiện</button></div></label></div><div class="editorActions"><span class="statusText" id="create-account-status">Chưa tạo</span><button class="btn pri" id="create-admin-account">Tạo tài khoản admin</button></div></section><section class="panel wide"><div class="panelHead"><div><h2>Quản lý tài khoản</h2><p>Khóa sẽ thu hồi mọi phiên đăng nhập hiện có ngay lập tức.</p></div></div><div class="accountCards">${runtime.accessControl.accounts.map((a) => `<article><div><strong>${runtime.esc(a.display_name)} <small>@${runtime.esc(a.username)}</small></strong><span>${a.is_admin ? '<b class="pill">Admin</b>' : ""}<i class="accountStatus ${runtime.esc(a.status)}">${a.status === "active" ? "Hoạt động" : a.status === "suspended" ? "Tạm khóa" : "Đã cấm"}</i></span><small>${runtime.esc(a.ban_reason || a.created_at)}</small></div><div class="accountActions"><button class="mini" data-admin-toggle="${runtime.esc(a.user_id)}">${a.is_admin ? "Bỏ quyền admin" : "Cấp quyền admin"}</button><button class="mini ${a.status === "active" ? "danger" : ""}" data-status-toggle="${runtime.esc(a.user_id)}">${a.status === "active" ? "Tạm khóa" : "Mở khóa"}</button></div></article>`).join("") || '<div class="empty">Chưa có tài khoản đăng ký.</div>'}</div></section></div>`;
    document
      .querySelector("#save-access")
      ?.addEventListener("click", runtime.saveAccess);
    document
      .querySelector("#toggle-admin-password")
      ?.addEventListener("click", () => {
        const input = document.querySelector<HTMLInputElement>(
          "#admin-account-password",
        )!;
        const button = document.querySelector<HTMLButtonElement>(
          "#toggle-admin-password",
        )!;
        const visible = input.type === "text";
        input.type = visible ? "password" : "text";
        button.textContent = visible ? "Hiện" : "Ẩn";
        button.setAttribute("aria-pressed", String(!visible));
      });
    document
      .querySelector("#create-admin-account")
      ?.addEventListener("click", runtime.createAdminAccount);
    host
      .querySelectorAll<HTMLButtonElement>("[data-admin-toggle]")
      .forEach((b) =>
        b.addEventListener("click", () =>
          runtime.updateAccessAccount(b.dataset.adminToggle!, {
            is_admin: !runtime.accessControl!.accounts.find(
              (a) => a.user_id === b.dataset.adminToggle,
            )!.is_admin,
          }),
        ),
      );
    host
      .querySelectorAll<HTMLButtonElement>("[data-status-toggle]")
      .forEach((b) =>
        b.addEventListener("click", () => {
          const a = runtime.accessControl!.accounts.find(
            (x) => x.user_id === b.dataset.statusToggle,
          )!;
          runtime.updateAccessAccount(a.user_id, {
            status: a.status === "active" ? "suspended" : "active",
            ban_reason: a.status === "active" ? "Tạm khóa từ CMS" : "",
            suspended_until: null,
          });
        }),
      );
  }

  async function saveAccess() {
    const status = document.querySelector("#access-status")!;
    status.textContent = "Đang lưu…";
    mountLoadingCat(status, "inline");
    try {
      runtime.accessControl = await runtime.request<AccessControl>(
        "/v1/admin/access-control",
        {
          method: "PUT",
          body: JSON.stringify({
            maintenance_mode:
              document.querySelector<HTMLInputElement>("#maintenance-mode")!
                .checked,
            registration_enabled: document.querySelector<HTMLInputElement>(
              "#registration-enabled",
            )!.checked,
          }),
        },
      );
      runtime.renderAccess();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  async function createAdminAccount() {
    const status = document.querySelector("#create-account-status")!;
    status.textContent = "Đang tạo…";
    mountLoadingCat(status, "inline");
    try {
      await runtime.request("/v1/admin/accounts", {
        method: "POST",
        body: JSON.stringify({
          username: document.querySelector<HTMLInputElement>(
            "#admin-account-username",
          )!.value,
          display_name: document.querySelector<HTMLInputElement>(
            "#admin-account-name",
          )!.value,
          password: document.querySelector<HTMLInputElement>(
            "#admin-account-password",
          )!.value,
          is_admin: true,
        }),
      });
      runtime.accessControl = await runtime.request<AccessControl>(
        "/v1/admin/access-control",
      );
      runtime.renderAccess();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  async function updateAccessAccount(
    userId: string,
    changes: Record<string, unknown>,
  ) {
    await runtime.request(`/v1/admin/accounts/${encodeURIComponent(userId)}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
    runtime.accessControl = await runtime.request<AccessControl>(
      "/v1/admin/access-control",
    );
    runtime.renderAccess();
  }

  return { renderAccess, saveAccess, createAdminAccount, updateAccessAccount };
}
