/** dashboard CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";

export function createDashboardController(runtime: AdminRuntime) {
  function renderDashboard() {
    if (!runtime.overview) return;
    const s = runtime.overview.stats;
    const kpis = [
      ["Người dùng", "users"],
      ["Nhân vật", "characters"],
      ["Phòng chat", "rooms"],
      ["Tin nhắn", "messages"],
      ["Ký ức", "memories"],
    ]
      .map(([label, key]) => {
        const delta = s[`${key}_delta`];
        return `<div class="kpi"><span>${label}</span><b>${runtime.fmtNumber(s[key])}</b><small${delta ? "" : ' class="faint"'}>${delta ? `+${runtime.fmtNumber(delta)} tuần này` : "toàn hệ thống"}</small></div>`;
      })
      .join("");
    const hasUsage = runtime.overview.characters.some(
      (c) => typeof c.usage_count === "number",
    );
    const top = [...runtime.overview.characters]
      .sort((a, b) => (b.usage_count || 0) - (a.usage_count || 0))
      .slice(0, 10);
    const maxUsage = Math.max(1, ...top.map((c) => c.usage_count || 0));
    const topRows = top
      .map(
        (c, i) =>
          `<tr><td class="num faint">${i + 1}</td><td><div class="row ovName">${c.avatar_url ? `<img class="ovAvatar" src="${runtime.esc(c.avatar_url)}" alt="">` : runtime.initialAvatar(c.name)}<span>${runtime.esc(c.name)}</span></div></td><td>${runtime.esc(runtime.ROLE_LABELS[c.role] || runtime.ROLE_LABELS[c.category] || c.role || "—")}</td><td>${hasUsage ? `<div class="bar-mini"><i style="width:${Math.round(((c.usage_count || 0) / maxUsage) * 80)}px"></i><span class="tnum">${runtime.fmtNumber(c.usage_count)}</span></div>` : `<span class="faint">${runtime.esc(c.category === "entertainment" ? "Giải trí" : "Hữu ích")}</span>`}</td></tr>`,
      )
      .join("");
    const docRows = runtime.overview.documents
      .slice(0, 6)
      .map((d) => {
        const kind =
          d.status === "ready" ? "ok" : d.status === "failed" ? "bad" : "warn";
        const label =
          d.status === "ready"
            ? "Sẵn sàng"
            : d.status === "failed"
              ? `Lỗi${d.error ? `: ${d.error}` : ""}`
              : "Đang xử lý";
        return `<tr><td class="mono">${runtime.esc(d.filename)}</td><td><span class="chip ${kind}">${runtime.esc(label)}</span></td></tr>`;
      })
      .join("");
    const charName = (id?: string) =>
      runtime.overview!.characters.find((c) => c.id === id)?.name;
    const traceRows = runtime.overview.ai_activity
      .slice(0, 6)
      .map(
        (a) =>
          `<tr><td class="mono">${runtime.fmtTime(a.created_at)}</td><td>${runtime.esc(a.room || charName(a.character_id) || "—")}</td><td class="num">${a.layers}</td><td class="num">${a.memories}</td><td class="num">${a.documents}</td></tr>`,
      )
      .join("");
    const table = (head: string, rows: string, empty: string, cols: number) =>
      `<div class="tbl-wrap"><table class="dt"><thead><tr>${head}</tr></thead><tbody>${rows || `<tr><td colspan="${cols}"><div class="empty">${empty}</div></td></tr>`}</tbody></table></div>`;
    document.querySelector("#dashboard")!.innerHTML =
      `<div class="kpis">${kpis}</div>

  <div class="cols2 ovGrid">

    <section class="panel"><header><h3>10 nhân vật đầu</h3><span class="faint mono">${hasUsage ? "theo lượt dùng" : "mới cập nhật"}</span></header>

      ${table(`<th class="num">#</th><th>Nhân vật</th><th>Loại</th><th>${hasUsage ? "Lượt dùng" : "Nhóm"}</th>`, topRows, "Chưa có nhân vật.", 4)}</section>

    <div class="stack" style="gap:14px">

      <section class="panel"><header><h3>Tài liệu</h3></header><div class="pb">

        <div class="row"><span class="chip ok">Sẵn sàng · ${runtime.fmtNumber(s.ready_documents)}</span><span class="chip bad">Lỗi · ${runtime.fmtNumber(s.failed_documents)}</span></div>

        ${table("<th>Tài liệu</th><th>Trạng thái</th>", docRows, "Chưa có tài liệu.", 2)}</div></section>

      <section class="panel"><header><h3>AI pipeline gần đây</h3></header>

        ${table('<th>Thời điểm</th><th>Phòng</th><th class="num">Lớp context</th><th class="num">Memory</th><th class="num">Tài liệu</th>', traceRows, "Chưa có hoạt động.", 5)}</section>

    </div>

  </div>`;
  }

  return { renderDashboard };
}
