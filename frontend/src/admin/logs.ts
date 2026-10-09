import { mountLoadingCat } from "../roleplay/loadingCatDom";

type CmsRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function createCmsLogViews(
  request: CmsRequest,
  esc: (value: unknown) => string,
  formatVietnamLogTime: (value: unknown) => string,
) {
  async function renderConversations() {
    const host = document.querySelector("#conversations");
    if (!host) return;
    host.innerHTML = `<section class="panel wide"><div class="panelHead logchatHead"><div><h2>Logchat tổng hợp</h2><p>.</p></div><div class="dbFilters"><select id="logchat-product"><option value="all">Tất cả sản phẩm</option><option value="roleplay">AI Role Play</option><option value="assistant">AI Assistant</option></select><input id="logchat-search" placeholder="Tìm user, nội dung, model hoặc phòng"/><button class="btn secondary" id="logchat-refresh">Lọc</button></div></div><div id="logchat-grid" class="dbGrid"><div class="empty">Đang tải…</div></div></section>`;
    const refresh = () => loadChatLogs();
    document
      .querySelector("#logchat-refresh")
      ?.addEventListener("click", refresh);
    document
      .querySelector("#logchat-search")
      ?.addEventListener("keydown", (event) => {
        if ((event as KeyboardEvent).key === "Enter") refresh();
      });
    refresh();
  }
  async function loadChatLogs() {
    const grid = document.querySelector("#logchat-grid");
    if (!grid) return;
    grid.innerHTML = '<div class="empty" role="status">Đang tải…</div>';
    mountLoadingCat(grid.firstElementChild!);
    const product =
      document.querySelector<HTMLSelectElement>("#logchat-product")!.value;
    const q = document
      .querySelector<HTMLInputElement>("#logchat-search")!
      .value.trim();
    try {
      const data = await request<{
        total: number;
        columns: string[];
        rows: Record<string, unknown>[];
      }>(
        `/v1/admin/chat-logs?product=${encodeURIComponent(product)}&q=${encodeURIComponent(q)}&limit=500`,
      );
      grid.innerHTML = `<div class="dbMeta">${data.total} lượt chat · thời gian Việt Nam (UTC+7) · cuộn ngang và dọc để xem toàn bộ</div><div class="dbTable logchatTable"><table><thead><tr>${data.columns.map((column) => `<th>${column === "created_at" ? "Thời gian (VN)" : esc(column)}</th>`).join("")}</tr></thead><tbody>${data.rows.map((row) => `<tr>${data.columns.map((column) => { const value = column === "created_at" ? formatVietnamLogTime(row[column]) : row[column]; return `<td class="logchat-${esc(column)}" title="${esc(value)}">${esc(value)}</td>`; }).join("")}</tr>`).join("") || `<tr><td colspan="${data.columns.length}">Chưa có logchat.</td></tr>`}</tbody></table></div>`;
    } catch (error) {
      grid.innerHTML = `<div class="error">${esc(error)}</div>`;
    }
  }
  function renderVoiceLogs() {
    const host = document.querySelector("#voice-logs");
    if (!host) return;
    host.innerHTML = `<section class="panel wide"><div class="panelHead logchatHead"><div><h2>Log voice</h2></div><div class="dbFilters"><select id="voice-event"><option value="all">Mọi sự kiện</option><option value="generation">Tạo audio</option><option value="listen">Lượt Nghe</option></select><select id="voice-status"><option value="all">Mọi trạng thái</option><option value="success">Tạo thành công</option><option value="error">Tạo lỗi</option><option value="started">Đã bắt đầu phát</option></select><input id="voice-search" placeholder="Tìm user, nhân vật, model, voice hoặc lỗi"/><button class="btn secondary" id="voice-refresh">Lọc</button></div></div><div id="voice-grid" class="dbGrid"><div class="empty">Đang tải…</div></div></section>`;
    host.querySelector("#voice-refresh")?.addEventListener("click", loadVoiceLogs);
    host.querySelector("#voice-search")?.addEventListener("keydown", (event) => { if ((event as KeyboardEvent).key === "Enter") loadVoiceLogs(); });
    loadVoiceLogs();
  }
  async function loadVoiceLogs() {
    const grid = document.querySelector("#voice-grid");
    if (!grid) return;
    grid.innerHTML = '<div class="empty" role="status">Đang tải…</div>';
    mountLoadingCat(grid.firstElementChild!);
    const eventType = document.querySelector<HTMLSelectElement>("#voice-event")!.value;
    const statusFilter = document.querySelector<HTMLSelectElement>("#voice-status")!.value;
    const q = document.querySelector<HTMLInputElement>("#voice-search")!.value.trim();
    try {
      const data = await request<{ total: number; columns: string[]; rows: Record<string, unknown>[] }>(`/v1/admin/voice-logs?event_type=${encodeURIComponent(eventType)}&status_filter=${encodeURIComponent(statusFilter)}&q=${encodeURIComponent(q)}&limit=500`);
      grid.innerHTML = `<div class="dbTable logchatTable"><table><thead><tr>${data.columns.map((column) => `<th>${column === "created_at" ? "Thời gian (VN)" : esc(column)}</th>`).join("")}</tr></thead><tbody>${data.rows.map((row) => `<tr>${data.columns.map((column) => { const value = column === "created_at" ? formatVietnamLogTime(row[column]) : row[column]; return `<td title="${esc(value)}">${esc(value)}</td>`; }).join("")}</tr>`).join("") || `<tr><td colspan="${data.columns.length}">Chưa có log voice.</td></tr>`}</tbody></table></div>`;
    } catch (error) {
      grid.innerHTML = `<div class="error">${esc(error)}</div>`;
    }
  }
  function renderActionLogs() {
    const host = document.querySelector("#action-logs");
    if (!host) return;
    host.innerHTML = `<section class="panel wide"><div class="panelHead logchatHead"><div><h2>Nhật ký hoạt động</h2><p>Đăng nhập, mở sản phẩm, sử dụng chức năng và lỗi HTTP. Mật khẩu, token và nội dung request không được ghi.</p></div><div class="dbFilters"><select id="action-category"><option value="all">Tất cả nhóm</option><option value="auth">Đăng nhập</option><option value="navigation">Truy cập app</option><option value="assistant">AI Assistant</option><option value="roleplay">AI Role Play</option><option value="document">Tài liệu</option><option value="api">API khác</option></select><select id="action-status"><option value="all">Mọi trạng thái</option><option value="success">Thành công</option><option value="partial">Câu trả lời dở</option><option value="error">Lỗi</option></select><input id="action-search" placeholder="Tìm user, action, URL hoặc lỗi"/><button class="btn secondary" id="action-refresh">Lọc</button></div></div><div id="action-grid" class="dbGrid"><div class="empty">Đang tải…</div></div></section>`;
    document
      .querySelector("#action-refresh")
      ?.addEventListener("click", loadActionLogs);
    document
      .querySelector("#action-search")
      ?.addEventListener("keydown", (event) => {
        if ((event as KeyboardEvent).key === "Enter") loadActionLogs();
      });
    loadActionLogs();
  }
  async function loadActionLogs() {
    const grid = document.querySelector("#action-grid");
    if (!grid) return;
    grid.innerHTML = '<div class="empty" role="status">Đang tải…</div>';
    mountLoadingCat(grid.firstElementChild!);
    const category =
      document.querySelector<HTMLSelectElement>("#action-category")!.value;
    const statusFilter =
      document.querySelector<HTMLSelectElement>("#action-status")!.value;
    const q = document
      .querySelector<HTMLInputElement>("#action-search")!
      .value.trim();
    try {
      const data = await request<{
        total: number;
        columns: string[];
        rows: Record<string, unknown>[];
      }>(
        `/v1/admin/action-logs?category=${encodeURIComponent(category)}&status_filter=${encodeURIComponent(statusFilter)}&q=${encodeURIComponent(q)}&limit=500`,
      );
      grid.innerHTML = `<div class="dbMeta">${data.total} sự kiện · cuộn ngang và dọc để xem toàn bộ</div><div class="dbTable logchatTable"><table><thead><tr>${data.columns.map((column) => `<th>${esc(column)}</th>`).join("")}</tr></thead><tbody>${data.rows.map((row) => `<tr>${data.columns.map((column) => `<td title="${esc(row[column])}">${esc(row[column])}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${data.columns.length}">Chưa có hoạt động.</td></tr>`}</tbody></table></div>`;
    } catch (error) {
      grid.innerHTML = `<div class="error">${esc(error)}</div>`;
    }
  }
  return { renderConversations, renderVoiceLogs, renderActionLogs };
}
