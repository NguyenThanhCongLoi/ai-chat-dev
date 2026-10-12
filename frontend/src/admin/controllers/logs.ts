/** logs CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import type { LogRow } from "../types";

export function createLogsController(runtime: AdminRuntime) {
  function logModelName(
    value: unknown,
    configId: unknown,
    product: unknown,
  ): string {
    const raw = runtime.usable(value);
    if (!raw) return "";
    const assistant = runtime.logText(product) === "assistant";
    const savedId = runtime.logText(configId).trim();
    const byId = runtime.models.find((item) => item.id === (savedId || raw));
    if (savedId && !byId) return raw;
    const matches = byId
      ? [byId]
      : runtime.models.filter(
          (item) =>
            (assistant
              ? item.assistant_model_id || item.model_id
              : item.model_id) === raw,
        );
    if (matches.length !== 1) return raw;
    const item = matches[0];
    return (assistant ? item.assistant_name || item.name : item.name) || raw;
  }

  function logSpeakerCell(row: LogRow) {
    const mode = runtime.logText(row.assistant_mode);
    if (mode)
      return `<div class="row ovName">${runtime.assistantFace(mode, 26)}<span>${runtime.esc(runtime.assistantName(mode))}</span></div>`;
    const name = runtime.logText(row.character_name),
      avatar = runtime.logText(row.character_avatar_url);
    if (!name) return '<span class="faint">—</span>';
    return `<div class="row ovName">${avatar ? `<img class="ovAvatar" src="${runtime.esc(avatar)}" alt="">` : runtime.initialAvatar(name)}<span>${runtime.esc(name)}</span></div>`;
  }

  function logDetailHtml(row: LogRow, columns: string[]) {
    const timingLabels: Record<string, string> = {
      server_prepare_ms: "Chuẩn bị trên server (ms)",
      gateway_headers_ms: "Gateway: nhận header (ms)",
      gateway_first_chunk_ms: "Gateway: chunk nội dung đầu (ms)",
    };
    return `<div class="kvs logKvs">${columns.map((c) => `<div class="kv"><span class="mono" title="${runtime.esc(c)}">${runtime.esc(timingLabels[c] || c)}</span><span>${runtime.esc(runtime.logText(row[c])) || '<span class="faint">—</span>'}</span></div>`).join("")}</div>`;
  }

  async function loadLogChatGateways() {
    const select =
      document.querySelector<HTMLSelectElement>("#logchat-gateway");
    if (!select) return;
    const gateways = await runtime.request<string[]>(
      `/v1/admin/chat-log-gateways?product=${encodeURIComponent(runtime.logchatProduct)}`,
    );
    select.innerHTML = `<option value="">Mọi gateway</option><option value="__unknown__">Chưa ghi nhận gateway</option>${gateways.map((base) => `<option value="${runtime.esc(base)}">${runtime.esc(base.replace(/^https?:\/\//, ""))}</option>`).join("")}`;
    select.value = runtime.logchatGateway;
  }

  async function renderConversations() {
    const host = document.querySelector("#conversations");
    if (!host) return;
    host.innerHTML = `<section class="panel"><header><div class="row"><div class="pills" id="logchat-product">${[
      ["all", "Tất cả"],
      ["roleplay", "Chat Bot AI"],
      ["assistant", "Trợ lý AI"],
    ]
      .map(
        ([k, v]) =>
          `<button type="button" data-product="${k}" aria-pressed="${runtime.logchatProduct === k}">${v}</button>`,
      )
      .join(
        "",
      )}</div><span class="chip tnum" id="logchat-count">…</span></div><input class="input logSearch" id="logchat-search" placeholder="Từ khóa: user, nội dung, model, gateway, phòng"><select class="input" id="logchat-gateway" aria-label="Lọc gateway"><option value="">Mọi gateway</option></select><button type="button" class="btn sm" id="logchat-export">Xuất CSV</button><span class="faint" id="logchat-export-status" role="status"></span></header><div class="row" style="padding:12px 16px;gap:12px;flex-wrap:wrap">
<label>Số log tải về <input class="input" id="logchat-export-count" type="number" min="1" step="1" placeholder="Tất cả" style="width:130px"></label>
<label>Khoảng ngày <select class="input" id="logchat-export-period"><option value="all">Tất cả thời gian</option><option value="today">Hôm nay</option><option value="7">7 ngày gần đây</option><option value="30">30 ngày gần đây</option><option value="custom">Tự chọn</option></select></label>
<label>Từ ngày <input class="input" type="date" id="logchat-export-from"></label>
<label>Đến ngày <input class="input" type="date" id="logchat-export-to"></label>
<small class="faint">Ngày theo giờ Việt Nam. Để trống số lượng để lấy tất cả; có giới hạn sẽ lấy log mới nhất theo bộ lọc.</small>
</div><div id="logchat-grid"><p class="empty" style="margin:14px">Đang tải…</p></div><div class="row" style="justify-content:flex-end;padding:12px 16px;gap:10px"><button type="button" class="btn ghost sm" id="logchat-newer">Mới hơn</button><span class="faint" id="logchat-page">Trang 1</span><button type="button" class="btn ghost sm" id="logchat-older">Cũ hơn</button></div></section>${runtime.cmsModal("modal-log-detail", "Chi tiết", "Log", `<div id="log-detail-body"></div>`, `<button class="btn" data-close>Đóng</button>`)}`;
    host.querySelectorAll<HTMLButtonElement>("[data-product]").forEach((b) =>
      b.addEventListener("click", () => {
        runtime.logchatProduct = b.dataset.product!;
        runtime.logchatGateway = "";
        runtime.logchatOffset = 0;
        host
          .querySelectorAll<HTMLButtonElement>("[data-product]")
          .forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        void runtime.loadLogChatGateways().then(runtime.loadChatLogs);
      }),
    );
    host
      .querySelector<HTMLSelectElement>("#logchat-gateway")
      ?.addEventListener("change", (event) => {
        runtime.logchatGateway = (
          event.currentTarget as HTMLSelectElement
        ).value;
        runtime.logchatOffset = 0;
        void runtime.loadChatLogs();
      });
    let timer = 0;
    host.querySelector("#logchat-search")?.addEventListener("input", () => {
      window.clearTimeout(timer);
      runtime.logchatOffset = 0;
      timer = window.setTimeout(() => void runtime.loadChatLogs(), 300);
    });
    host.querySelector("#logchat-newer")?.addEventListener("click", () => {
      runtime.logchatOffset = Math.max(
        0,
        runtime.logchatOffset - runtime.LOGCHAT_PAGE_SIZE,
      );
      void runtime.loadChatLogs();
    });
    host.querySelector("#logchat-older")?.addEventListener("click", () => {
      runtime.logchatOffset += runtime.LOGCHAT_PAGE_SIZE;
      void runtime.loadChatLogs();
    });
    const fromDate = host.querySelector<HTMLInputElement>(
      "#logchat-export-from",
    )!;
    const toDate = host.querySelector<HTMLInputElement>("#logchat-export-to")!;
    const period = host.querySelector<HTMLSelectElement>(
      "#logchat-export-period",
    )!;
    const vietnamDate = (value: Date) => {
      const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Ho_Chi_Minh",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).formatToParts(value);
      const part = (type: string) =>
        parts.find((item) => item.type === type)!.value;
      return `${part("year")}-${part("month")}-${part("day")}`;
    };
    period.addEventListener("change", () => {
      if (period.value === "custom") return;
      if (period.value === "all") {
        fromDate.value = "";
        toDate.value = "";
        return;
      }
      const today = vietnamDate(new Date());
      toDate.value = today;
      const first = new Date(today + "T00:00:00+07:00");
      first.setTime(
        first.getTime() -
          (period.value === "today" ? 0 : Number(period.value) - 1) * 86400000,
      );
      fromDate.value = vietnamDate(first);
    });
    [fromDate, toDate].forEach((input) =>
      input.addEventListener("change", () => {
        period.value = "custom";
      }),
    );
    host
      .querySelector<HTMLButtonElement>("#logchat-export")
      ?.addEventListener("click", async (event) => {
        const button = event.currentTarget as HTMLButtonElement;
        const status = host.querySelector<HTMLElement>(
          "#logchat-export-status",
        )!;
        const params = new URLSearchParams({
          product: runtime.logchatProduct,
          gateway: runtime.logchatGateway,
          q: host
            .querySelector<HTMLInputElement>("#logchat-search")!
            .value.trim(),
        });
        const countInput = host.querySelector<HTMLInputElement>(
          "#logchat-export-count",
        )!;
        const count = countInput.value.trim();
        if (
          count &&
          (!countInput.checkValidity() ||
            !Number.isSafeInteger(Number(count)) ||
            Number(count) < 1)
        ) {
          status.textContent = "Số log phải là số nguyên lớn hơn 0.";
          return;
        }
        if (fromDate.value && toDate.value && fromDate.value > toDate.value) {
          status.textContent =
            "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.";
          return;
        }
        if (count) params.set("max_rows", count);
        if (fromDate.value) params.set("start_date", fromDate.value);
        if (toDate.value) params.set("end_date", toDate.value);
        button.disabled = true;
        status.textContent = "Đang xuất log theo lựa chọn…";
        try {
          const response = await fetch(`/v1/admin/chat-logs.csv?${params}`);
          if (!response.ok)
            throw new Error(
              response.status === 401
                ? "Phiên CMS đã hết. Hãy đăng nhập lại."
                : "Không xuất được CSV.",
            );
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download =
            response.headers
              .get("Content-Disposition")
              ?.match(/filename="([^"]+)"/)?.[1] || "logchat.csv";
          document.body.append(link);
          link.click();
          link.remove();
          window.setTimeout(() => URL.revokeObjectURL(url), 10000);
          status.textContent = "Đã tải CSV.";
        } catch (error) {
          status.textContent = String(error);
        } finally {
          button.disabled = false;
        }
      });
    await runtime.loadLogChatGateways();
    await runtime.loadChatLogs();
  }

  async function loadChatLogs() {
    const grid = document.querySelector("#logchat-grid");
    if (!grid) return;
    const q = document
      .querySelector<HTMLInputElement>("#logchat-search")!
      .value.trim();
    const version = ++runtime.logchatRequestVersion;
    try {
      const data = await runtime.request<{
        total: number;
        offset: number;
        has_more: boolean;
        columns: string[];
        rows: LogRow[];
      }>(
        `/v1/admin/chat-logs?product=${encodeURIComponent(runtime.logchatProduct)}&q=${encodeURIComponent(q)}&gateway=${encodeURIComponent(runtime.logchatGateway)}&limit=${runtime.LOGCHAT_PAGE_SIZE}&offset=${runtime.logchatOffset}`,
      );
      if (version !== runtime.logchatRequestVersion) return;
      runtime.logchatRows = data.rows;
      runtime.logchatColumns = data.columns;
      document.querySelector("#logchat-count")!.textContent = data.rows.length
        ? `${runtime.logchatOffset + 1}–${runtime.logchatOffset + data.rows.length}${data.has_more ? "+" : ""} lượt chat`
        : "0 lượt chat";
      document.querySelector("#logchat-page")!.textContent =
        `Trang ${Math.floor(runtime.logchatOffset / runtime.LOGCHAT_PAGE_SIZE) + 1}`;
      (document.querySelector("#logchat-newer") as HTMLButtonElement).disabled =
        runtime.logchatOffset === 0;
      (document.querySelector("#logchat-older") as HTMLButtonElement).disabled =
        !data.has_more;
      const rows = data.rows
        .map((row, i) => {
          const fallbackUsed = runtime.truthy(row.fallback_used);
          const model =
            runtime.usable(row.primary_model_name) ||
            runtime.logModelName(
              row.primary_model,
              row.primary_model_config_id,
              row.product,
            ) ||
            runtime.usable(row.actual_model_name) ||
            runtime.logModelName(
              row.actual_model,
              row.actual_model_config_id,
              row.product,
            ) ||
            "—";
          const fallback = fallbackUsed
            ? runtime.usable(row.actual_model_name) ||
              runtime.logModelName(
                row.actual_model,
                row.actual_model_config_id,
                row.product,
              ) ||
              runtime.logModelName(row.fallback_model, "", row.product) ||
              "Có"
            : "—";
          const error = runtime.logText(row.error),
            reason = runtime.usable(row.fallback_reason);
          const gateway =
            runtime.usable(row.actual_api_base) ||
            runtime.usable(row.primary_api_base);
          const inferredGateway =
            runtime.logText(row.gateway_snapshot_source) === "inferred";
          const gatewayLabel = gateway
            ? gateway.replace(/^https?:\/\//, "").slice(0, 38) +
              (inferredGateway ? " (\u01b0\u1edbc t\u00ednh)" : "")
            : "\u2014";
          const latency = Number(row.latency_ms) || 0;
          const firstChunk =
            runtime.logText(row.task) === "suggestion"
              ? row.client_suggestion_ms
              : row.client_first_chunk_ms;
          const firstChunkLabel =
            typeof firstChunk === "number"
              ? `${firstChunk.toLocaleString("vi-VN")} ms`
              : "—";
          const issue = error
            ? `<span class="chip bad" title="${runtime.esc(error)}">${runtime.esc(error.slice(0, 60))}</span>`
            : fallbackUsed && reason
              ? `<span class="chip warn" title="${runtime.esc(reason)}">${runtime.esc(reason.slice(0, 60))}</span>`
              : "";
          const question = runtime.logText(row.user_message);
          const user =
            runtime.logText(row.user) || runtime.logText(row.user_id);
          const roomLabel = runtime.logText(row.room),
            turnId = runtime.logText(row.user_message_id);
          const output = runtime.logText(row.model_response);
          const taskLabel =
            runtime.logText(row.task) === "suggestion" ? "Gợi ý" : "Trả lời";
          return `<tr class="clickRow" data-log-row="${i}"><td class="mono">${runtime.esc(runtime.shortTime(row.created_at))}</td><td><span class="chip">${runtime.esc(runtime.PRODUCT_LABELS[runtime.logText(row.product)] || runtime.logText(row.product) || "—")}</span></td><td class="logUser" title="${runtime.esc(runtime.logText(row.user_id))}">${user ? runtime.esc(user) : '<span class="faint">—</span>'}</td><td class="logSpeaker">${runtime.logSpeakerCell(row)}</td><td class="logTurn" title="${runtime.esc(turnId)}"><span>${runtime.esc(roomLabel)}</span><small>${runtime.esc(taskLabel)} · ${runtime.esc(turnId.slice(0, 8))}</small></td><td class="logQuestion">${question ? runtime.esc(question.slice(0, 80)) + (question.length > 80 ? "…" : "") : '<span class="faint">—</span>'}</td><td class="logAnswer" title="${runtime.esc(output)}">${runtime.esc(output.slice(0, 120))}${output.length > 120 ? "…" : ""}</td><td title="${runtime.esc(runtime.logText(row.primary_model) || runtime.logText(row.actual_model))}">${runtime.esc(model)}</td><td title="${runtime.esc(runtime.logText(row.actual_model))}">${runtime.esc(fallback)}</td><td class="mono" title="${runtime.esc(gateway)}">${runtime.esc(gatewayLabel)}</td><td class="num">${runtime.esc(firstChunkLabel)}</td><td class="num">${latency ? `${latency.toLocaleString("vi-VN")} ms` : "—"}</td><td>${issue}</td></tr>`;
        })
        .join("");
      grid.innerHTML = data.rows.length
        ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Thời gian</th><th>Sản phẩm</th><th>Người dùng</th><th>Nhân vật</th><th>Phòng / lượt gửi</th><th>Câu hỏi</th><th>Câu trả lời / gợi ý</th><th>Model</th><th>Fallback</th><th>Gateway</th><th class="num" title="Từ bấm gửi đến chunk nội dung đầu tiên; với suggest: đến lúc nhận gợi ý tại trình duyệt">Latency</th><th class="num" title="Thời gian server xử lý đến khi nhận xong câu trả lời">Runtime</th><th>Lỗi</th></tr></thead><tbody>${rows}</tbody></table></div>`
        : '<p class="empty" style="margin:14px">Không có lượt chat nào khớp bộ lọc.</p>';
      grid.querySelectorAll<HTMLElement>("[data-log-row]").forEach((tr) =>
        tr.addEventListener("click", () => {
          const row = runtime.logchatRows[Number(tr.dataset.logRow)];
          document.querySelector("#modal-log-detail header h2")!.textContent =
            `Lượt chat · ${runtime.shortTime(row.created_at)}`;
          document.querySelector("#log-detail-body")!.innerHTML =
            runtime.logDetailHtml(row, runtime.logchatColumns);
          runtime.openCmsModal("modal-log-detail");
        }),
      );
    } catch (error) {
      grid.innerHTML = `<div class="err" style="margin:14px">${runtime.esc(error)}</div>`;
    }
  }

  function renderActionLogs() {
    const host = document.querySelector("#action-logs");
    if (!host) return;
    host.innerHTML = `<section class="panel"><header><div class="row"><label class="mdlFilter">Nhóm <select class="sm" id="action-category">${runtime.ACTION_GROUPS.map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></label><label class="mdlFilter">Trạng thái <select class="sm" id="action-status"><option value="all">Tất cả</option>${Object.entries(
      runtime.ACTION_STATUS,
    )
      .map(([k, [, v]]) => `<option value="${k}">${v}</option>`)
      .join(
        "",
      )}</select></label><input class="input logSearch" id="action-search" placeholder="Tìm user, hành động, URL hoặc lỗi"></div><span class="chip tnum" id="action-count">…</span></header><div id="action-grid"><p class="empty" style="margin:14px">Đang tải…</p></div></section>${runtime.cmsModal("modal-action-detail", "Chi tiết sự kiện", "Nhật ký hoạt động", `<div id="action-detail-body"></div>`, `<button class="btn" data-close>Đóng</button>`)}`;
    host
      .querySelector("#action-category")
      ?.addEventListener("change", () => void runtime.loadActionLogs());
    host
      .querySelector("#action-status")
      ?.addEventListener("change", () => void runtime.loadActionLogs());
    let timer = 0;
    host.querySelector("#action-search")?.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => void runtime.loadActionLogs(), 300);
    });
    void runtime.loadActionLogs();
  }

  async function loadActionLogs() {
    const grid = document.querySelector("#action-grid");
    if (!grid) return;
    const category =
      document.querySelector<HTMLSelectElement>("#action-category")!.value;
    const statusFilter =
      document.querySelector<HTMLSelectElement>("#action-status")!.value;
    const q = document
      .querySelector<HTMLInputElement>("#action-search")!
      .value.trim();
    try {
      const data = await runtime.request<{
        total: number;
        columns: string[];
        rows: LogRow[];
      }>(
        `/v1/admin/action-logs?category=${encodeURIComponent(category)}&status_filter=${encodeURIComponent(statusFilter)}&q=${encodeURIComponent(q)}&limit=500`,
      );
      runtime.actionRows = data.rows;
      runtime.actionColumns = data.columns;
      document.querySelector("#action-count")!.textContent =
        `${data.total} sự kiện`;
      const rows = data.rows
        .map((row, i) => {
          const [kind, label] = runtime.ACTION_STATUS[
            runtime.logText(row.status)
          ] || ["", runtime.logText(row.status) || "—"];
          const code = runtime.logText(row.status_code),
            path = runtime.logText(row.path),
            error = runtime.logText(row.error);
          return `<tr class="clickRow" data-action-row="${i}"><td class="mono">${runtime.esc(runtime.shortTime(row.created_at, false))}</td><td>${row.username ? `@${runtime.esc(runtime.logText(row.username))}` : '<span class="faint">khách</span>'}</td><td>${runtime.esc(runtime.logText(row.action) || path)}${Number(code) >= 400 ? ` → ${runtime.esc(code)}` : ""}${error ? `<br><small class="faint">${runtime.esc(error.slice(0, 90))}</small>` : ""}</td><td class="mono">${runtime.esc(runtime.logText(row.category))}</td><td><span class="chip ${kind}">${runtime.esc(label)}</span></td></tr>`;
        })
        .join("");
      grid.innerHTML = data.rows.length
        ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Giờ</th><th>Tài khoản</th><th>Hành động</th><th>Nhóm</th><th>Trạng thái</th></tr></thead><tbody>${rows}</tbody></table></div>`
        : '<p class="empty" style="margin:14px">Không có sự kiện nào khớp bộ lọc.</p>';
      grid.querySelectorAll<HTMLElement>("[data-action-row]").forEach((tr) =>
        tr.addEventListener("click", () => {
          const row = runtime.actionRows[Number(tr.dataset.actionRow)];
          document.querySelector(
            "#modal-action-detail header h2",
          )!.textContent = runtime.logText(row.action) || "Chi tiết sự kiện";
          document.querySelector("#action-detail-body")!.innerHTML =
            runtime.logDetailHtml(row, runtime.actionColumns);
          runtime.openCmsModal("modal-action-detail");
        }),
      );
    } catch (error) {
      grid.innerHTML = `<div class="err" style="margin:14px">${runtime.esc(error)}</div>`;
    }
  }

  return {
    logModelName,
    logSpeakerCell,
    logDetailHtml,
    loadLogChatGateways,
    renderConversations,
    loadChatLogs,
    renderActionLogs,
    loadActionLogs,
  };
}
