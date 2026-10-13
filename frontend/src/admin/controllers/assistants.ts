/** assistants CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import {
  HAIRS,
  faceSvg,
  illustrationHtml,
  personaFaceSvg,
} from "../../persona";
import { mountLoadingCat } from "../../roleplay/loadingCatDom";
import type {
  AssistantDraft,
  AssistantProfiles,
  AssistantTab,
  GlobalDraft,
  ModelConfig,
  Settings,
} from "../types";

export function createAssistantsController(runtime: AdminRuntime) {
  async function loadAssistantProfiles() {
    try {
      runtime.assistantProfiles = await runtime.request<AssistantProfiles>(
        "/v1/admin/assistant-profiles",
      );
      runtime.assistantProfilesAvailable = true;
    } catch {
      runtime.assistantProfilesAvailable = false;
    }
  }

  function loadAssistantDraft(purpose: string): AssistantDraft {
    const main = runtime.purposeModel(purpose),
      f1 = runtime.purposeModel(purpose + "_fallback"),
      f2 = runtime.purposeModel(purpose + "_fallback_2");
    const p = runtime.profileOf(purpose);
    return {
      main: main?.id || "",
      f1: f1?.id || "",
      f2: f2?.id || "",
      prompt: runtime.assistantPromptOf(main, purpose + "_instruction"),
      fp1: runtime.assistantPromptOf(f1, purpose + "_fallback_instruction"),
      fp2: runtime.assistantPromptOf(f2, purpose + "_fallback_2_instruction"),
      title: p.title,
      slogan: p.slogan,
      description: p.description,
      greeting: p.greeting,
      starters: p.starters.join("\n"),
      visible: p.visible,
      user_pick: p.user_pick,
    };
  }

  function loadGlobalDraft(): GlobalDraft {
    return {
      prompt: runtime.settings?.assistant_system_instruction || "",
      enabled: Object.fromEntries(
        runtime.models.map((m) => [m.id, m.assistant_enabled]),
      ),
    };
  }

  function assistantHealth(ids: string[]) {
    const picked = ids.filter(Boolean);
    const hidden = picked.filter((id) =>
      runtime.models.find((m) => m.id === id && !m.assistant_enabled),
    );
    if (!ids[0])
      return { k: "bad", t: "Chưa có model chính", n: picked.length };
    if (hidden.length)
      return { k: "warn", t: "Có model đang ẩn", n: picked.length };
    if (picked.length < 3)
      return {
        k: picked.length === 1 ? "bad" : "warn",
        t: `Thiếu ${3 - picked.length} dự phòng`,
        n: picked.length,
      };
    return { k: "ok", t: "Đủ model", n: 3 };
  }

  function assistantFace(purpose: string, size = 34) {
    const p = runtime.assistantProfiles.items[purpose];
    return p?.custom
      ? faceSvg(p.hue ?? 172, HAIRS[p.hair ?? 0], size)
      : personaFaceSvg(purpose, size);
  }

  function assistantIllustration(purpose: string) {
    const p = runtime.assistantProfiles.items[purpose];
    return p?.custom
      ? illustrationHtml(purpose, p.hue ?? 172, p.icon || "sparkles")
      : illustrationHtml(purpose);
  }

  function assistantCardPreview(o: {
    face: string;
    illustration: string;
    title: string;
    description: string;
    requests: number;
    hidden?: boolean;
  }) {
    return `<article class="asSpec asPreviewCard">${o.hidden ? '<span class="chip warn asPreviewHidden">Đang ẩn</span>' : ""}<div class="asSpecArt">${o.illustration}<span class="asSpecAvatar"><span class="modeAvatar" style="width:44px;height:44px">${o.face}</span></span></div><div class="asSpecBody"><b>${runtime.esc(o.title || "Tên trợ lý")}</b><p>${runtime.esc(o.description || "Mô tả ngắn của trợ lý")}</p><div class="asSpecFoot"><span class="asSpecCount">${runtime.ico("comment-alt")}<b class="tnum">${o.requests.toLocaleString("vi-VN")}</b> lượt tương tác</span><span class="btn pri sm">${runtime.ico("comment-alt")}Chat</span></div></div></article>`;
  }

  function assistantSaveBar() {
    return `<div class="savebar${runtime.assistantDirty ? " on" : ""}"><span id="assistant-save-status">${runtime.assistantDirty ? `${runtime.ico("info")} Có thay đổi chưa lưu` : `${runtime.ico("check")} Đã lưu`}</span><div class="savebarActions"><button class="btn" id="assistant-discard" ${runtime.assistantDirty ? "" : "disabled"}>Hủy thay đổi</button><button class="btn pri" id="assistant-save" ${runtime.assistantDirty ? "" : "disabled"}>Lưu thay đổi</button></div></div>`;
  }

  function assistantModelSelect(
    id: string,
    selected: string,
    placeholder = "— Chưa chọn —",
  ) {
    return `<select class="input" id="${id}"><option value="">${placeholder}</option>${runtime.models
      .map(
        (m) =>
          `<option value="${runtime.esc(m.id)}" ${m.id === selected ? "selected" : ""}>${runtime.esc(m.assistant_name || m.name)}${m.assistant_enabled ? "" : " (đang ẩn)"}</option>`,
      )
      .join("")}</select>`;
  }

  function assistantGlobalView() {
    const g = runtime.assistantGlobalDraft!;
    const rows = runtime.models
      .map(
        (m) =>
          `<tr><td><b>${runtime.esc(m.assistant_name || m.name)}</b></td><td class="mono">${runtime.esc(m.assistant_model_id || m.model_id)}</td><td><input type="checkbox" class="switch" data-assistant-enable="${runtime.esc(m.id)}" ${g.enabled[m.id] ? "checked" : ""} aria-label="Cho chọn ${runtime.esc(m.assistant_name || m.name)}"></td><td>${m.assistant_thinking_mode === "enabled" ? '<span class="chip acc">Bật</span>' : m.assistant_thinking_mode === "disabled" ? '<span class="chip">Tắt</span>' : '<span class="chip">Mặc định</span>'}</td><td class="mono">${runtime.esc(m.assistant_reasoning_effort === "default" ? "—" : m.assistant_reasoning_effort || "—")}</td><td class="act"><button class="btn ghost sm" data-assistant-edit-model="${runtime.esc(m.id)}">${runtime.ico("edit")}Sửa</button></td></tr>`,
      )
      .join("");
    return `<header class="dt-head">${runtime.assistantIcon("global", true)}<div class="grow"><h3>Prompt &amp; model chung</h3><small class="muted">Thiết lập nền cho mọi trợ lý. Prompt riêng của từng trợ lý được nối sau prompt chung.</small></div></header>

  <div class="pb dt-body">

    <div class="dt-sec"><div class="dt-t"><b>System prompt chung</b><small>Đứng đầu mọi lượt gọi model của Trợ lý AI; không ảnh hưởng Chat Bot AI</small></div><textarea class="input mono" id="assistant-global-prompt" rows="5">${runtime.esc(g.prompt)}</textarea><small class="faint tnum" id="assistant-global-count">${g.prompt.length} ký tự</small></div>


    <div class="dt-sec"><div class="dt-t"><b>Model hiển thị cho người dùng</b><small>Danh sách trong ô chọn Model ở màn chat. Tên hiển thị và Core Model ID chỉ áp dụng cho Trợ lý AI.</small></div>

      ${runtime.models.length ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Tên hiển thị</th><th>Core model</th><th>Cho chọn</th><th>Thinking</th><th>Effort</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<div class="empty">Chưa có model. Thêm model ở mục Cấu hình AI.</div>'}</div>

    ${runtime.profilesNote()}

  </div>${runtime.assistantSaveBar()}`;
  }

  function assistantInfoTab(purpose: string) {
    const d = runtime.assistantDraft!,
      general = purpose === "assistant_general";
    const starters = d.starters
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean)
      .slice(0, 4);
    const preview = general
      ? `<div class="pv-gen">${runtime.assistantFace(purpose, 44)}<div><b>${runtime.esc(d.title)}</b><p class="muted" style="font-size:13px;margin:0">${runtime.esc(d.description)}</p></div></div>`
      : runtime.assistantCardPreview({
          face: runtime.assistantFace(purpose, 44),
          illustration: runtime.assistantIllustration(purpose),
          title: d.title,
          description: d.description,
          requests: runtime.profileOf(purpose).stats?.requests || 0,
          hidden: !d.visible,
        });
    return `<div class="dt-grid">

    <div class="dt-sec"><div class="dt-t"><b>Thẻ trên trang chủ</b><small>Người dùng thấy thẻ này ở mục Trợ lý cá nhân</small></div>

      <div class="form-grid">

        <label class="field"><span>Tên trợ lý</span><input class="input" data-assistant-field="title" value="${runtime.esc(d.title)}"></label>

        <label class="field"><span>Slogan</span><input class="input" data-assistant-field="slogan" value="${runtime.esc(d.slogan)}"></label>

        <label class="field full"><span>Mô tả ngắn</span><input class="input" data-assistant-field="description" maxlength="80" value="${runtime.esc(d.description)}"><small class="tnum" id="assistant-desc-count">${d.description.length}/80 ký tự</small></label>

        <label class="field full"><span>Lời chào khi mở phòng</span><textarea class="input" rows="2" data-assistant-field="greeting">${runtime.esc(d.greeting)}</textarea></label>

        <label class="field full"><span>Câu hỏi gợi ý</span><textarea class="input" rows="3" data-assistant-field="starters">${runtime.esc(d.starters)}</textarea><small>Mỗi dòng một câu, tối đa 4</small></label>

        ${general ? "" : `<label class="switchRow full"><span><b>Hiển thị trên trang chủ</b><br><small class="muted">Tắt để ẩn thẻ; phòng cũ vẫn mở được từ lịch sử</small></span><input type="checkbox" class="switch" data-assistant-field="visible" ${d.visible ? "checked" : ""}></label>`}

      </div></div>

    <div class="dt-sec"><div class="dt-t"><b>Xem trước</b><small>Cập nhật theo nội dung bạn nhập</small></div>

      <div id="assistant-preview">${preview}</div>

      <div class="starters asPreviewStarters">${starters.map((t) => `<button tabindex="-1" type="button">${runtime.esc(t)}</button>`).join("")}</div></div>

  </div>`;
  }

  function assistantModelTab(purpose: string) {
    const d = runtime.assistantDraft!,
      h = runtime.assistantHealth([d.main, d.f1, d.f2]);
    const slot = (field: "main" | "f1" | "f2", label: string, hint: string) => {
      const m = runtime.models.find((x) => x.id === d[field]);
      const st = !d[field]
        ? ["bad", "Chưa chọn"]
        : m && !m.assistant_enabled
          ? ["warn", "Model đang ẩn"]
          : ["ok", "Sẵn sàng"];
      return `<div class="slot ${st[0]}"><div class="slotHead"><b>${label}</b><span class="chip ${st[0]}">${st[1]}</span></div>${runtime.assistantModelSelect(`assistant-slot-${field}`, d[field])}<small class="faint">${hint}</small></div>`;
    };
    return `<div class="dt-sec"><div class="dt-t"><b>Chuỗi model</b><small>Hệ thống gọi model chính trước; lỗi hoặc quá thời gian chờ thì chuyển sang dự phòng theo thứ tự</small></div>

      <div class="chain">${slot("main", "1 · Model chính", "Xử lý mọi yêu cầu khi hoạt động bình thường")}<span class="arrow">${runtime.ico("angle-small-right")}</span>${slot("f1", "2 · Dự phòng 1", "Dùng khi model chính lỗi")}<span class="arrow">${runtime.ico("angle-small-right")}</span>${slot("f2", "3 · Dự phòng 2", "Dùng khi cả hai model trên lỗi")}</div>

      ${h.k !== "ok" ? `<div class="note-info" style="background:var(--${h.k}-soft)">${runtime.ico("info")}<span><b>${h.t}.</b> Nên cấu hình đủ 1 model chính và 2 dự phòng để tránh gián đoạn.</span></div>` : ""}</div>

    <div class="dt-grid">

      <div class="dt-sec"><div class="dt-t"><b>Tham số theo model</b><small>Temperature và giới hạn token lấy từ cấu hình của model thực sự được gọi, kể cả model dự phòng hoặc model user chọn.</small></div><p class="muted">Sửa các tham số trong Cấu hình AI → Sửa model.</p></div>

      ${
        purpose === "assistant_suggestion"
          ? ""
          : `<div class="dt-sec"><div class="dt-t"><b>Lựa chọn của người dùng</b></div>

        <label class="switchRow"><span>Cho người dùng chọn model trong phòng chat<br><small class="muted">Danh sách model lấy từ Cài đặt chung</small></span><input type="checkbox" class="switch" data-assistant-field="user_pick" ${d.user_pick ? "checked" : ""}></label></div>`
      }

    </div>`;
  }

  function assistantPromptPreview(purpose: string, prompt: string) {
    return `<span class="lbl-g">Chung</span>${runtime.esc(runtime.settings?.assistant_system_instruction || "(trống)")}<hr><span class="lbl-r">${runtime.esc(runtime.assistantName(purpose))}</span>${runtime.esc(prompt || "(prompt base trong code)")}`;
  }

  function assistantPromptTab(purpose: string) {
    const d = runtime.assistantDraft!;
    const vars = [
      "{{user_name}}",
      "{{language}}",
      "{{memories}}",
      "{{room_files}}",
      "{{today}}",
    ];
    return `<div class="dt-grid">

      <div class="dt-sec"><div class="dt-t"><b>Prompt riêng của trợ lý</b><small>Nối sau prompt chung. Để trống thì hệ thống dùng prompt base trong code.</small></div>

        <textarea class="input mono" id="assistant-prompt-main" rows="8">${runtime.esc(d.prompt)}</textarea>

        <div class="promptTools"><div class="row" style="gap:4px">${vars.map((v) => `<button type="button" class="chip promptVar" data-assistant-var="${v}" title="Chèn biến">${v}</button>`).join("")}</div><small class="faint tnum" id="assistant-prompt-count">${d.prompt.length} ký tự</small></div>

        <div class="dt-t"><b>Prompt cho model dự phòng</b><small>Dùng khi hệ thống chuyển sang dự phòng</small></div>

        <label class="field"><span>Dự phòng 1</span><textarea class="input mono" id="assistant-prompt-f1" rows="3" ${d.f1 ? "" : 'disabled placeholder="Chưa chọn model dự phòng 1"'}>${runtime.esc(d.fp1)}</textarea></label>

        <label class="field"><span>Dự phòng 2</span><textarea class="input mono" id="assistant-prompt-f2" rows="3" ${d.f2 ? "" : 'disabled placeholder="Chưa chọn model dự phòng 2"'}>${runtime.esc(d.fp2)}</textarea></label></div>

      <div class="dt-sec"><div class="dt-t"><b>Prompt hoàn chỉnh gửi tới model</b><small>Chỉ xem</small></div>

        <div class="prompt-pv" id="assistant-prompt-preview">${runtime.assistantPromptPreview(purpose, d.prompt)}</div></div>

    </div>`;
  }

  function assistantStatsTab(purpose: string) {
    const st = runtime.profileOf(purpose).stats;
    if (!st)
      return `<div class="empty">Chưa có số liệu thống kê cho trợ lý này.</div>`;
    const max = Math.max(1, ...st.days);
    const labels = Array.from({ length: st.days.length }, (_, i) => {
      const day = new Date(
        Date.now() - (st.days.length - 1 - i) * 86400000,
      ).getDay();
      return day === 0 ? "CN" : `T${day + 1}`;
    });
    const pct = (v: number) => `${String(v).replace(".", ",")}%`;
    return `<div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr));margin:0">

      <div class="kpi"><span>Lượt tương tác</span><b>${st.requests.toLocaleString("vi-VN")}</b><small class="faint">từ khi ra mắt</small></div>

      <div class="kpi"><span>Tỉ lệ dùng dự phòng</span><b>${pct(st.fallback_rate)}</b><small style="color:var(--${st.fallback_rate > 5 ? "warn" : "ok"})">${st.fallback_rate > 5 ? "cao hơn ngưỡng 5%" : "trong ngưỡng"}</small></div>

      <div class="kpi"><span>Thời gian phản hồi TB</span><b>${String(st.latency).replace(".", ",")} s</b><small class="faint">7 ngày qua</small></div>

      <div class="kpi"><span>Tỉ lệ lỗi</span><b>${pct(st.error_rate)}</b><small style="color:var(--${st.error_rate > 1 ? "bad" : "ok"})">${st.error_rate > 1 ? "cần kiểm tra" : "ổn định"}</small></div></div>

    <div class="dt-sec"><div class="dt-t"><b>Lượt tương tác 7 ngày</b><small>nghìn lượt mỗi ngày</small></div>

      <div class="bars">${st.days.map((v, i) => `<div class="bar-c"><span class="tnum">${v.toFixed(1).replace(".", ",")}</span><i style="height:${Math.round((v / max) * 100)}%" class="${i === st.days.length - 1 ? "last" : ""}"></i><small>${labels[i]}</small></div>`).join("")}</div></div>`;
  }

  function assistantDetailView(purpose: string) {
    const d = runtime.assistantDraft!,
      h = runtime.assistantHealth([d.main, d.f1, d.f2]),
      task = purpose === "assistant_suggestion";
    const tabs: [AssistantTab, string][] = [
      ...(task ? [] : ([["info", "Hiển thị"]] as [AssistantTab, string][])),
      ["model", "Model & dự phòng"],
      ["prompt", "Prompt"],
      ["stats", "Thống kê"],
    ];
    if (task && runtime.activeAssistantTab === "info")
      runtime.activeAssistantTab = "model";
    const body =
      runtime.activeAssistantTab === "info"
        ? runtime.assistantInfoTab(purpose)
        : runtime.activeAssistantTab === "model"
          ? runtime.assistantModelTab(purpose)
          : runtime.activeAssistantTab === "prompt"
            ? runtime.assistantPromptTab(purpose)
            : runtime.assistantStatsTab(purpose);
    const showNote =
      runtime.activeAssistantTab === "info" ||
      runtime.activeAssistantTab === "stats" ||
      runtime.activeAssistantTab === "model";
    return `<header class="dt-head">${runtime.assistantIcon(purpose)}<div class="grow" style="min-width:0"><h3>${runtime.esc(task ? runtime.assistantName(purpose) : d.title)}</h3><small class="muted">${runtime.esc(task ? runtime.assistantDesc(purpose) : d.description)}</small></div><span class="chip ${h.k}">${h.n}/3 model · ${h.t}</span></header>

    <div class="dt-tabs"><div class="tabs" role="tablist">${tabs.map(([t, l]) => `<button role="tab" aria-selected="${runtime.activeAssistantTab === t}" data-assistant-detail-tab="${t}">${l}</button>`).join("")}</div></div>

    <div class="pb dt-body">${body}${showNote ? runtime.profilesNote() : ""}</div>${runtime.activeAssistantTab === "stats" ? "" : runtime.assistantSaveBar()}`;
  }

  function renderAssistantSettings() {
    const host = document.querySelector("#assistant-config")!;
    const purpose = runtime.activeAssistantPurpose;
    if (!runtime.assistantDirty) {
      if (purpose === "global")
        runtime.assistantGlobalDraft = runtime.loadGlobalDraft();
      else runtime.assistantDraft = runtime.loadAssistantDraft(purpose);
    }
    const all = [...runtime.userAssistants(), "assistant_suggestion"];
    const issues = all.filter((p) => runtime.savedHealth(p).k !== "ok").length;
    const item = (p: string) => {
      const h = runtime.savedHealth(p),
        hidden = p !== "assistant_suggestion" && !runtime.profileOf(p).visible;
      return `<button class="tl-item" data-assistant-select="${runtime.esc(p)}" aria-current="${purpose === p}">${runtime.assistantIcon(p)}<span class="grow" style="min-width:0"><b>${runtime.esc(runtime.assistantName(p))}</b><small>${hidden ? "Đang ẩn · " : ""}${runtime.esc(runtime.purposeModel(p)?.assistant_name || "—")}</small></span><span class="dot ${h.k}" title="${h.t}"></span></button>`;
    };
    host.innerHTML = `<div class="as-cms">

    <aside class="panel tl">

      <button class="btn pri tl-create" id="assistant-create-open" ${runtime.assistantProfilesAvailable ? "" : 'disabled title="Backend chưa hỗ trợ tạo trợ lý"'}>${runtime.ico("plus")}Tạo trợ lý AI</button>

      <div class="tl-sum ${issues ? "warn" : "ok"}">${runtime.ico(issues ? "info" : "check")}<span>${issues ? `<b>${issues}/${all.length}</b> mục cần chú ý về model` : "Tất cả trợ lý đã đủ model"}</span></div>

      <div class="tl-grp">Cài đặt chung</div>

      <button class="tl-item" data-assistant-select="global" aria-current="${purpose === "global"}">${runtime.assistantIcon("global")}<span class="grow"><b>Prompt &amp; model chung</b><small>Áp dụng cho mọi trợ lý</small></span></button>

      <div class="tl-grp">Trợ lý hiển thị cho người dùng</div>

      ${runtime.userAssistants().map(item).join("")}

      <div class="tl-grp">Tác vụ nền</div>

      ${item("assistant_suggestion")}

      <div class="tl-legend"><span><i class="dot ok"></i>Đủ model</span><span><i class="dot warn"></i>Thiếu dự phòng</span><span><i class="dot bad"></i>Thiếu nghiêm trọng</span></div>

    </aside>

    <section class="panel tl-detail">${purpose === "global" ? runtime.assistantGlobalView() : runtime.assistantDetailView(purpose)}</section>

  </div>

  ${runtime.cmsModal("modal-assistant-model", "Sửa model của Trợ lý AI", "Model hiển thị", `<div class="fields"><label class="field">Tên hiển thị trên Assistant<input id="assistant-model-name"/></label><label class="field">Core Model ID trên Assistant<input id="assistant-model-core"/></label><label class="field">Thinking mode<select id="assistant-model-thinking"><option value="default">Theo mặc định gateway</option><option value="enabled">Bật</option><option value="disabled">Tắt</option></select></label><label class="field">Reasoning effort<select id="assistant-model-effort"><option value="default">Theo mặc định gateway</option><option value="low">Low</option><option value="high">High</option><option value="max">Max</option></select></label><label class="check full"><input id="assistant-model-enabled" type="checkbox"/> Cho phép chọn trên client</label></div>`, `<span class="statusText" id="assistant-model-editor-status">Không thay đổi Chat Bot AI</span><button class="btn" data-close>Hủy</button><button class="btn pri" id="save-assistant-model-editor">Lưu model</button>`, false)}

  <div class="scrim" id="modal-assistant-create" hidden><section class="dialog naDialog" role="dialog" aria-modal="true" aria-label="Tạo trợ lý AI"><header><h3>Tạo trợ lý AI</h3><button class="iconbtn" data-close aria-label="Đóng">${runtime.ico("cross-small")}</button></header><div class="body" id="assistant-create-body"></div><footer><span class="statusText" id="assistant-create-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="assistant-create-save">${runtime.ico("plus")}Tạo trợ lý</button></footer></section></div>`;
    runtime.bindAssistantSettings();
  }

  function markAssistantDirty() {
    if (runtime.assistantDirty) return;
    runtime.assistantDirty = true;
    const bar = document.querySelector<HTMLElement>(
      "#assistant-config .savebar",
    );
    if (!bar) return;
    bar.classList.add("on");
    bar.querySelector("#assistant-save-status")!.innerHTML =
      `${runtime.ico("info")} Có thay đổi chưa lưu`;
    bar
      .querySelectorAll<HTMLButtonElement>("button")
      .forEach((b) => (b.disabled = false));
  }

  function confirmLeaveAssistant() {
    return !runtime.assistantDirty || confirm("Bỏ các thay đổi chưa lưu?");
  }

  function refreshAssistantPreview() {
    const d = runtime.assistantDraft!,
      purpose = runtime.activeAssistantPurpose,
      host = document.querySelector("#assistant-config")!;
    const preview = host.querySelector("#assistant-preview");
    if (preview)
      preview.innerHTML =
        purpose === "assistant_general"
          ? `<div class="pv-gen">${runtime.assistantFace(purpose, 44)}<div><b>${runtime.esc(d.title)}</b><p class="muted" style="font-size:13px;margin:0">${runtime.esc(d.description)}</p></div></div>`
          : runtime.assistantCardPreview({
              face: runtime.assistantFace(purpose, 44),
              illustration: runtime.assistantIllustration(purpose),
              title: d.title,
              description: d.description,
              requests: runtime.profileOf(purpose).stats?.requests || 0,
              hidden: !d.visible,
            });
    const starters = host.querySelector(".asPreviewStarters");
    if (starters)
      starters.innerHTML = d.starters
        .split("\n")
        .map((x) => x.trim())
        .filter(Boolean)
        .slice(0, 4)
        .map(
          (t) =>
            `<button tabindex="-1" type="button">${runtime.esc(t)}</button>`,
        )
        .join("");
    const count = host.querySelector("#assistant-desc-count");
    if (count) count.textContent = `${d.description.length}/80 ký tự`;
    const head = host.querySelector(".dt-head h3"),
      sub = host.querySelector(".dt-head small");
    if (head && purpose !== "assistant_suggestion") head.textContent = d.title;
    if (sub && purpose !== "assistant_suggestion")
      sub.textContent = d.description;
  }

  function bindAssistantSettings() {
    const host = document.querySelector("#assistant-config")!;
    const on = <T extends HTMLElement>(
      sel: string,
      ev: string,
      fn: (el: T) => void,
    ) =>
      host
        .querySelectorAll<T>(sel)
        .forEach((el) => el.addEventListener(ev, () => fn(el)));
    on<HTMLButtonElement>("[data-assistant-select]", "click", (el) => {
      if (
        el.dataset.assistantSelect === runtime.activeAssistantPurpose ||
        !runtime.confirmLeaveAssistant()
      )
        return;
      runtime.assistantDirty = false;
      runtime.activeAssistantPurpose = el.dataset.assistantSelect!;
      runtime.activeAssistantTab =
        runtime.activeAssistantPurpose === "assistant_suggestion"
          ? "model"
          : "info";
      runtime.renderAssistantSettings();
    });
    on<HTMLButtonElement>("[data-assistant-detail-tab]", "click", (el) => {
      runtime.activeAssistantTab = el.dataset
        .assistantDetailTab as AssistantTab;
      runtime.renderAssistantSettings();
    });
    // Cài đặt chung
    on<HTMLTextAreaElement>("#assistant-global-prompt", "input", (el) => {
      runtime.assistantGlobalDraft!.prompt = el.value;
      host.querySelector("#assistant-global-count")!.textContent =
        `${el.value.length} ký tự`;
      runtime.markAssistantDirty();
    });
    on<HTMLInputElement>("[data-assistant-enable]", "change", (el) => {
      runtime.assistantGlobalDraft!.enabled[el.dataset.assistantEnable!] =
        el.checked;
      runtime.markAssistantDirty();
    });
    on<HTMLButtonElement>("[data-assistant-edit-model]", "click", (el) =>
      runtime.openAssistantModelEditor(el.dataset.assistantEditModel!),
    );
    // Hiển thị & tham số
    on<HTMLInputElement | HTMLTextAreaElement>(
      "[data-assistant-field]",
      "input",
      (el) => {
        const d = runtime.assistantDraft! as unknown as Record<string, unknown>,
          key = el.dataset.assistantField!;
        if (el instanceof HTMLInputElement && el.type === "checkbox")
          d[key] = el.checked;
        else if (
          el instanceof HTMLInputElement &&
          (el.type === "range" || el.type === "number")
        )
          d[key] = Number(el.value);
        else d[key] = el.value;
        runtime.refreshAssistantPreview();
        runtime.markAssistantDirty();
      },
    );
    // Chuỗi model
    (["main", "f1", "f2"] as const).forEach((field) =>
      on<HTMLSelectElement>(`#assistant-slot-${field}`, "change", (el) => {
        const d = runtime.assistantDraft!,
          purpose = runtime.activeAssistantPurpose;
        d[field] = el.value;
        const model = runtime.models.find((m) => m.id === el.value);
        if (field === "main")
          d.prompt = runtime.assistantPromptOf(model, purpose + "_instruction");
        if (field === "f1")
          d.fp1 = runtime.assistantPromptOf(
            model,
            purpose + "_fallback_instruction",
          );
        if (field === "f2")
          d.fp2 = runtime.assistantPromptOf(
            model,
            purpose + "_fallback_2_instruction",
          );
        runtime.markAssistantDirty();
        runtime.renderAssistantSettings();
      }),
    );
    // Prompt
    const updateMainPrompt = (value: string) => {
      runtime.assistantDraft!.prompt = value;
      host.querySelector("#assistant-prompt-count")!.textContent =
        `${value.length} ký tự`;
      host.querySelector("#assistant-prompt-preview")!.innerHTML =
        runtime.assistantPromptPreview(runtime.activeAssistantPurpose, value);
      runtime.markAssistantDirty();
    };
    on<HTMLTextAreaElement>("#assistant-prompt-main", "input", (el) =>
      updateMainPrompt(el.value),
    );
    on<HTMLButtonElement>("[data-assistant-var]", "click", (el) => {
      const area = host.querySelector<HTMLTextAreaElement>(
        "#assistant-prompt-main",
      )!;
      const at = area.selectionStart ?? area.value.length;
      area.value =
        area.value.slice(0, at) +
        el.dataset.assistantVar +
        area.value.slice(area.selectionEnd ?? at);
      area.focus();
      updateMainPrompt(area.value);
    });
    on<HTMLTextAreaElement>("#assistant-prompt-f1", "input", (el) => {
      runtime.assistantDraft!.fp1 = el.value;
      runtime.markAssistantDirty();
    });
    on<HTMLTextAreaElement>("#assistant-prompt-f2", "input", (el) => {
      runtime.assistantDraft!.fp2 = el.value;
      runtime.markAssistantDirty();
    });
    // Thanh lưu
    on<HTMLButtonElement>("#assistant-discard", "click", () => {
      runtime.assistantDirty = false;
      runtime.renderAssistantSettings();
    });
    on<HTMLButtonElement>(
      "#assistant-save",
      "click",
      () => void runtime.saveAssistantSettings(),
    );
    on<HTMLButtonElement>(
      "#save-assistant-model-editor",
      "click",
      () => void runtime.saveAssistantModelEditor(),
    );
    // Tạo trợ lý mới
    on<HTMLButtonElement>("#assistant-create-open", "click", () =>
      runtime.openAssistantCreate(),
    );
    on<HTMLButtonElement>(
      "#assistant-create-save",
      "click",
      () => void runtime.createAssistant(),
    );
  }

  function openAssistantModelEditor(id: string) {
    const model = runtime.models.find((x) => x.id === id);
    if (!model) return;
    runtime.editingAssistantModel = id;
    const value = (sel: string, v: string) =>
      ((
        document.querySelector(sel) as HTMLInputElement | HTMLSelectElement
      ).value = v);
    value("#assistant-model-name", model.assistant_name);
    value("#assistant-model-core", model.assistant_model_id);
    value(
      "#assistant-model-thinking",
      model.assistant_thinking_mode || "default",
    );
    value(
      "#assistant-model-effort",
      model.assistant_reasoning_effort || "default",
    );
    document.querySelector<HTMLInputElement>(
      "#assistant-model-enabled",
    )!.checked = model.assistant_enabled;
    runtime.openCmsModal("modal-assistant-model");
  }

  async function saveAssistantModelEditor() {
    const status = document.querySelector("#assistant-model-editor-status")!;
    if (!runtime.editingAssistantModel) return;
    status.textContent = "Đang lưu…";
    mountLoadingCat(status, "inline");
    status.className = "statusText";
    const field = (sel: string) =>
      (document.querySelector(sel) as HTMLInputElement | HTMLSelectElement)
        .value;
    try {
      await runtime.request(
        `/v1/admin/assistant-models/${runtime.editingAssistantModel}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            name: field("#assistant-model-name"),
            model_id: field("#assistant-model-core"),
            enabled: document.querySelector<HTMLInputElement>(
              "#assistant-model-enabled",
            )!.checked,
            thinking_mode: field("#assistant-model-thinking"),
            reasoning_effort: field("#assistant-model-effort"),
          }),
        },
      );
      runtime.models = await runtime.request<ModelConfig[]>("/v1/admin/models");
      runtime.assistantDirty = false;
      runtime.renderAssistantSettings();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  async function saveAssistantSettings() {
    const status = document.querySelector<HTMLElement>(
      "#assistant-save-status",
    );
    if (status) status.textContent = "Đang lưu…";
    try {
      if (runtime.activeAssistantPurpose === "global") {
        const g = runtime.assistantGlobalDraft!;
        runtime.settings = await runtime.request<Settings>(
          "/v1/admin/settings",
          {
            method: "PUT",
            body: JSON.stringify({ assistant_system_instruction: g.prompt }),
          },
        );
        for (const model of runtime.models.filter(
          (m) => g.enabled[m.id] !== m.assistant_enabled,
        ))
          await runtime.request(`/v1/admin/assistant-models/${model.id}`, {
            method: "PATCH",
            body: JSON.stringify({
              name: model.assistant_name,
              model_id: model.assistant_model_id,
              enabled: g.enabled[model.id],
              thinking_mode: model.assistant_thinking_mode,
              reasoning_effort: model.assistant_reasoning_effort,
            }),
          });
      } else {
        const d = runtime.assistantDraft!,
          purpose = runtime.activeAssistantPurpose;
        await runtime.request(
          `/v1/admin/assistant-purposes/${encodeURIComponent(purpose)}`,
          {
            method: "PUT",
            body: JSON.stringify({
              primary_model_id: d.main || null,
              fallback_model_id: d.f1 || null,
              fallback_2_model_id: d.f2 || null,
              primary_prompt: d.prompt,
              fallback_prompt: d.fp1,
              fallback_2_prompt: d.fp2,
            }),
          },
        );
        if (runtime.assistantProfilesAvailable)
          await runtime.request(
            `/v1/admin/assistant-profiles/${encodeURIComponent(purpose)}`,
            {
              method: "PUT",
              body: JSON.stringify({
                title: d.title,
                slogan: d.slogan,
                description: d.description,
                greeting: d.greeting,
                starters: d.starters
                  .split("\n")
                  .map((x) => x.trim())
                  .filter(Boolean)
                  .slice(0, 4),
                visible: d.visible,
                user_pick: d.user_pick,
              }),
            },
          );
      }
      runtime.models = await runtime.request<ModelConfig[]>("/v1/admin/models");
      await runtime.loadAssistantProfiles();
      runtime.assistantDirty = false;
      runtime.renderModels();
      runtime.renderSettings();
      runtime.renderAssistantSettings();
    } catch (error) {
      if (status) {
        status.textContent = String(error);
        status.className = "statusText error";
      }
    }
  }

  function renderAssistantCreate() {
    const f = runtime.newAssistant,
      body = document.querySelector("#assistant-create-body")!;
    const options = (selected: string, empty: string, enabledOnly: boolean) =>
      `<option value="">${empty}</option>${runtime.models
        .filter((m) => !enabledOnly || m.assistant_enabled)
        .map(
          (m) =>
            `<option value="${runtime.esc(m.id)}" ${m.id === selected ? "selected" : ""} ${m.assistant_enabled ? "" : "disabled"}>${runtime.esc(m.assistant_name || m.name)}${m.assistant_enabled ? "" : " (đang ẩn)"}</option>`,
        )
        .join("")}`;
    body.innerHTML = `<div class="na-grid">

    <div class="stack" style="gap:14px">

      <div class="dt-t"><b>1. Thông tin hiển thị</b><small>Người dùng thấy ở mục Trợ lý cá nhân</small></div>

      <div class="form-grid">

        <label class="field"><span>Tên trợ lý *</span><input class="input" data-na="title" value="${runtime.esc(f.title)}" placeholder="VD: Ngoại ngữ"></label>

        <label class="field"><span>Slogan</span><input class="input" data-na="slogan" value="${runtime.esc(f.slogan)}" placeholder="VD: Mỗi ngày một câu"></label>

        <label class="field full"><span>Mô tả ngắn *</span><input class="input" data-na="description" maxlength="80" value="${runtime.esc(f.description)}" placeholder="VD: Luyện nói và sửa lỗi tiếng Anh"><small class="tnum" id="na-desc-count">${f.description.length}/80</small></label>

        <label class="field full"><span>Lời chào khi mở phòng</span><textarea class="input" rows="2" data-na="greeting">${runtime.esc(f.greeting)}</textarea></label>

      </div>

      <div class="field"><span>Biểu tượng minh họa</span><div class="pick-row">${runtime.ASSISTANT_ICONS.map(([k, l]) => `<button type="button" class="ipick" data-na-icon="${k}" aria-pressed="${f.icon === k}" title="${l}">${runtime.ico(k)}</button>`).join("")}</div></div>

      <div class="field"><span>Màu chủ đạo</span><div class="pick-row">${runtime.ASSISTANT_HUES.map((h) => `<button type="button" class="cpick" data-na-hue="${h}" aria-pressed="${f.hue === h}" style="background:hsl(${h} 55% 52%)" aria-label="Màu ${h}"></button>`).join("")}<button type="button" class="btn sm ghost" id="na-hair">${runtime.ico("refresh")}Đổi ảnh đại diện</button></div></div>

      <div class="dt-t" style="margin-top:6px"><b>2. Model &amp; prompt</b><small>Có thể cấu hình chi tiết sau khi tạo</small></div>

      <div class="form-grid">

        <label class="field"><span>Model chính *</span><select class="input" data-na-select="main">${options(f.main, "— Chọn model —", false)}</select></label>

        <label class="field"><span>Dự phòng 1</span><select class="input" data-na-select="f1">${options(f.f1, "— Chưa chọn —", true)}</select></label>

        <label class="field full"><span>Prompt riêng *</span><textarea class="input mono" rows="3" data-na="prompt" placeholder="Vai trò, giọng điệu, giới hạn của trợ lý…">${runtime.esc(f.prompt)}</textarea></label>

        <label class="switchRow full"><span><b>Hiển thị ngay trên trang chủ</b><br><small class="muted">Tắt nếu muốn hoàn thiện cấu hình trước khi ra mắt</small></span><input type="checkbox" class="switch" id="na-visible" ${f.visible ? "checked" : ""}></label>

      </div>

    </div>

    <div class="stack na-pv" style="gap:10px"><div class="dt-t"><b>Xem trước</b><small>Thẻ trên trang chủ Trợ lý AI</small></div><div id="na-preview"></div></div>

  </div>`;
    const refresh = () => {
      body.querySelector("#na-preview")!.innerHTML =
        runtime.assistantCardPreview({
          face: faceSvg(f.hue, HAIRS[f.hair], 44),
          illustration: illustrationHtml("custom", f.hue, f.icon),
          title: f.title || "Trợ lý mới",
          description: f.description,
          requests: 0,
          hidden: !f.visible,
        });
      body.querySelector("#na-desc-count")!.textContent =
        `${f.description.length}/80`;
    };
    refresh();
    body
      .querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("[data-na]")
      .forEach((el) =>
        el.addEventListener("input", () => {
          (f as unknown as Record<string, string>)[el.dataset.na!] = el.value;
          refresh();
        }),
      );
    body.querySelectorAll<HTMLSelectElement>("[data-na-select]").forEach((el) =>
      el.addEventListener("change", () => {
        (f as unknown as Record<string, string>)[el.dataset.naSelect!] =
          el.value;
      }),
    );
    body
      .querySelector<HTMLInputElement>("#na-visible")!
      .addEventListener("change", (e) => {
        f.visible = (e.target as HTMLInputElement).checked;
        refresh();
      });
    body.querySelectorAll<HTMLButtonElement>("[data-na-icon]").forEach((el) =>
      el.addEventListener("click", () => {
        f.icon = el.dataset.naIcon!;
        runtime.renderAssistantCreate();
      }),
    );
    body.querySelectorAll<HTMLButtonElement>("[data-na-hue]").forEach((el) =>
      el.addEventListener("click", () => {
        f.hue = Number(el.dataset.naHue);
        runtime.renderAssistantCreate();
      }),
    );
    body.querySelector("#na-hair")!.addEventListener("click", () => {
      f.hair = (f.hair + 1) % HAIRS.length;
      refresh();
    });
  }

  function openAssistantCreate() {
    runtime.newAssistant = {
      title: "",
      slogan: "",
      description: "",
      greeting: "",
      icon: "sparkles",
      hue: 172,
      hair: 0,
      main: "",
      f1: "",
      prompt: "",
      visible: true,
    };
    const status = document.querySelector("#assistant-create-status")!;
    status.textContent = "";
    status.className = "statusText";
    runtime.renderAssistantCreate();
    runtime.openCmsModal("modal-assistant-create");
  }

  async function createAssistant() {
    const f = runtime.newAssistant,
      status = document.querySelector("#assistant-create-status")!;
    const missing = !f.title.trim()
      ? "Nhập tên trợ lý."
      : !f.description.trim()
        ? "Nhập mô tả ngắn."
        : !f.main
          ? "Chọn model chính."
          : !f.prompt.trim()
            ? "Nhập prompt riêng."
            : "";
    status.className = missing ? "statusText error" : "statusText";
    if (missing) return void (status.textContent = missing);
    status.textContent = "Đang tạo…";
    try {
      const created = await runtime.request<{
        id: string;
      }>("/v1/admin/assistant-profiles", {
        method: "POST",
        body: JSON.stringify({
          title: f.title.trim(),
          slogan: f.slogan,
          description: f.description.trim(),
          greeting: f.greeting,
          icon: f.icon,
          hue: f.hue,
          hair: f.hair,
          visible: f.visible,
        }),
      });
      await runtime.request(
        `/v1/admin/assistant-purposes/${encodeURIComponent(created.id)}`,
        {
          method: "PUT",
          body: JSON.stringify({
            primary_model_id: f.main,
            fallback_model_id: f.f1 || null,
            fallback_2_model_id: null,
            primary_prompt: f.prompt,
            fallback_prompt: "",
            fallback_2_prompt: "",
          }),
        },
      );
      runtime.models = await runtime.request<ModelConfig[]>("/v1/admin/models");
      await runtime.loadAssistantProfiles();
      (
        document.querySelector("#modal-assistant-create") as HTMLElement
      ).hidden = true;
      runtime.assistantDirty = false;
      runtime.activeAssistantPurpose = created.id;
      runtime.activeAssistantTab = "info";
      runtime.renderAssistantSettings();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  return {
    loadAssistantProfiles,
    loadAssistantDraft,
    loadGlobalDraft,
    assistantHealth,
    assistantFace,
    assistantIllustration,
    assistantCardPreview,
    assistantSaveBar,
    assistantModelSelect,
    assistantGlobalView,
    assistantInfoTab,
    assistantModelTab,
    assistantPromptPreview,
    assistantPromptTab,
    assistantStatsTab,
    assistantDetailView,
    renderAssistantSettings,
    markAssistantDirty,
    confirmLeaveAssistant,
    refreshAssistantPreview,
    bindAssistantSettings,
    openAssistantModelEditor,
    saveAssistantModelEditor,
    saveAssistantSettings,
    renderAssistantCreate,
    openAssistantCreate,
    createAssistant,
  };
}
