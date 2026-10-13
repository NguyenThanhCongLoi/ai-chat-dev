/** database CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import { mountLoadingCat } from "../../roleplay/loadingCatDom";
import type { DbRows } from "../types";

export function createDatabaseController(runtime: AdminRuntime) {
  function renderDatabase() {
    const host = document.querySelector("#database")!;
    if (
      !runtime.dbTables.some((t) => t.name === runtime.activeDbTable) &&
      runtime.dbTables.length
    )
      runtime.activeDbTable = runtime.dbTables[0].name;
    host.innerHTML = `<section class="panel"><header><div class="row"><label class="mdlFilter">Bảng <select class="sm" id="db-table">${runtime.dbTables.map((t) => `<option value="${runtime.esc(t.name)}" ${t.name === runtime.activeDbTable ? "selected" : ""}>${runtime.esc(t.name)} (${t.rows.toLocaleString("vi-VN")})</option>`).join("")}</select></label><input class="input logSearch" id="db-user-filter" placeholder="Lọc theo user ID, VD u_01"></div><div class="row"><span class="chip tnum" id="db-count">…</span><span class="chip">Chỉ đọc</span></div></header><div id="db-grid"><p class="empty" style="margin:14px">Đang tải…</p></div></section>${runtime.cmsModal("modal-db-row", "Bản ghi", "Database", `<div id="db-row-body"></div>`, `<button class="btn" data-close>Đóng</button>`)}`;
    host.querySelector("#db-table")?.addEventListener("change", (event) => {
      runtime.activeDbTable = (event.target as HTMLSelectElement).value;
      void runtime.loadDbRows();
    });
    let timer = 0;
    host.querySelector("#db-user-filter")?.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => void runtime.loadDbRows(), 300);
    });
    void runtime.loadDbRows();
  }

  async function loadDbRows() {
    const grid = document.querySelector("#db-grid");
    if (!grid || !runtime.activeDbTable) return;
    grid.innerHTML = '<div class="empty" role="status">Đang tải…</div>';
    mountLoadingCat(grid.firstElementChild!);
    const user = document
      .querySelector<HTMLInputElement>("#db-user-filter")
      ?.value.trim();
    try {
      const data = await runtime.request<DbRows>(
        `/v1/admin/database/${encodeURIComponent(runtime.activeDbTable)}?limit=100${user ? `&user_id=${encodeURIComponent(user)}` : ""}`,
      );
      runtime.dbRows = data.rows;
      runtime.dbColumns = data.columns;
      document.querySelector("#db-count")!.textContent =
        data.total > data.rows.length
          ? `${data.rows.length} / ${data.total.toLocaleString("vi-VN")} dòng`
          : `${data.total.toLocaleString("vi-VN")} dòng`;
      const rows = data.rows
        .map(
          (row, i) =>
            `<tr class="clickRow" data-db-row="${i}">${data.columns
              .map((c) => {
                const v = runtime.dbCell(row[c]);
                return `<td class="${runtime.isRedacted(v) ? "redact" : "mono"}" title="${runtime.esc(v)}">${runtime.esc(v.length > 60 ? `${v.slice(0, 60)}…` : v)}</td>`;
              })
              .join("")}</tr>`,
        )
        .join("");
      grid.innerHTML = data.rows.length
        ? `<div class="tbl-wrap"><table class="dt dbTable"><thead><tr>${data.columns.map((c) => `<th>${runtime.esc(c)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>`
        : '<p class="empty" style="margin:14px">Không có dòng nào khớp.</p>';
      grid.querySelectorAll<HTMLElement>("[data-db-row]").forEach((tr) =>
        tr.addEventListener("click", () => {
          const row = runtime.dbRows[Number(tr.dataset.dbRow)];
          document.querySelector("#modal-db-row header h2")!.textContent =
            `${runtime.activeDbTable} · ${runtime.dbCell(row.id ?? row[runtime.dbColumns[0]])}`;
          document.querySelector("#db-row-body")!.innerHTML =
            `<div class="kvs logKvs">${runtime.dbColumns
              .map((c) => {
                const v = runtime.dbCell(row[c]);
                return `<div class="kv"><span class="mono">${runtime.esc(c)}</span><span class="${runtime.isRedacted(v) ? "redact" : "mono"}">${runtime.esc(v) || '<span class="faint">—</span>'}</span></div>`;
              })
              .join("")}</div>`;
          runtime.openCmsModal("modal-db-row");
        }),
      );
    } catch (error) {
      grid.innerHTML = `<div class="err" style="margin:14px">${runtime.esc(error)}</div>`;
    }
  }

  return { renderDatabase, loadDbRows };
}
