import {renderActionSounds} from "./admin/actionSounds";
import {bindReactionSounds,refreshReactionSounds} from "./admin/reactionSounds";
import {setApiVoices,refreshVoiceSources} from "./admin/voiceSources";
import { bindVoiceSettings, fillVoiceSettings, voiceSettings } from "./admin/voiceSettings";
import { bindVoiceClone, refreshVoiceClone } from "./admin/voiceClone";
import "./admin-styles.css";
import { mountLoadingCat } from "./roleplay/loadingCatDom";
import type { Overview, Settings, CredentialState, AccessControl, DbRows, AdminCharacter, CharacterCatalog, DbTable, ModelConfig, ExpressionPreview, ModelUpdate } from "./admin/types";
import { renderBackgroundMusic } from "./admin/music";
import { createCmsLogViews } from "./admin/logs";
import { HAIRS, faceSvg, illustrationHtml, personaFaceSvg } from "./persona";
document.documentElement.dataset.app = "admin";
const root = document.querySelector<HTMLDivElement>("#admin-root")!;
root.innerHTML = `<div class="adminShell"><aside class="adminSide"><div class="adminBrand"><span class="logo">CMS</span><span>Avibi CMS<small>Quản trị nền tảng</small></span></div><nav class="adminNav"><div class="adminNavGroup"><span>Tổng quan</span><button class="active" data-view="dashboard"><i class="fi-rr-apps vi" aria-hidden="true"></i>Tổng quan</button></div><div class="adminNavGroup"><span>Nội dung</span><button class="" data-view="content"><i class="fi-rr-users-alt vi" aria-hidden="true"></i>Nhân vật</button><button data-view="action-sounds"><i class="fi-rr-volume vi" aria-hidden="true"></i>Âm hành động</button><button data-view="background-music"><i class="fi-rr-music-alt vi" aria-hidden="true"></i>Nhạc nền</button><button class="" data-view="home-sections"><i class="fi-rr-apps-sort vi" aria-hidden="true"></i>Danh mục trang chủ</button><button class="" data-view="assistant-config"><i class="fi-rr-sparkles vi" aria-hidden="true"></i>Trợ lý AI</button></div><div class="adminNavGroup"><span>AI & model</span><button class="" data-view="models"><i class="fi-rr-settings-sliders vi" aria-hidden="true"></i>Cấu hình AI</button><button class="" data-view="settings"><i class="fi-rr-shuffle vi" aria-hidden="true"></i>Phân công model</button></div><div class="adminNavGroup"><span>Giám sát</span><button class="" data-view="conversations"><i class="fi-rr-comment-alt vi" aria-hidden="true"></i>Logchat</button><button data-view="voice-logs"><i class="fi-rr-volume vi" aria-hidden="true"></i>Log voice</button><button class="" data-view="action-logs"><i class="fi-rr-time-past vi" aria-hidden="true"></i>Nhật ký hoạt động</button></div><div class="adminNavGroup"><span>Hệ thống</span><button class="" data-view="access"><i class="fi-rr-shield-check vi" aria-hidden="true"></i>Truy cập</button><button class="" data-view="database"><i class="fi-rr-database vi" aria-hidden="true"></i>Database</button></div></nav><div class="adminMeta mono faint">Khu vực quản trị riêng · tài khoản admin</div></aside><main class="adminMain"><div class="top"><div><h1 id="page-title">Tổng quan sản phẩm</h1><p id="page-subtitle">Sức khỏe hệ thống và nội dung sản phẩm</p></div><div class="topActions"><a class="btn" href="/role-play-ai" style="text-decoration:none"><i class="fi-rr-arrow-up-right-from-square vi" aria-hidden="true"></i>Mở Chat Bot AI</a><button class="btn" id="refresh"><i class="fi-rr-refresh vi" aria-hidden="true"></i>Làm mới</button></div></div><section class="view active" id="dashboard"></section><section class="view" id="content"></section><section class="view" id="action-sounds"></section><section class="view" id="background-music"></section><section class="view" id="home-sections"></section><section class="view" id="assistant-config"></section><section class="view" id="models"></section><section class="view" id="settings"></section><section class="view" id="conversations"></section><section class="view" id="voice-logs"></section><section class="view" id="action-logs"></section><section class="view" id="access"></section><section class="view" id="database"></section></main></div>`;
let overview: Overview | null = null;
let settings: Settings | null = null;
let accessControl: AccessControl | null = null;
let characterCatalog: CharacterCatalog = {
    preset_catalog: [],
    user_characters: [],
};
let credentials: CredentialState | null = null;
let adminCharacters: AdminCharacter[] = [];
let models: ModelConfig[] = [];
let dbTables: DbTable[] = [];
let activeDbTable = "users";
const esc = (value: unknown) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]!);
const vietnamLogTime = new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});
function formatVietnamLogTime(value: unknown): string {
    const raw = String(value ?? "").trim();
    if (!raw)
        return "";
    // Older database rows may omit the offset even though they were stored in UTC.
    const timestamp = new Date(/^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/i.test(raw) ? raw : `${raw}Z`);
    return Number.isNaN(timestamp.getTime()) ? raw : vietnamLogTime.format(timestamp);
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(path, {
        ...init,
        headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    if (!response.ok) {
        const body=await response.text();
        try {
            const detail=JSON.parse(body).detail;
            if(detail&&typeof detail==="object"&&String(detail.code||"").startsWith("character_policy_"))
                throw new Error(String(detail.message||"Không thể kiểm duyệt nhân vật."));
        } catch(error) {
            if(error instanceof Error&&error.name!=="SyntaxError")throw error;
        }
        throw new Error(response.status === 401
            ? "Bạn chưa đăng nhập CMS hoặc phiên đăng nhập đã hết." : body);
    }
    return response.json();
}
function showGenerationNotice(plan: NonNullable<ModelUpdate["expression_generation"]>) {
    const message = plan.images
        ? `Đã lưu model ảnh. Hệ thống sẽ tạo ${plan.images} ảnh cho ${plan.unique_sources} nguồn avatar duy nhất, tương ứng ${plan.characters} nhân vật. Nhân vật không có avatar và bộ đã đủ 6 ảnh không được tính.`
        : `Đã lưu model ảnh. Không có nhân vật có avatar nào thiếu bộ 6 ảnh, vì vậy model ảnh sẽ không được gọi.`;
    let notice = document.querySelector<HTMLDivElement>("#expression-generation-notice");
    if (!notice) {
        notice = document.createElement("div");
        notice.id = "expression-generation-notice";
        notice.className = "generationNotice";
        document.body.appendChild(notice);
    }
    notice.innerHTML = `<b>Tạo ảnh biểu cảm</b><span>${esc(message)}</span><button aria-label="Đóng">×</button>`;
    notice.classList.add("show");
    notice
        .querySelector("button")
        ?.addEventListener("click", () => notice?.classList.remove("show"));
    window.setTimeout(() => notice?.classList.remove("show"), 15000);
    window.sessionStorage.setItem("expression_generation_notice", message);
}
const ROLE_LABELS: Record<string, string> = { companion: "Đồng hành", study: "Học tập", work: "Công việc", entertainment: "Giải trí", romance: "Tình cảm", roleplay: "Role play" };
const fmtNumber = (value: number | undefined) => (value ?? 0).toLocaleString("vi-VN");
const fmtTime = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
};
const initialAvatar = (name: string, size = 26) => `<span class="ovAvatar" style="width:${size}px;height:${size}px;font-size:${Math.round(size * 0.42)}px">${esc((name || "?").trim()[0]?.toUpperCase() || "?")}</span>`;
function renderDashboard() {
    if (!overview)
        return;
    const s = overview.stats;
    const kpis = [
        ["Người dùng", "users"],
        ["Nhân vật", "characters"],
        ["Phòng chat", "rooms"],
        ["Tin nhắn", "messages"],
        ["Ký ức", "memories"],
    ]
        .map(([label, key]) => {
        const delta = s[`${key}_delta`];
        return `<div class="kpi"><span>${label}</span><b>${fmtNumber(s[key])}</b><small${delta ? "" : ' class="faint"'}>${delta ? `+${fmtNumber(delta)} tuần này` : "toàn hệ thống"}</small></div>`;
    })
        .join("");
    const hasUsage = overview.characters.some((c) => typeof c.usage_count === "number");
    const top = [...overview.characters].sort((a, b) => (b.usage_count || 0) - (a.usage_count || 0)).slice(0, 10);
    const maxUsage = Math.max(1, ...top.map((c) => c.usage_count || 0));
    const topRows = top
        .map((c, i) => `<tr><td class="num faint">${i + 1}</td><td><div class="row ovName">${c.avatar_url ? `<img class="ovAvatar" src="${esc(c.avatar_url)}" alt="">` : initialAvatar(c.name)}<span>${esc(c.name)}</span></div></td><td>${esc(ROLE_LABELS[c.role] || ROLE_LABELS[c.category] || c.role || "—")}</td><td>${hasUsage ? `<div class="bar-mini"><i style="width:${Math.round(((c.usage_count || 0) / maxUsage) * 80)}px"></i><span class="tnum">${fmtNumber(c.usage_count)}</span></div>` : `<span class="faint">${esc(c.category === "entertainment" ? "Giải trí" : "Hữu ích")}</span>`}</td></tr>`)
        .join("");
    const docRows = overview.documents
        .slice(0, 6)
        .map((d) => {
        const kind = d.status === "ready" ? "ok" : d.status === "failed" ? "bad" : "warn";
        const label = d.status === "ready" ? "Sẵn sàng" : d.status === "failed" ? `Lỗi${d.error ? `: ${d.error}` : ""}` : "Đang xử lý";
        return `<tr><td class="mono">${esc(d.filename)}</td><td><span class="chip ${kind}">${esc(label)}</span></td></tr>`;
    })
        .join("");
    const charName = (id?: string) => overview!.characters.find((c) => c.id === id)?.name;
    const traceRows = overview.ai_activity
        .slice(0, 6)
        .map((a) => `<tr><td class="mono">${fmtTime(a.created_at)}</td><td>${esc(a.room || charName(a.character_id) || "—")}</td><td class="num">${a.layers}</td><td class="num">${a.memories}</td><td class="num">${a.documents}</td></tr>`)
        .join("");
    const table = (head: string, rows: string, empty: string, cols: number) => `<div class="tbl-wrap"><table class="dt"><thead><tr>${head}</tr></thead><tbody>${rows || `<tr><td colspan="${cols}"><div class="empty">${empty}</div></td></tr>`}</tbody></table></div>`;
    document.querySelector("#dashboard")!.innerHTML = `<div class="kpis">${kpis}</div>

  <div class="cols2 ovGrid">

    <section class="panel"><header><h3>10 nhân vật đầu</h3><span class="faint mono">${hasUsage ? "theo lượt dùng" : "mới cập nhật"}</span></header>

      ${table(`<th class="num">#</th><th>Nhân vật</th><th>Loại</th><th>${hasUsage ? "Lượt dùng" : "Nhóm"}</th>`, topRows, "Chưa có nhân vật.", 4)}</section>

    <div class="stack" style="gap:14px">

      <section class="panel"><header><h3>Tài liệu</h3></header><div class="pb">

        <div class="row"><span class="chip ok">Sẵn sàng · ${fmtNumber(s.ready_documents)}</span><span class="chip bad">Lỗi · ${fmtNumber(s.failed_documents)}</span></div>

        ${table("<th>Tài liệu</th><th>Trạng thái</th>", docRows, "Chưa có tài liệu.", 2)}</div></section>

      <section class="panel"><header><h3>AI pipeline gần đây</h3></header>

        ${table('<th>Thời điểm</th><th>Phòng</th><th class="num">Lớp context</th><th class="num">Memory</th><th class="num">Tài liệu</th>', traceRows, "Chưa có hoạt động.", 5)}</section>

    </div>

  </div>`;
}
const CREATE_FIELDS = `<label class="field">Tên nhân vật<input id="new-character-name" placeholder="Ví dụ: Linh"/></label><label class="field">Vai trò<input id="new-character-role" value="companion" placeholder="companion, study, work..."/></label><label class="field">Nhóm<select id="new-character-category"><option value="utility">Hữu ích</option><option value="entertainment">Giải trí</option></select></label><label class="field">Ảnh nhân vật<input type="file" id="new-character-avatar" accept="image/png,image/jpeg,image/webp,image/gif"/><span class="hint">JPG, PNG, WEBP hoặc GIF · tối đa 5 MB</span></label><label class="field full">Mô tả<textarea id="new-character-description"></textarea></label><label class="field full">System prompt<textarea class="largePrompt" id="new-character-prompt"></textarea></label><label class="field full">Lời chào đầu tiên<textarea id="new-character-greeting"></textarea></label>`;
const EDIT_FIELDS = `<label class="field full">Chọn nhân vật<select id="character-select"></select></label><label class="field full" id="home-section-field">Vị trí trên trang chủ<select id="character-home-section"><option value="auto">Hiện trong Nhân vật hệ thống</option><option value="hidden">Ẩn khỏi trang chủ</option></select><span class="hint">Chỉ áp dụng cho nhân vật hệ thống do admin quản lý.</span></label><label class="field">Tên<input id="character-name"/></label><label class="field">Vai trò<input id="character-role"/></label><label class="field full">Mô tả<textarea id="character-description"></textarea></label><label class="field full">System prompt riêng<textarea class="largePrompt" id="character-system-prompt"></textarea></label><label class="field full">Scenario<textarea id="character-scenario"></textarea></label><label class="field full">Lời chào đầu tiên<textarea id="character-greeting"></textarea></label><label class="field full">Thay Ảnh nhân vật<input type="file" id="character-avatar-file" accept="image/png,image/jpeg,image/webp,image/gif"/><span class="hint">Để trống nếu muốn giữ ảnh hiện tại.</span></label><label class="field">Goals, mỗi dòng một mục<textarea id="character-goals"></textarea></label><label class="field">Behavior rules, mỗi dòng một mục<textarea id="character-rules"></textarea></label>`;
let contentSource: "preset" | "user" = "preset";
let contentQuery = "";
const ico = (name: string) => `<i class="fi-rr-${name} vi" aria-hidden="true"></i>`;
function cmsModal(id: string, title: string, eyebrow: string, body: string, footer: string, wide = true) {
    return `<div class="scrim" id="${id}" hidden><section class="dialog${wide ? " wide" : ""}" role="dialog" aria-modal="true"><header><div><span class="eyebrow">${eyebrow}</span><h2>${title}</h2></div><button class="iconbtn" data-close aria-label="Đóng">${ico("cross-small")}</button></header><div class="body">${body}</div><footer>${footer}</footer></section></div>`;
}
function openCmsModal(id: string) {
    const el = document.getElementById(id);
    if (!el)
        return;
    el.hidden = false;
    el.classList.add("enter");
    setTimeout(() => el.classList.remove("enter"), 200);
}
function closeCmsModal(el: Element | null) {
    if (el instanceof HTMLElement)
        el.hidden = true;
}
document.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const opener = target.closest<HTMLElement>("[data-open]");
    if (opener)
        return openCmsModal(opener.dataset.open!);
    if (target.closest("[data-close]"))
        return closeCmsModal(target.closest(".scrim"));
    if (target.classList.contains("scrim"))
        closeCmsModal(target);
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape")
        document.querySelectorAll<HTMLElement>(".scrim:not([hidden])").forEach((el) => (el.hidden = true));
});
/** Nút ẩn/hiện nhân vật hệ thống trên trang chủ (đổi home_section giữa "hidden" và "auto"). */
const visibilityButton = (x: AdminCharacter) =>
  x.home_section === "hidden"
    ? `<button class="btn sm" data-toggle-visibility="${esc(x.id)}" title="Hiện ${esc(x.spec.name)} trên trang chủ">${ico("eye")}Hiện</button>`
    : `<button class="btn sm" data-toggle-visibility="${esc(x.id)}" title="Ẩn ${esc(x.spec.name)} khỏi trang chủ">${ico("eye-crossed")}Ẩn</button>`;
async function toggleCharacterVisibility(button: HTMLButtonElement) {
  const item = adminCharacters.find((x) => x.id === button.dataset.toggleVisibility);
  if (!item?.spec.preset_type) return;
  const next = item.home_section === "hidden" ? "auto" : "hidden";
  button.disabled = true;
  try {
    await request(`/v1/admin/presets/${encodeURIComponent(item.spec.preset_type)}/home-section`, {
      method: "PUT",
      body: JSON.stringify({ home_section: next }),
    });
    item.home_section = next;
    document.querySelector("#cms-char-rows")!.innerHTML = contentRows();
  } catch (error) {
    button.disabled = false;
    button.title = error instanceof Error ? error.message : String(error);
    button.textContent = "Lỗi, thử lại";
  }
}
function contentRows() {
  const q = contentQuery.trim().toLowerCase();
  const list = adminCharacters.filter((x) => x.source === contentSource && (!q || `${x.spec.name} ${x.spec.identity.role} ${x.user_id || ""}`.toLowerCase().includes(q)));
  return list
    .map((x) => `<tr><td><span class="cmsCharCell">${x.spec.avatar_url ? `<img src="${esc(x.spec.avatar_url)}" alt=""/>` : `<b>${esc(x.spec.name.slice(0, 1))}</b>`}<span><strong>${esc(x.spec.name)}</strong><small>${esc((x.spec.description || "").slice(0, 70))}</small></span></span></td><td>${esc(x.spec.identity.role)}</td><td>${x.source === "preset" ? (x.home_section === "hidden" ? '<span class="chip">Ẩn</span>' : '<span class="chip accent">Hiển thị</span>') : `<small>User ${esc(x.user_id)}</small>`}</td><td>${esc(x.spec.tts_voice_mode==="separate" ? "VI: "+(x.spec.tts_voice_vi||"Auto")+" / EN: "+(x.spec.tts_voice_en||"Auto") : x.spec.tts_voice_id || "Mặc định")}</td><td class="num"><span class="cmsActions">${x.source === "preset" ? visibilityButton(x) : ""}<button class="btn sm" data-edit-character="${esc(x.id)}">${ico("edit")}Sửa</button></span></td></tr>`)
    .join("") || `<tr><td colspan="5"><div class="empty">Không có nhân vật phù hợp.</div></td></tr>`;
}
async function loadVbeeVoices() {
    const status = document.querySelector<HTMLElement>("#tts-voice-status");
    const list = document.querySelector<HTMLDataListElement>("#tts-voice-options");
    if (!status || !list)
        return;
    try {
        const result = await request<{
            voices: {
                id: string;
                name: string;
                gender: string;
                language: string;
            }[];
        }>("/v1/admin/tts/voices");
        if (!list.isConnected)
            return;
        setApiVoices(result.voices);
        list.innerHTML = result.voices.map((voice) => `<option value="${esc(voice.id)}" label="${esc(voice.name)} · ${voice.gender === "male" ? "Nam" : voice.gender === "female" ? "Nữ" : "Khác"} · ${esc(voice.language)}"></option>`).join("");
        status.textContent = `Đã tải ${result.voices.length} giọng từ API TTS. Để trống mã giọng để hệ thống tự chọn theo giới tính.`;
    }
    catch (error) {
        if(!list.isConnected)return;
        const message=error instanceof Error?error.message:"Không tải được danh sách giọng API TTS.";
        setApiVoices([],message);
        if (status.isConnected)status.textContent=message;
    }
}
function renderContent() {
    if (!overview)
        return;
    const options = adminCharacters.map((x) => `<option value="${esc(x.id)}">${esc(x.spec.name)}${x.source === "preset" ? " · Preset" : ` · User ${esc(x.user_id)}`}</option>`).join("");
    const editFields = EDIT_FIELDS.replace('<select id="character-select"></select>', `<select id="character-select">${options}</select>`);
    document.querySelector("#content")!.innerHTML =
        `<section class="panel wide cmsPanel"><div class="cmsToolbar"><div class="tabs" role="tablist"><button class="${contentSource === "preset" ? "active" : ""}" data-content-source="preset">Nhân vật hệ thống <b>${adminCharacters.filter((x) => x.source === "preset").length}</b></button><button class="${contentSource === "user" ? "active" : ""}" data-content-source="user">Do người dùng tạo <b>${adminCharacters.filter((x) => x.source === "user").length}</b></button></div><label class="cmsSearch">${ico("search")}<input id="cms-char-q" placeholder="Tìm theo tên, vai trò, user…" value="${esc(contentQuery)}"/></label><span class="cmsSpacer"></span><button class="btn" id="backfill-system-expressions" type="button">${ico("picture")}Bổ sung ảnh biểu cảm</button><button class="btn primary" data-open="modal-create-character">${ico("plus-small")}Tạo nhân vật</button></div><div class="cmsTable"><table><thead><tr><th>Nhân vật</th><th>Vai trò</th><th>Hiển thị</th><th>Giọng TTS</th><th class="num">Thao tác</th></tr></thead><tbody id="cms-char-rows">${contentRows()}</tbody></table></div></section>` +
            cmsModal("modal-create-character", "Tạo nhân vật hệ thống", "Nhân vật mới", `<div class="fields">${CREATE_FIELDS}</div>`, `<span class="statusText" id="new-character-status">Chưa tạo</span><button class="btn" data-close>Hủy</button><button class="btn primary" id="create-system-character">Tạo nhân vật</button>`) +
            cmsModal("modal-edit-character", "Sửa nhân vật", "Chỉnh sửa", `<div class="fields">${editFields}</div>`, `<span class="statusText" id="character-status">Chọn nhân vật để chỉnh sửa</span><button class="btn" data-close>Đóng</button><button class="btn primary" id="save-character">Lưu nhân vật</button>`);
    const select = document.querySelector<HTMLSelectElement>("#character-select");
    const selectField = select?.closest<HTMLElement>("label");
    if (selectField)
        selectField.style.display = "none";
    document.querySelectorAll<HTMLButtonElement>("[data-content-source]").forEach((b) => b.addEventListener("click", () => { contentSource = b.dataset.contentSource as "preset" | "user"; renderContent(); }));
    document.querySelector<HTMLInputElement>("#cms-char-q")?.addEventListener("input", (event) => { contentQuery = (event.target as HTMLInputElement).value; document.querySelector("#cms-char-rows")!.innerHTML = contentRows(); });
    document.querySelector("#cms-char-rows")?.addEventListener("click", (event) => {
        const toggle = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-toggle-visibility]");
        if (toggle) return void toggleCharacterVisibility(toggle);
        const btn = (event.target as HTMLElement).closest<HTMLElement>("[data-edit-character]");
        if (!btn || !select)
            return;
        select.value = btn.dataset.editCharacter!;
        fillCharacter();
        const item = currentCharacter();
        if (item)
            void loadExpressionPreview(item);
        const avatarFile = document.querySelector<HTMLInputElement>("#character-avatar-file");
        if (avatarFile)
            avatarFile.value = "";
        document.querySelector("#modal-edit-character h2")!.textContent = item ? `Sửa · ${item.spec.name}` : "Sửa nhân vật";
        openCmsModal("modal-edit-character");
    });
    document.querySelector("#character-greeting")?.closest("label")?.insertAdjacentHTML("afterend", '<label class="field">Giọng TTS<input id="character-tts-voice" list="tts-voice-options" maxlength="160" placeholder="Tự chọn theo giới tính"/><small>Để trống để tự chọn voice Vbee; nhập mã để dùng giọng riêng.</small></label><label class="field">Giới tính giọng<select id="character-tts-gender"><option value="unspecified">Tự nhận diện</option><option value="male">Nam</option><option value="female">Nữ</option></select><small>Dùng để tự chọn voice Vbee. Chọn rõ nếu nhân vật public chưa nhận diện đúng.</small></label>');
    document.querySelector("#new-character-greeting")?.closest("label")?.insertAdjacentHTML("afterend", '<label class="field">Giọng TTS<input id="new-character-tts-voice" list="tts-voice-options" maxlength="160" placeholder="Tự chọn theo giới tính"/></label><label class="field">Giới tính giọng<select id="new-character-tts-gender"><option value="unspecified">Tự nhận diện</option><option value="male">Nam</option><option value="female">Nữ</option></select></label>');
    document.querySelector<HTMLButtonElement>("#backfill-system-expressions")?.addEventListener("click", async (event) => {
        const button = event.currentTarget as HTMLButtonElement;
        button.disabled = true;
        try {
            const result = await request<{
                characters_queued: number;
                images_queued: number;
            }>("/v1/admin/system-characters/expressions/backfill", { method: "POST" });
            button.textContent = result.characters_queued ? `Đã xếp hàng ${result.characters_queued} nhân vật · ${result.images_queued} ảnh` : "Tất cả nhân vật có ảnh đã đủ biểu cảm";
            const selected = currentCharacter();
            if (selected)
                void loadExpressionPreview(selected);
        }
        catch (error) {
            button.textContent = error instanceof Error ? error.message : "Không thể tạo ảnh biểu cảm";
        }
        finally {
            button.disabled = false;
        }
    });
    document.querySelector("#content")?.insertAdjacentHTML("beforeend", '<datalist id="tts-voice-options"></datalist><p id="tts-voice-status" class="hint"></p>');
    void loadVbeeVoices();
    bindVoiceSettings(loadVbeeVoices);
    bindVoiceClone(currentCharacter, (value) => {
        refreshReactionSounds();
        const updated = value as AdminCharacter;
        adminCharacters = adminCharacters.map(item => item.id === updated.id ? {...item,...updated} : item);
        document.querySelector("#cms-char-rows")!.innerHTML = contentRows();
    }, loadVbeeVoices);
    bindReactionSounds(currentCharacter);
    bindCharacterEditor();
    bindAdminCreate();
}
function currentCharacter() {
    const id = document.querySelector<HTMLSelectElement>("#character-select")?.value;
    return adminCharacters.find((item) => item.id === id);
}
function fillCharacter() {
    const item = currentCharacter();
    if (!item)
        return;
    fillVoiceSettings(item.spec);
    refreshReactionSounds();
    const values: Record<string, string> = {
        "character-name": item.spec.name,
        "character-role": item.spec.identity.role,
        "character-description": item.spec.description,
        "character-system-prompt": item.spec.system_prompt,
        "character-scenario": item.spec.scenario,
        "character-greeting": item.spec.initial_greeting,
        "character-tts-voice": item.spec.tts_voice_id || "",
        "character-tts-gender": item.spec.tts_gender || "unspecified",
        "character-goals": item.spec.goals.join("\n"),
        "character-rules": item.spec.behavior_rules.join("\n"),
    };
    Object.entries(values).forEach(([id, value]) => {
        const input = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`);
        if (input)
            input.value = value;
    });
    refreshVoiceSources();
    refreshVoiceClone();
    const placement = document.querySelector<HTMLSelectElement>("#character-home-section");
    const placementField = document.querySelector<HTMLElement>("#home-section-field");
    if (placement)
        placement.value = item.home_section || "hidden";
    if (placementField)
        placementField.style.display = item.source === "preset" ? "grid" : "none";
    const status = document.querySelector("#character-status");
    if (status)
        status.textContent = `Đang sửa ${item.spec.name}`;
}
async function loadExpressionPreview(item: AdminCharacter, attempt = 0) {
    let host = document.querySelector<HTMLElement>("#character-expression-preview");
    if (!host) {
        const field = document
            .querySelector("#character-avatar-file")
            ?.closest("label");
        field?.insertAdjacentHTML("afterend", '<div id="character-expression-preview" class="expressionPreview"><span>Đang kiểm tra bộ ảnh biểu cảm…</span></div>');
        host = document.querySelector<HTMLElement>("#character-expression-preview");
    }
    if (!host)
        return;
    host.innerHTML = "<span>Đang kiểm tra bộ ảnh biểu cảm…</span>";
    mountLoadingCat(host, "compact");
    try {
        const data = await request<ExpressionPreview>(`/v1/admin/characters/${encodeURIComponent(item.id)}/expressions`);
        const labels: Record<string, string> = {
            neutral: "Bình thường",
            happy: "Vui",
            sad: "Buồn",
            angry: "Giận",
            surprised: "Bất ngờ",
            shy: "Ngại",
            thinking: "Suy nghĩ",
            laughing: "Cười",
            crying: "Khóc",
            winking: "Nháy mắt",
            playful: "Tinh nghịch",
        };
        const meaning: Record<string, string> = {
            queued: "Đang chờ tạo ảnh",
            processing: "Đang tạo ảnh",
            failed: "Tạo ảnh thất bại; kiểm tra model ảnh hoặc gateway",
            "no-image-model": "Chưa phân công model cho tác vụ tạo ảnh nhân vật",
            fallback: "Đã dùng bộ ảnh xử lý từ avatar vì model ảnh không trả kết quả",
            missing: "Chưa tải ảnh nguồn hoặc chưa có bộ biểu cảm",
        };
        host.innerHTML = `<div class="expressionPreviewHead"><b>Bộ ảnh biểu cảm</b><span>${esc(meaning[data.quality] || data.quality)}${data.error ? `: ${esc(data.error)}` : ""} · ${Object.keys(data.images).length}/6 ảnh</span></div><div class="expressionPreviewGrid">${Object.entries(data.images)
            .map(([emotion, url]) => `<figure><img src="${esc(url)}?v=${Date.now()}" alt="${esc(labels[emotion] || emotion)}"/><figcaption>${esc(labels[emotion] || emotion)}</figcaption></figure>`)
            .join("") || "<p>Chưa có ảnh được tạo.</p>"}</div>`;
        if ((data.status === "queued" || data.status === "processing") && attempt < 60)
            window.setTimeout(() => { if (currentCharacter()?.id === item.id)
                void loadExpressionPreview(item, attempt + 1); }, 3000);
    }
    catch (error) {
        host.innerHTML = `<span>Chưa có bộ ảnh: ${esc(error)}</span>`;
    }
}
function bindCharacterEditor() {
    const select = document.querySelector<HTMLSelectElement>("#character-select");
    if (!select)
        return;
    select.addEventListener("change", () => {
        fillCharacter();
        const item = currentCharacter();
        if (item)
            loadExpressionPreview(item);
    });
    document
        .querySelector("#save-character")
        ?.addEventListener("click", saveCharacter);
    fillCharacter();
    const item = currentCharacter();
    if (item)
        loadExpressionPreview(item);
}
async function saveCharacter() {
    const item = currentCharacter();
    const status = document.querySelector("#character-status");
    if (!item || !status)
        return;
    status.textContent = "Đang lưu…";
    mountLoadingCat(status, "inline");
    status.className = "statusText";
    const value = (id: string) => document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`)!
        .value;
    try {
        const endpoint = item.source === "preset"
            ? `/v1/admin/presets/${item.spec.preset_type}`
            : `/v1/admin/characters/${item.id}`;
        const updated = await request<AdminCharacter>(endpoint, {
            method: "PUT",
            body: JSON.stringify({
                name: value("character-name"),
                display_name: value("character-name"),
                description: value("character-description"),
                identity: { ...item.spec.identity, role: value("character-role") },
                system_prompt: value("character-system-prompt"),
                scenario: value("character-scenario"),
                initial_greeting: value("character-greeting"),
                ...voiceSettings("character"),
                tts_voice_id: value("character-tts-voice").trim(),
                tts_gender: value("character-tts-gender"),
                goals: value("character-goals")
                    .split("\n")
                    .map((x) => x.trim())
                    .filter(Boolean),
                behavior_rules: value("character-rules")
                    .split("\n")
                    .map((x) => x.trim())
                    .filter(Boolean),
            }),
        });
        if (item.source === "preset") {
            const placement = document.querySelector<HTMLSelectElement>("#character-home-section")!.value;
            await request(`/v1/admin/presets/${item.spec.preset_type}/home-section`, {
                method: "PUT",
                body: JSON.stringify({ home_section: placement }),
            });
            updated.home_section = placement as AdminCharacter["home_section"];
        }
        const avatar = document.querySelector<HTMLInputElement>("#character-avatar-file")?.files?.[0];
        if (avatar) {
            const avatarPath = item.source === "preset"
                ? `/v1/admin/presets/${item.spec.preset_type}/avatar`
                : `/v1/admin/characters/${item.id}/avatar`;
            const uploaded = await uploadAdminAvatar(avatarPath, avatar);
            updated.spec.avatar_url = uploaded.avatar_url;
        }
        adminCharacters = adminCharacters.map((x) => x.id === updated.id ? { ...x, ...updated } : x);
        const rows = document.querySelector("#cms-char-rows");
        if (rows) rows.innerHTML = contentRows();
        const option = document.querySelector<HTMLOptionElement>(`#character-select option[value="${CSS.escape(item.id)}"]`);
        if (option) option.textContent = `${updated.spec.name}${item.source === "preset" ? " · Preset" : ` · User ${item.user_id}`}`;
        status.textContent = "Đã lưu và áp dụng cho cuộc trò chuyện mới";
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
type CmsHomeSection = {
    id: string;
    name: string;
    rule?: string;
    tags?: string[];
    hidden?: boolean;
};
let homeSections: CmsHomeSection[] = [];
let editingSectionId = "";
const SECTION_RULES: Record<string, string> = { popular: "Phổ biến nhất", trending: "Đang thịnh hành", top_rated: "Đánh giá cao", favorites: "Được yêu thích", featured: "Nổi bật", tags: "Theo tag" };
const SECTION_RULE_HINTS: Record<string, string> = { popular: "Sắp xếp theo lượt dùng", trending: "Sắp xếp theo điểm trending", top_rated: "Sắp xếp theo điểm đánh giá", favorites: "Sắp xếp theo tổng lượt cảm xúc", featured: "Nhân vật được ghim nổi bật", tags: "Lấy nhân vật có tag hoặc vai trò khớp" };
async function loadHomeSections() {
    try {
        const data = await request<CmsHomeSection[]>("/v1/home-sections");
        homeSections = Array.isArray(data) ? data : [];
    }
    catch {
        homeSections = [];
    }
    renderHomeSections();
}
/** Nhân vật hệ thống khớp một danh mục: luật theo tag lọc theo tag/vai trò, các luật xếp hạng lấy toàn bộ. */
function sectionMatches(rule: string, tags: string[]) {
    const presets = adminCharacters.filter((x) => x.source === "preset" && x.home_section !== "hidden");
    if (rule !== "tags")
        return presets;
    const wanted = tags.map((t) => t.toLowerCase()).filter(Boolean);
    return presets.filter((x) => {
        const text = `${x.spec.identity.role} ${x.spec.name} ${x.spec.description} ${x.spec.creation_type}`.toLowerCase();
        return wanted.some((t) => text.includes(t));
    });
}
const sectionAvatar = (c: AdminCharacter, size = 24) => c.spec.avatar_url
    ? `<img class="ovAvatar" src="${esc(c.spec.avatar_url)}" alt="" style="width:${size}px;height:${size}px">`
    : `<span class="ovAvatar" style="width:${size}px;height:${size}px;font-size:${Math.round(size * 0.42)}px">${esc((c.spec.name || "?")[0].toUpperCase())}</span>`;
function renderHomeSections() {
    const host = document.querySelector("#home-sections");
    if (!host)
        return;
    const rows = homeSections
        .map((s, i) => {
        const rule = s.rule || "tags", matches = sectionMatches(rule, s.tags || []);
        return `<tr><td class="num">${i + 1}</td><td><b>${esc(s.name)}</b></td><td>${esc(SECTION_RULES[rule] || rule)}<br><small class="faint">${esc(SECTION_RULE_HINTS[rule] || "")}</small></td>

        <td>${(s.tags || []).map((t) => `<span class="chip">${esc(t)}</span>`).join(" ") || '<span class="faint">—</span>'}</td>

        <td><div class="secAvatars">${matches.slice(0, 4).map((c) => sectionAvatar(c)).join("")}<span class="faint tnum">${matches.length}</span></div></td>

        <td><input type="checkbox" class="switch" data-section-visible="${esc(s.id)}" ${s.hidden ? "" : "checked"} aria-label="Hiển thị ${esc(s.name)}"></td>

        <td class="act"><div class="row" style="flex-wrap:nowrap;justify-content:flex-end"><button class="iconbtn" data-section-move="${esc(s.id)}" data-dir="-1" aria-label="Lên" ${i ? "" : "disabled"}>${ico("arrow-small-up")}</button><button class="iconbtn" data-section-move="${esc(s.id)}" data-dir="1" aria-label="Xuống" ${i < homeSections.length - 1 ? "" : "disabled"}>${ico("arrow-small-down")}</button><button class="btn sm" data-section-edit="${esc(s.id)}">Sửa</button><button class="btn sm danger" data-section-delete="${esc(s.id)}">Xóa</button></div></td></tr>`;
    })
        .join("");
    host.innerHTML =
        `<section class="panel"><header><div><h3>Danh mục</h3><small class="faint">Thứ tự hiển thị từ trên xuống trên trang chủ</small></div><div class="row"><span class="statusText" id="section-list-status"></span><button class="btn pri" id="section-create-open">${ico("plus")}Tạo danh mục mới</button></div></header>

      ${homeSections.length ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th class="num">Thứ tự</th><th>Tên danh mục</th><th>Luật lọc</th><th>Tag khớp</th><th>Nhân vật khớp</th><th>Hiển thị</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="empty" style="margin:14px">Chưa có danh mục. Bấm Tạo danh mục mới để thêm.</p>'}</section>` +
            cmsModal("modal-section", "Tạo danh mục mới", "Danh mục trang chủ", `<label class="field full">Tên danh mục *<input id="section-name" placeholder="VD: Luyện ngoại ngữ"/></label><label class="field full">Luật lọc<select id="section-rule">${Object.entries(SECTION_RULES).filter(([k]) => k !== "featured").map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select><small id="section-rule-hint"></small></label><label class="field full" id="section-tags-field">Tag khớp *<input id="section-tags" placeholder="tiếng Anh, JLPT, study"/><small>Phân tách bằng dấu phẩy</small></label><label class="switchRow full"><span><b>Hiển thị trên trang chủ</b></span><input type="checkbox" class="switch" id="section-visible" checked></label><div class="field full"><span>Xem trước <small class="faint" id="section-preview-count"></small></span><div class="hrow secPreview" id="section-preview"></div></div>`, `<span class="statusText" id="section-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="section-save">Tạo danh mục</button>`, false);
    bindHomeSections();
}
function refreshSectionDialog() {
    const rule = (document.querySelector("#section-rule") as HTMLSelectElement).value;
    const tags = (document.querySelector("#section-tags") as HTMLInputElement).value.split(",").map((x) => x.trim()).filter(Boolean);
    (document.querySelector("#section-tags-field") as HTMLElement).hidden = rule !== "tags";
    document.querySelector("#section-rule-hint")!.textContent = SECTION_RULE_HINTS[rule] || "";
    const matches = sectionMatches(rule, tags);
    document.querySelector("#section-preview-count")!.textContent = `· ${matches.length} nhân vật khớp, hiển thị tối đa 8`;
    document.querySelector("#section-preview")!.innerHTML =
        matches.slice(0, 8).map((c) => `<div class="secPreviewItem">${sectionAvatar(c, 44)}<span>${esc(c.spec.name)}</span></div>`).join("") || '<span class="faint" style="font-size:12px">Chưa có nhân vật khớp.</span>';
}
function openSectionDialog(section?: CmsHomeSection) {
    editingSectionId = section?.id || "";
    (document.querySelector("#section-name") as HTMLInputElement).value = section?.name || "";
    (document.querySelector("#section-rule") as HTMLSelectElement).value = section?.rule && SECTION_RULES[section.rule] ? section.rule : "tags";
    (document.querySelector("#section-tags") as HTMLInputElement).value = (section?.tags || []).join(", ");
    (document.querySelector("#section-visible") as HTMLInputElement).checked = !section?.hidden;
    document.querySelector("#modal-section header h2")!.textContent = section ? "Sửa danh mục" : "Tạo danh mục mới";
    document.querySelector("#section-save")!.textContent = section ? "Lưu thay đổi" : "Tạo danh mục";
    const status = document.querySelector("#section-status")!;
    status.textContent = "";
    status.className = "statusText";
    refreshSectionDialog();
    openCmsModal("modal-section");
}
function bindHomeSections() {
    const host = document.querySelector("#home-sections")!;
    host.querySelector("#section-create-open")?.addEventListener("click", () => openSectionDialog());
    host.querySelectorAll<HTMLButtonElement>("[data-section-edit]").forEach((b) => b.addEventListener("click", () => openSectionDialog(homeSections.find((s) => s.id === b.dataset.sectionEdit))));
    host.querySelector("#section-rule")?.addEventListener("change", refreshSectionDialog);
    host.querySelector("#section-tags")?.addEventListener("input", refreshSectionDialog);
    host.querySelector("#section-save")?.addEventListener("click", () => void saveHomeSection());
    host.querySelectorAll<HTMLInputElement>("[data-section-visible]").forEach((x) => x.addEventListener("change", () => void updateHomeSection(x.dataset.sectionVisible!, { hidden: !x.checked })));
    host.querySelectorAll<HTMLButtonElement>("[data-section-move]").forEach((b) => b.addEventListener("click", () => void moveHomeSection(b.dataset.sectionMove!, Number(b.dataset.dir))));
    host.querySelectorAll<HTMLButtonElement>("[data-section-delete]").forEach((b) => b.addEventListener("click", () => {
        const section = homeSections.find((s) => s.id === b.dataset.sectionDelete);
        if (section && confirm(`Xóa danh mục “${section.name}”?`))
            void deleteHomeSection(section.id);
    }));
}
function sectionListError(error: unknown) {
    const status = document.querySelector<HTMLElement>("#section-list-status");
    if (status) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
async function saveHomeSection() {
    const name = (document.querySelector("#section-name") as HTMLInputElement).value.trim();
    const rule = (document.querySelector("#section-rule") as HTMLSelectElement).value;
    const tags = (document.querySelector("#section-tags") as HTMLInputElement).value.split(",").map((x) => x.trim()).filter(Boolean);
    const hidden = !(document.querySelector("#section-visible") as HTMLInputElement).checked;
    const status = document.querySelector("#section-status")!;
    const missing = !name ? "Nhập tên danh mục." : rule === "tags" && !tags.length ? "Nhập ít nhất một tag." : "";
    status.className = missing ? "statusText error" : "statusText";
    if (missing)
        return void (status.textContent = missing);
    status.textContent = "Đang lưu…";
    try {
        const body = JSON.stringify({ name, rule, tags: rule === "tags" ? tags : [], hidden });
        if (editingSectionId)
            await request(`/v1/admin/home-sections/${encodeURIComponent(editingSectionId)}`, { method: "PATCH", body });
        else
            await request("/v1/admin/home-sections", { method: "POST", body });
        await loadHomeSections();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
async function updateHomeSection(id: string, changes: Partial<CmsHomeSection>) {
    try {
        await request(`/v1/admin/home-sections/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(changes) });
        await loadHomeSections();
    }
    catch (error) {
        await loadHomeSections();
        sectionListError(error);
    }
}
async function moveHomeSection(id: string, dir: number) {
    const ids = homeSections.map((s) => s.id), i = ids.indexOf(id), j = i + dir;
    if (i < 0 || j < 0 || j >= ids.length)
        return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    try {
        await request("/v1/admin/home-sections/order", { method: "PUT", body: JSON.stringify({ ids }) });
        await loadHomeSections();
    }
    catch (error) {
        sectionListError(error);
    }
}
async function deleteHomeSection(id: string) {
    try {
        await request(`/v1/admin/home-sections/${encodeURIComponent(id)}`, { method: "DELETE" });
        await loadHomeSections();
    }
    catch (error) {
        sectionListError(error);
    }
}
function bindAdminCreate() {
    document
        .querySelector("#create-system-character")
        ?.addEventListener("click", createAdminCharacter);
}
async function uploadAdminAvatar(path: string, file: File) {
    const data = new FormData();
    data.append("file", file);
    const response = await fetch(path, { method: "PUT", body: data });
    if (!response.ok)
        throw new Error(await response.text());
    return response.json() as Promise<{
        avatar_url: string;
        expression_status?: string;
        images_queued?: number;
    }>;
}
async function createAdminCharacter() {
    const status = document.querySelector("#new-character-status")!;
    const value = (id: string) => document
        .querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(`#${id}`)!
        .value.trim();
    if (!value("new-character-name")) {
        status.textContent = "Hãy nhập tên nhân vật";
        status.className = "statusText error";
        return;
    }
    status.textContent = "Đang tạo…";
    mountLoadingCat(status, "inline");
    status.className = "statusText";
    try {
        const created = await request<AdminCharacter>("/v1/admin/presets", {
            method: "POST",
            body: JSON.stringify({
                name: value("new-character-name"),
                role: value("new-character-role"),
                category: value("new-character-category"),
                description: value("new-character-description"),
                system_prompt: value("new-character-prompt"),
                initial_greeting: value("new-character-greeting"),
                ...voiceSettings("new-character"),
                tts_voice_id: value("new-character-tts-voice").trim(),
                tts_gender: value("new-character-tts-gender"),
            }),
        });
        const avatar = document.querySelector<HTMLInputElement>("#new-character-avatar")?.files?.[0];
        let imagesQueued = 0;
        if (avatar) {
            const uploaded = await uploadAdminAvatar(`/v1/admin/presets/${created.spec.preset_type}/avatar`, avatar);
            created.spec.avatar_url = uploaded.avatar_url;
            imagesQueued = uploaded.images_queued || 0;
        }
        adminCharacters = [created, ...adminCharacters];
        characterCatalog.preset_catalog = [
            created,
            ...characterCatalog.preset_catalog,
        ];
        renderContent();
        const select = document.querySelector<HTMLSelectElement>("#character-select");
        if (select) {
            select.value = created.id;
            fillCharacter();
            void loadExpressionPreview(created);
        }
        openCmsModal("modal-edit-character");
        const createdStatus = document.querySelector("#character-status");
        if (createdStatus)
            createdStatus.textContent = imagesQueued ? `Đã tạo nhân vật · đang tạo ${imagesQueued} ảnh biểu cảm` : "Đã tạo nhân vật · tải ảnh nguồn để tạo biểu cảm";
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
function modelOptions(selected = "", includeEmpty = false) {
    const options = models
        .map((x) => `<option value="${esc(x.id)}" ${x.id === selected ? "selected" : ""}>${esc(x.name)} &middot; ${esc(x.model_id)}${x.enabled ? "" : " (\u0111ang \u1ea9n)"}</option>`)
        .join("");
    return `${includeEmpty ? '<option value="">Ch\u01b0a ph\u00e2n c\u00f4ng</option>' : ""}${options}`;
}
const modelPurposeLabels: Record<string, string> = {
    response: "Trả lời hội thoại",
    suggestion: "Gợi ý trả lời",
    suggestion_fallback: "Dự phòng gợi ý",
    compiler: "Tạo nhân vật",
    moderation: "Kiểm duyệt",
    fallback: "Dự phòng",
    avatar_image: "Tạo avatar biểu cảm",
    emotion: "Nhận diện cảm xúc",
    emotion_fallback: "Dự phòng cảm xúc",
    tts: "Phát giọng nói Role Play",
    assistant_general: "Assistant · Tổng quát",
    assistant_general_fallback: "Dự phòng · Tổng quát",
    assistant_psychology_fallback: "Dự phòng · Tâm lý",
    assistant_health_fallback: "Dự phòng · Sức khỏe",
    assistant_homework_fallback: "Dự phòng · Bài tập",
    assistant_tarot_fallback: "Dự phòng · Tarot",
    assistant_psychology: "Assistant · Tâm lý",
    assistant_health: "Assistant · Sức khỏe",
    assistant_homework: "Assistant · Bài tập",
    assistant_tarot: "Assistant · Tarot",
    assistant_suggestion: "Assistant · Gợi ý trả lời",
};
/* ---------- Cấu hình AI (theo màn admAI của prototype) ---------- */
const GATEWAY_BASE = "https://gateway.avibi.ai/v1";
let modelsTab: "models" | "conns" = "models";
let modelFilter = { q: "", provider: "all", type: "all", status: "all" };
let editingModelId = "";
const normBase = (base: string) => base.replace(/\/+$/, "").toLowerCase();
const baseHost = (base: string) => {
    try {
        return new URL(base).host;
    }
    catch {
        return base || "—";
    }
};
const modelType = (m: ModelConfig) => (m.purposes.includes("tts") ? "TTS" : m.purposes.includes("avatar_image") ? "Ảnh" : "Chat");
/** Nhãn tác vụ; tác vụ dự phòng chưa có nhãn riêng thì ghép từ nhãn tác vụ gốc. */
const purposeLabel = (p: string) => {
    if (modelPurposeLabels[p])
        return modelPurposeLabels[p];
    const match = p.match(/^(.*)_fallback(?:_(\d))?$/);
    if (match && modelPurposeLabels[match[1]])
        return `${modelPurposeLabels[match[1]].replace(/^Assistant · /, "")} · dự phòng ${match[2] || 1}`;
    return p;
};
const modelUsage = (m: ModelConfig) => m.purposes.map(purposeLabel);
/** Nguồn API key mà model đang dùng: key riêng, key theo API base hoặc key gateway chung. */
function modelKeySource(m: ModelConfig) {
    if (m.has_api_key)
        return { ok: true, label: "Key riêng", hint: m.api_key_hint };
    const base = normBase(m.api_base);
    const entry = credentials?.bases?.find((item) => normBase(item.api_base) === base);
    if (entry)
        return { ok: true, label: "Key theo API base", hint: entry.hint };
    if (base === GATEWAY_BASE && credentials?.avibi.configured)
        return { ok: true, label: "Key gateway chung", hint: credentials.avibi.hint };
    return { ok: false, label: "Chưa có API key", hint: "" };
}
type Connection = {
    base: string;
    gateway: boolean;
    hint: string;
    source: string;
    ok: boolean;
    baseKeyId?: string;
    models: ModelConfig[];
};
function connections(): Connection[] {
    const bases = new Map<string, Connection>();
    const add = (base: string) => {
        const key = normBase(base);
        if (!bases.has(key)) {
            const gateway = key === GATEWAY_BASE;
            const entry = credentials?.bases?.find((item) => normBase(item.api_base) === key);
            const hint = entry?.hint || (gateway && credentials?.avibi.configured ? credentials.avibi.hint : "");
            const source = entry ? "Key theo API base" : gateway ? (credentials?.avibi.source === "modal_secret" ? "Modal Secret" : credentials?.avibi.configured ? "Lưu trong CMS" : "Chưa cấu hình") : "Chưa cấu hình";
            bases.set(key, { base: key, gateway, hint, source, ok: Boolean(hint), baseKeyId: entry?.id, models: [] });
        }
        return bases.get(key)!;
    };
    add(GATEWAY_BASE);
    (credentials?.bases || []).forEach((item) => add(item.api_base));
    models.forEach((m) => add(m.api_base).models.push(m));
    return [...bases.values()];
}
const modelLogo = (m: ModelConfig, size = 30) => {
    let hash = 0;
    for (const ch of m.provider + m.name)
        hash = (hash * 31 + ch.charCodeAt(0)) % 360;
    return `<span class="mdlLogo" style="width:${size}px;height:${size}px;background:hsl(${hash} 45% 45%)">${esc((m.logo || m.name || "?").slice(0, 2).toUpperCase())}</span>`;
};
function renderModels() {
    const conns = connections();
    const brokenConns = conns.filter((c) => !c.ok && c.models.length).length;
    const tabs = `<div class="tabs mdlTabs" role="tablist"><button role="tab" aria-selected="${modelsTab === "models"}" data-models-tab="models">Model <span class="chip tnum">${models.length}</span></button><button role="tab" aria-selected="${modelsTab === "conns"}" data-models-tab="conns">Kết nối &amp; API key <span class="chip tnum${brokenConns ? " bad" : ""}">${conns.length}</span></button></div>`;
    let body = "";
    if (modelsTab === "conns") {
        body = `${brokenConns ? `<div class="note-info" style="background:var(--bad-soft)">${ico("info")}<span><b>${brokenConns} kết nối chưa có API key.</b> Các model dùng kết nối này sẽ lỗi hoặc phải chuyển sang dự phòng.</span></div>` : ""}

      <div class="mdlBar"><p class="muted" style="font-size:13px;margin:0">Model dùng key riêng nếu có; nếu không thì dùng key của API base tương ứng. Gateway AVIBI là kết nối mặc định.</p><button class="btn pri" id="conn-add">${ico("plus")}Thêm kết nối</button></div>

      <div class="conn-grid">${conns
            .map((c) => `<article class="panel conn${c.ok || !c.models.length ? "" : " down"}">

        <header><div class="row" style="flex-wrap:nowrap;gap:10px;min-width:0"><span class="tl-ic">${ico(c.gateway ? "globe" : "link")}</span><div style="min-width:0"><h3>${esc(c.gateway ? "Gateway AVIBI" : baseHost(c.base))}</h3><small class="mono faint">${esc(c.base)}</small></div></div>

          <span class="chip ${c.ok ? "ok" : "bad"}">${c.ok ? "Đã có key" : "Thiếu key"}</span></header>

        <div class="pb">

          <div class="kvs">

            <div class="kv"><span>API key</span><span>${c.hint ? `<code class="mono">${esc(c.hint)}</code>` : '<span class="faint">Chưa có</span>'}</span></div>

            <div class="kv"><span>Nguồn key</span><span>${esc(c.source)}</span></div>

            <div class="kv"><span>Model dùng</span><span>${c.models.length ? c.models.map((m) => `<span class="chip">${esc(m.name)}</span>`).join(" ") : '<span class="faint">Chưa có model</span>'}</span></div>

          </div>

          <div class="row"><button class="btn sm" data-conn-edit="${esc(c.base)}">${ico("edit")}${c.ok ? "Đổi key" : "Cập nhật key"}</button>${c.gateway && credentials?.avibi.source === "cms" ? `<button class="btn sm" id="reset-credential">Dùng Modal Secret</button>` : ""}${c.baseKeyId ? `<button class="btn sm danger" data-delete-base-key="${esc(c.baseKeyId)}">Xóa key</button>` : ""}</div>

        </div></article>`)
            .join("")}</div>`;
    }
    else {
        const q = modelFilter.q.toLowerCase();
        const providers = [...new Set(models.map((m) => m.provider).filter(Boolean))];
        const list = models.filter((m) => (!q || `${m.name} ${m.model_id}`.toLowerCase().includes(q)) &&
            (modelFilter.provider === "all" || m.provider === modelFilter.provider) &&
            (modelFilter.type === "all" || modelType(m) === modelFilter.type) &&
            (modelFilter.status === "all" || (modelFilter.status === "on") === m.enabled));
        const on = models.filter((m) => m.enabled).length;
        const noKey = models.filter((m) => !modelKeySource(m).ok).length;
        const unused = models.filter((m) => !m.purposes.length).length;
        const rows = list
            .map((m) => {
            const key = modelKeySource(m), use = modelUsage(m);
            return `<tr class="${m.enabled ? "" : "muted-row"}">

        <td><div class="row" style="flex-wrap:nowrap">${modelLogo(m)}<span><b>${esc(m.name)}</b><br><small class="mono faint">${esc(m.provider)} · ${esc(m.model_id)}</small></span></div></td>

        <td><span class="chip">${modelType(m)}</span></td>

        <td><span class="row" style="flex-wrap:nowrap;gap:6px" title="${esc(key.label)}${key.hint ? ` · ${esc(key.hint)}` : ""}"><span class="dot ${key.ok ? "ok" : "bad"}"></span>${esc(baseHost(m.api_base))}</span></td>

        <td>${use.length ? `<span title="${esc(use.join(", "))}">${use.slice(0, 2).map((u) => `<span class="chip">${esc(u)}</span>`).join(" ")}${use.length > 2 ? ` <span class="faint" style="font-size:12px">+${use.length - 2}</span>` : ""}</span>` : '<span class="faint">Chưa dùng</span>'}</td>

        <td><input type="checkbox" class="switch" data-toggle="${esc(m.id)}" ${m.enabled ? "checked" : ""} aria-label="Bật ${esc(m.name)}"></td>

        <td class="act"><div class="row" style="flex-wrap:nowrap;justify-content:flex-end"><button class="btn sm" data-edit="${esc(m.id)}">Cấu hình</button><button class="iconbtn" data-delete="${esc(m.id)}" aria-label="Xóa ${esc(m.name)}" style="color:var(--bad)">${ico("trash")}</button></div></td></tr>`;
        })
            .join("");
        body = `<div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))">

        <div class="kpi"><span>Tổng số model</span><b>${models.length}</b><small class="faint">${providers.length} nhà cung cấp</small></div>

        <div class="kpi"><span>Đang bật</span><b>${on}</b><small class="faint">${models.length - on} đang ẩn</small></div>

        <div class="kpi"><span>Thiếu API key</span><b style="color:var(--${noKey ? "bad" : "ink"})">${noKey}</b><small style="color:var(--${noKey ? "bad" : "ok"})">${noKey ? "model sẽ lỗi khi gọi" : "tất cả đã có key"}</small></div>

        <div class="kpi"><span>Chưa phân công</span><b>${unused}</b><small class="faint">${unused ? "chưa dùng cho tác vụ nào" : "mọi model đều được dùng"}</small></div></div>

      <section class="panel"><header><div class="filters mdlFilters">

          <label class="mdlSearch">${ico("search")}<input id="m-q" placeholder="Tìm tên hoặc model ID" value="${esc(modelFilter.q)}"></label>

          <label class="mdlFilter">Nhà cung cấp <select data-model-filter="provider" class="sm"><option value="all">Tất cả</option>${providers.map((p) => `<option ${modelFilter.provider === p ? "selected" : ""}>${esc(p)}</option>`).join("")}</select></label>

          <label class="mdlFilter">Loại <select data-model-filter="type" class="sm"><option value="all">Tất cả</option>${["Chat", "TTS", "Ảnh"].map((t) => `<option ${modelFilter.type === t ? "selected" : ""}>${t}</option>`).join("")}</select></label>

          <label class="mdlFilter">Trạng thái <select data-model-filter="status" class="sm"><option value="all">Tất cả</option><option value="on" ${modelFilter.status === "on" ? "selected" : ""}>Đang bật</option><option value="off" ${modelFilter.status === "off" ? "selected" : ""}>Đang ẩn</option></select></label></div>

        <button class="btn pri" id="model-add-open">${ico("plus")}Thêm model</button></header>

        ${models.length ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Model</th><th>Loại</th><th>Kết nối</th><th>Đang dùng cho</th><th>Bật</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div>` : ""}

        ${list.length ? "" : `<p class="empty" style="margin:14px">${models.length ? "Không có model phù hợp bộ lọc." : "Chưa có model. Bấm Thêm model để bắt đầu."}</p>`}</section>`;
    }
    const dialogs = cmsModal("modal-model-add", "Thêm model", "Cấu hình AI", `<div class="dt-t"><b>Thông tin</b></div><div class="fields"><label class="field">Tên hiển thị *<input id="model-name"/></label><label class="field">Nhà cung cấp<input id="model-provider" value="AVIBI"/></label><label class="field">Model ID *<input id="model-id" class="mono" placeholder="openai/gpt-4.1-mini"/></label><label class="field">Logo chữ<input id="model-logo" maxlength="4" value="AI"/></label><label class="field full">API base<input id="model-base" class="mono" value="${GATEWAY_BASE}"/><small>Dùng chung key của kết nối nếu không nhập key riêng</small></label><label class="field full">API key riêng<input type="password" id="model-key" class="mono" placeholder="Để trống để dùng key của kết nối"/><small>Key được mã hóa khi lưu và chỉ hiện 4 ký tự cuối</small></label></div>`, `<span class="statusText" id="model-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="add-model">Thêm model</button>`) +
        cmsModal("modal-model-edit", "Cấu hình model", "Cấu hình AI", `<div class="modelPurposeSummary" id="model-purpose-summary"></div><div class="dt-t"><b>Thông tin</b></div><div class="fields"><label class="field">Tên hiển thị<input id="edit-model-name"/></label><label class="field">Nhà cung cấp<input id="edit-model-provider"/></label><label class="field full">Model ID<input id="edit-model-id" class="mono"/></label><label class="field full">API base<input id="edit-model-base" class="mono"/></label><label class="field full" data-config-purpose="tts">Mã giọng TTS mặc định<input id="edit-model-tts-voice" maxlength="160" placeholder="Voice ID từ gateway"/><small>Áp dụng cho nhân vật chưa có mã giọng riêng. API base cần kết thúc bằng /v1.</small></label><label class="field full">API key mới<input id="edit-model-key" type="password" class="mono" placeholder="Để trống để giữ key hiện tại"/></label></div><div class="dt-t"><b>Tham số mặc định</b><small>Trợ lý hoặc tác vụ có thể ghi đè</small></div><div class="fields"><label class="field" data-config-generation="text">Temperature mặc định<input id="edit-model-temperature" type="number" min="0" max="2" step="0.05"/></label><label class="field" data-config-generation="text">Temperature câu ngắn<input id="edit-model-short-temperature" type="number" min="0" max="2" step="0.05"/></label><label class="field" data-config-generation="text">Max tokens mặc định<input id="edit-model-max-tokens" type="number" min="50" max="8000"/></label><label class="field" data-config-generation="text">Max tokens câu ngắn<input id="edit-model-short-max-tokens" type="number" min="50" max="8000"/></label><label class="field">Thinking mode<select id="edit-model-thinking"><option value="default">Theo mặc định gateway</option><option value="enabled">Bật</option><option value="disabled">Tắt</option></select></label><label class="field">Reasoning effort<select id="edit-model-effort"><option value="default">Theo mặc định gateway</option><option value="low">Low</option><option value="high">High</option><option value="max">Max</option></select></label><label class="field">Chờ gateway tối đa (giây)<input id="edit-model-gateway-timeout" type="number" min="4" max="45" step="1"/><small>Quá thời gian sẽ chuyển sang dự phòng</small></label></div><div class="dt-t" id="model-prompt-title"><b>System prompt theo tác vụ</b><small>Chỉ hiện các tác vụ model này đang được phân công</small></div><div class="fields"><label class="field full" data-config-purpose="response">Trả lời hội thoại<textarea class="largePrompt" id="edit-response-prompt"></textarea></label><label class="field full" data-config-purpose="suggestion">Gợi ý trả lời<textarea class="largePrompt" id="edit-suggestion-prompt"></textarea></label><label class="field full" data-config-purpose="compiler">Tạo nhân vật<textarea class="largePrompt" id="edit-compiler-prompt"></textarea></label><label class="field full" data-config-purpose="moderation">Kiểm duyệt<textarea class="largePrompt" id="edit-moderation-prompt"></textarea></label><label class="field full" data-config-purpose="emotion">Nhận diện cảm xúc<textarea class="largePrompt" id="edit-emotion-prompt"></textarea></label></div>`, `<span class="statusText" id="model-edit-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="save-model-profile">Lưu thay đổi</button>`) +
        cmsModal("modal-conn", "Kết nối", "Kết nối &amp; API key", `<label class="field full">API base *<input id="credential-base-url" class="mono" placeholder="https://…/v1"/></label><label class="field full">API key *<input id="credential-base-key" type="password" class="mono" autocomplete="new-password" placeholder="Dán key vào đây"/><small>Key được mã hóa khi lưu và chỉ hiện 4 ký tự cuối</small></label>`, `<span class="statusText" id="credential-base-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="save-base-credential">Lưu key</button>`, false);
    document.querySelector("#models")!.innerHTML = tabs + body + dialogs;
    bindModels();
}
function bindModels() {
    const host = document.querySelector("#models")!;
    host.querySelectorAll<HTMLButtonElement>("[data-models-tab]").forEach((b) => b.addEventListener("click", () => {
        modelsTab = b.dataset.modelsTab as typeof modelsTab;
        renderModels();
    }));
    host.querySelector<HTMLInputElement>("#m-q")?.addEventListener("input", (event) => {
        modelFilter.q = (event.target as HTMLInputElement).value;
        renderModels();
        const input = document.querySelector<HTMLInputElement>("#m-q")!;
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    });
    host.querySelectorAll<HTMLSelectElement>("[data-model-filter]").forEach((s) => s.addEventListener("change", () => {
        (modelFilter as Record<string, string>)[s.dataset.modelFilter!] = s.value;
        renderModels();
    }));
    host.querySelector("#model-add-open")?.addEventListener("click", () => openCmsModal("modal-model-add"));
    host.querySelector("#add-model")?.addEventListener("click", addModel);
    host.querySelectorAll<HTMLButtonElement>("[data-edit]").forEach((b) => b.addEventListener("click", () => {
        editingModelId = b.dataset.edit!;
        fillModelEditor();
        openCmsModal("modal-model-edit");
    }));
    host.querySelector("#save-model-profile")?.addEventListener("click", saveModelProfile);
    host.querySelectorAll<HTMLInputElement>("[data-toggle]").forEach((x) => x.addEventListener("change", () => void patchModel(x.dataset.toggle!, { enabled: x.checked })));
    host.querySelectorAll<HTMLButtonElement>("[data-delete]").forEach((x) => x.addEventListener("click", () => deleteModel(x.dataset.delete!)));
    host.querySelector("#conn-add")?.addEventListener("click", () => {
        (host.querySelector("#credential-base-url") as HTMLInputElement).value = "";
        (host.querySelector("#credential-base-url") as HTMLInputElement).readOnly = false;
        openCmsModal("modal-conn");
    });
    host.querySelectorAll<HTMLButtonElement>("[data-conn-edit]").forEach((b) => b.addEventListener("click", () => {
        const url = host.querySelector("#credential-base-url") as HTMLInputElement;
        url.value = b.dataset.connEdit!;
        url.readOnly = true;
        openCmsModal("modal-conn");
    }));
    host.querySelector("#save-base-credential")?.addEventListener("click", saveConnectionKey);
    host.querySelectorAll<HTMLButtonElement>("[data-delete-base-key]").forEach((button) => button.addEventListener("click", () => void deleteBaseCredential(button.dataset.deleteBaseKey || "")));
    host.querySelector("#reset-credential")?.addEventListener("click", resetCredential);
}
/** Lưu key cho một kết nối: gateway AVIBI dùng key chung, API base khác dùng key theo API base. */
async function saveConnectionKey() {
    const base = normBase((document.querySelector("#credential-base-url") as HTMLInputElement).value.trim());
    const key = (document.querySelector("#credential-base-key") as HTMLInputElement).value.trim();
    const status = document.querySelector<HTMLElement>("#credential-base-status")!;
    if (!base || !key) {
        status.textContent = "Nhập API base và API key.";
        status.className = "statusText error";
        return;
    }
    status.textContent = "Đang lưu…";
    status.className = "statusText";
    try {
        if (base === GATEWAY_BASE) {
            const result = await request<CredentialState["avibi"]>("/v1/admin/credentials/avibi", { method: "PUT", body: JSON.stringify({ api_key: key }) });
            credentials = { ...credentials, avibi: result };
        }
        else {
            await request("/v1/admin/credentials/bases", { method: "PUT", body: JSON.stringify({ api_base: base, api_key: key }) });
            credentials = await request<CredentialState>("/v1/admin/credentials");
        }
        renderModels();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
function selectedModel() {
    return models.find((x) => x.id === editingModelId);
}
function fillModelEditor() {
    if (!document.querySelector("#edit-model-tts-voice")) {
        document.querySelector("#edit-model-base")?.closest("label")?.insertAdjacentHTML("afterend", '<label class="field full" data-config-purpose="tts">Mã giọng TTS mặc định<input id="edit-model-tts-voice" maxlength="160" placeholder="Voice ID từ gateway"/><small>Áp dụng cho nhân vật chưa có mã giọng riêng. API base cần kết thúc bằng /v1.</small></label>');
    }
    const model = selectedModel();
    if (!model)
        return;
    const values: Record<string, string> = {
        "edit-model-name": model.name,
        "edit-model-provider": model.provider,
        "edit-model-id": model.model_id,
        "edit-model-base": model.api_base,
        "edit-model-key": "",
        "edit-model-temperature": model.temperature,
        "edit-model-short-temperature": model.short_temperature,
        "edit-model-max-tokens": model.max_tokens,
        "edit-model-short-max-tokens": model.short_max_tokens,
        "edit-model-gateway-timeout": model.gateway_read_timeout_seconds,
        "edit-model-tts-voice": model.tts_default_voice,
        "edit-model-thinking": model.thinking_mode,
        "edit-model-effort": model.reasoning_effort,
        "edit-response-prompt": model.response_instruction,
        "edit-suggestion-prompt": model.suggestion_instruction,
        "edit-compiler-prompt": model.compiler_instruction,
        "edit-moderation-prompt": model.moderation_instruction,
        "edit-emotion-prompt": model.emotion_instruction,
    };
    Object.entries(values).forEach(([id, value]) => {
        const node = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`);
        if (node)
            node.value = value || "";
    });
    const textGeneration = !model.purposes.length || model.purposes.some((purpose) => purpose !== "tts" && purpose !== "avatar_image");
    document.querySelectorAll<HTMLElement>("#modal-model-edit [data-config-generation]").forEach((node) => { node.hidden = !textGeneration; });
    let promptCount = 0;
    document.querySelectorAll<HTMLElement>("#modal-model-edit [data-config-purpose]").forEach((node) => {
        const purpose = node.dataset.configPurpose!;
        node.hidden = !(model.purposes.includes(purpose) ||
            model.purposes.includes(purpose + "_fallback") ||
            (purpose === "response" && model.purposes.includes("fallback")));
        if (!node.hidden && node.querySelector("textarea"))
            promptCount++;
    });
    (document.querySelector("#model-prompt-title") as HTMLElement).hidden = !promptCount;
    const title = document.querySelector("#modal-model-edit header h2");
    if (title)
        title.textContent = `Cấu hình ${model.name}`;
    const summary = document.querySelector("#model-purpose-summary");
    if (summary)
        summary.innerHTML = model.purposes.length
            ? `<span class="faint" style="font-size:12px">Đang dùng cho:</span> ${model.purposes.map((p) => `<span class="chip">${esc(purposeLabel(p))}</span>`).join(" ")}`
            : `<span class="faint" style="font-size:12px">Chưa được dùng ở tác vụ nào.</span>`;
    const status = document.querySelector("#model-edit-status");
    if (status) {
        status.textContent = "";
        status.className = "statusText";
    }
}
async function saveModelProfile() {
    const model = selectedModel();
    const status = document.querySelector("#model-edit-status")!;
    if (!model)
        return;
    const value = (id: string) => document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`)!
        .value;
    status.textContent = "\u0110ang l\u01b0u\u2026";
    mountLoadingCat(status, "inline");
    try {
        const updated = await request<ModelUpdate>(`/v1/admin/models/${model.id}`, {
            method: "PATCH",
            body: JSON.stringify({
                name: value("edit-model-name"),
                provider: value("edit-model-provider"),
                model_id: value("edit-model-id"),
                api_base: value("edit-model-base"),
                api_key: value("edit-model-key"),
                temperature: value("edit-model-temperature"),
                short_temperature: value("edit-model-short-temperature"),
                max_tokens: value("edit-model-max-tokens"),
                short_max_tokens: value("edit-model-short-max-tokens"),
                gateway_read_timeout_seconds: value("edit-model-gateway-timeout"),
                tts_default_voice: value("edit-model-tts-voice"),
                thinking_mode: value("edit-model-thinking"),
                reasoning_effort: value("edit-model-effort"),
                response_instruction: value("edit-response-prompt"),
                suggestion_instruction: value("edit-suggestion-prompt"),
                compiler_instruction: value("edit-compiler-prompt"),
                moderation_instruction: value("edit-moderation-prompt"),
                emotion_instruction: value("edit-emotion-prompt"),
            }),
        });
        if (updated.expression_generation) {
            const plan = updated.expression_generation;
            showGenerationNotice(plan);
        }
        await reloadModels();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
async function resetCredential() {
    try {
        const result = await request<CredentialState["avibi"]>("/v1/admin/credentials/avibi", { method: "DELETE" });
        credentials = { ...credentials, avibi: result };
        renderModels();
    }
    catch (error) {
        alert(String(error));
    }
}
async function deleteBaseCredential(id: string) {
    try {
        await request(`/v1/admin/credentials/bases/${encodeURIComponent(id)}`, { method: "DELETE" });
        credentials = await request<CredentialState>("/v1/admin/credentials");
        renderModels();
    }
    catch (error) {
        alert(String(error));
    }
}
async function reloadModels() {
    models = await request<ModelConfig[]>("/v1/admin/models");
    renderModels();
    renderSettings();
}
async function addModel() {
    const status = document.querySelector("#model-status")!;
    const value = (id: string) => document.querySelector<HTMLInputElement>(`#${id}`)!.value;
    status.textContent = "Đang mã hóa và lưu…";
    mountLoadingCat(status, "inline");
    try {
        await request("/v1/admin/models", {
            method: "POST",
            body: JSON.stringify({
                name: value("model-name"),
                provider: value("model-provider"),
                model_id: value("model-id"),
                logo: value("model-logo"),
                api_base: value("model-base"),
                api_key: value("model-key"),
                enabled: true,
            }),
        });
        status.textContent = "Đã thêm model";
        await reloadModels();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
async function patchModel(id: string, body: Record<string, unknown>) {
    try {
        await request(`/v1/admin/models/${id}`, {
            method: "PATCH",
            body: JSON.stringify(body),
        });
        await reloadModels();
    }
    catch (error) {
        alert(String(error));
        await reloadModels();
    }
}
async function deleteModel(id: string) {
    if (!confirm("Xóa cấu hình model này?"))
        return;
    try {
        await request(`/v1/admin/models/${id}?force=true`, { method: "DELETE" });
        await reloadModels();
    }
    catch (error) {
        alert(String(error));
    }
}
function assignmentValue(purpose: string) {
    return models.find((x) => x.purposes.includes(purpose))?.id || "";
}
const assistantPurposes = [
    "assistant_general",
    "assistant_psychology",
    "assistant_health",
    "assistant_homework",
    "assistant_tarot",
    "assistant_suggestion",
];
/* ---------- Trợ lý AI (theo màn "as-cms" của prototype) ---------- */
type AssistantStats = {
    requests: number;
    fallback_rate: number;
    latency: number;
    error_rate: number;
    days: number[];
};
type AssistantProfile = {
    title: string;
    slogan: string;
    description: string;
    greeting: string;
    starters: string[];
    visible: boolean;
    user_pick: boolean;
    icon?: string;
    hue?: number;
    hair?: number;
    custom?: boolean;
    stats?: AssistantStats;
};
type AssistantProfiles = {
    order: string[];
    items: Record<string, AssistantProfile>;
};
type AssistantDraft = {
    main: string;
    f1: string;
    f2: string;
    prompt: string;
    fp1: string;
    fp2: string;
    title: string;
    slogan: string;
    description: string;
    greeting: string;
    starters: string;
    visible: boolean;
    user_pick: boolean;
};
type GlobalDraft = {
    prompt: string;
    enabled: Record<string, boolean>;
};
type AssistantTab = "info" | "model" | "prompt" | "stats";
const ASSISTANT_INFO: Record<string, {
    name: string;
    desc: string;
}> = {
    assistant_general: { name: "Trợ lý AI chung", desc: "Hỏi mình bất cứ điều gì" },
    assistant_psychology: { name: "Tâm lý", desc: "Lắng nghe và cùng bạn gỡ rối cảm xúc" },
    assistant_health: { name: "Sức khỏe", desc: "Thông tin sức khỏe thận trọng, dễ hiểu" },
    assistant_homework: { name: "Học tập", desc: "Giải thích từng bước từ tài liệu của bạn" },
    assistant_tarot: { name: "Tarot & Tử vi", desc: "Gửi Bát Tự, lá số hoặc trải bài minh họa" },
    assistant_suggestion: { name: "Gợi ý trả lời", desc: "Tác vụ nền: sinh 3 gợi ý dưới mỗi câu trả lời" },
};
const ASSISTANT_ICONS: [
    string,
    string
][] = [["sparkles", "Đa năng"], ["book-alt", "Học tập"], ["heart", "Sức khỏe"], ["cloud", "Cảm xúc"], ["moon-stars", "Chiêm nghiệm"], ["users", "Giao tiếp"], ["globe", "Ngoại ngữ"], ["document", "Tài liệu"]];
const ASSISTANT_HUES = [172, 205, 140, 32, 275, 350, 220, 48];
let assistantProfiles: AssistantProfiles = { order: [], items: {} };
let assistantProfilesAvailable = true;
let activeAssistantPurpose = "global";
let activeAssistantTab: AssistantTab = "info";
let assistantDraft: AssistantDraft | null = null;
let assistantGlobalDraft: GlobalDraft | null = null;
let assistantDirty = false;
const defaultProfile = (purpose: string): AssistantProfile => ({
    title: ASSISTANT_INFO[purpose]?.name || purpose, slogan: "", description: ASSISTANT_INFO[purpose]?.desc || "", greeting: "", starters: [],
    visible: true, user_pick: false,
});
const profileOf = (purpose: string) => assistantProfiles.items[purpose] || defaultProfile(purpose);
/** Trợ lý hiển thị cho người dùng: 5 trợ lý có sẵn và các trợ lý admin tạo thêm. */
const userAssistants = () => [
    ...assistantPurposes.filter((p) => p !== "assistant_suggestion"),
    ...assistantProfiles.order.filter((p) => !assistantPurposes.includes(p)),
];
async function loadAssistantProfiles() {
    try {
        assistantProfiles = await request<AssistantProfiles>("/v1/admin/assistant-profiles");
        assistantProfilesAvailable = true;
    }
    catch {
        assistantProfilesAvailable = false;
    }
}
const purposeModel = (role: string) => models.find((x) => x.purposes.includes(role));
const assistantPromptOf = (model: ModelConfig | undefined, field: string) => model ? String((model as unknown as Record<string, unknown>)[field] || "") : "";
function loadAssistantDraft(purpose: string): AssistantDraft {
    const main = purposeModel(purpose), f1 = purposeModel(purpose + "_fallback"), f2 = purposeModel(purpose + "_fallback_2");
    const p = profileOf(purpose);
    return {
        main: main?.id || "", f1: f1?.id || "", f2: f2?.id || "",
        prompt: assistantPromptOf(main, purpose + "_instruction"),
        fp1: assistantPromptOf(f1, purpose + "_fallback_instruction"),
        fp2: assistantPromptOf(f2, purpose + "_fallback_2_instruction"),
        title: p.title, slogan: p.slogan, description: p.description, greeting: p.greeting, starters: p.starters.join("\n"), visible: p.visible,
        user_pick: p.user_pick,
    };
}
function loadGlobalDraft(): GlobalDraft {
    return {
        prompt: settings?.assistant_system_instruction || "",
        enabled: Object.fromEntries(models.map((m) => [m.id, m.assistant_enabled])),
    };
}
/** Tình trạng chuỗi model của một tác vụ: đủ 3 model, thiếu dự phòng hoặc có model đang ẩn. */
function assistantHealth(ids: string[]) {
    const picked = ids.filter(Boolean);
    const hidden = picked.filter((id) => models.find((m) => m.id === id && !m.assistant_enabled));
    if (!ids[0])
        return { k: "bad", t: "Chưa có model chính", n: picked.length };
    if (hidden.length)
        return { k: "warn", t: "Có model đang ẩn", n: picked.length };
    if (picked.length < 3)
        return { k: picked.length === 1 ? "bad" : "warn", t: `Thiếu ${3 - picked.length} dự phòng`, n: picked.length };
    return { k: "ok", t: "Đủ model", n: 3 };
}
const savedHealth = (purpose: string) => assistantHealth([purpose, purpose + "_fallback", purpose + "_fallback_2"].map((role) => purposeModel(role)?.id || ""));
const assistantName = (purpose: string) => purpose === "assistant_suggestion" ? ASSISTANT_INFO[purpose].name : purpose === "assistant_general" ? ASSISTANT_INFO[purpose].name : profileOf(purpose).title;
const assistantDesc = (purpose: string) => (purpose === "assistant_suggestion" ? ASSISTANT_INFO[purpose].desc : profileOf(purpose).description);
function assistantFace(purpose: string, size = 34) {
    const p = assistantProfiles.items[purpose];
    return p?.custom ? faceSvg(p.hue ?? 172, HAIRS[p.hair ?? 0], size) : personaFaceSvg(purpose, size);
}
function assistantIllustration(purpose: string) {
    const p = assistantProfiles.items[purpose];
    return p?.custom ? illustrationHtml(purpose, p.hue ?? 172, p.icon || "sparkles") : illustrationHtml(purpose);
}
const assistantIcon = (purpose: string, large = false) => purpose === "assistant_suggestion" || purpose === "global"
    ? `<span class="tl-ic${large ? " lg" : ""}">${ico(purpose === "global" ? "settings-sliders" : "sparkles")}</span>`
    : assistantFace(purpose, large ? 44 : 34);
/** Thẻ trợ lý như trên trang chủ Trợ lý AI, dùng cho phần xem trước. */
function assistantCardPreview(o: {
    face: string;
    illustration: string;
    title: string;
    description: string;
    requests: number;
    hidden?: boolean;
}) {
    return `<article class="asSpec asPreviewCard">${o.hidden ? '<span class="chip warn asPreviewHidden">Đang ẩn</span>' : ""}<div class="asSpecArt">${o.illustration}<span class="asSpecAvatar"><span class="modeAvatar" style="width:44px;height:44px">${o.face}</span></span></div><div class="asSpecBody"><b>${esc(o.title || "Tên trợ lý")}</b><p>${esc(o.description || "Mô tả ngắn của trợ lý")}</p><div class="asSpecFoot"><span class="asSpecCount">${ico("comment-alt")}<b class="tnum">${o.requests.toLocaleString("vi-VN")}</b> lượt tương tác</span><span class="btn pri sm">${ico("comment-alt")}Chat</span></div></div></article>`;
}
const profilesNote = () => assistantProfilesAvailable ? "" : `<div class="note">Backend chưa có API <span class="mono">/v1/admin/assistant-profiles</span> nên phần hiển thị và thống kê chỉ để xem, không lưu được.</div>`;
function assistantSaveBar() {
    return `<div class="savebar${assistantDirty ? " on" : ""}"><span id="assistant-save-status">${assistantDirty ? `${ico("info")} Có thay đổi chưa lưu` : `${ico("check")} Đã lưu`}</span><div class="savebarActions"><button class="btn" id="assistant-discard" ${assistantDirty ? "" : "disabled"}>Hủy thay đổi</button><button class="btn pri" id="assistant-save" ${assistantDirty ? "" : "disabled"}>Lưu thay đổi</button></div></div>`;
}
function assistantModelSelect(id: string, selected: string, placeholder = "— Chưa chọn —") {
    return `<select class="input" id="${id}"><option value="">${placeholder}</option>${models
        .map((m) => `<option value="${esc(m.id)}" ${m.id === selected ? "selected" : ""}>${esc(m.assistant_name || m.name)}${m.assistant_enabled ? "" : " (đang ẩn)"}</option>`)
        .join("")}</select>`;
}
function assistantGlobalView() {
    const g = assistantGlobalDraft!;
    const rows = models.map((m) => `<tr><td><b>${esc(m.assistant_name || m.name)}</b></td><td class="mono">${esc(m.assistant_model_id || m.model_id)}</td><td><input type="checkbox" class="switch" data-assistant-enable="${esc(m.id)}" ${g.enabled[m.id] ? "checked" : ""} aria-label="Cho chọn ${esc(m.assistant_name || m.name)}"></td><td>${m.assistant_thinking_mode === "enabled" ? '<span class="chip acc">Bật</span>' : m.assistant_thinking_mode === "disabled" ? '<span class="chip">Tắt</span>' : '<span class="chip">Mặc định</span>'}</td><td class="mono">${esc(m.assistant_reasoning_effort === "default" ? "—" : m.assistant_reasoning_effort || "—")}</td><td class="act"><button class="btn ghost sm" data-assistant-edit-model="${esc(m.id)}">${ico("edit")}Sửa</button></td></tr>`).join("");
    return `<header class="dt-head">${assistantIcon("global", true)}<div class="grow"><h3>Prompt &amp; model chung</h3><small class="muted">Thiết lập nền cho mọi trợ lý. Prompt riêng của từng trợ lý được nối sau prompt chung.</small></div></header>

  <div class="pb dt-body">

    <div class="dt-sec"><div class="dt-t"><b>System prompt chung</b><small>Đứng đầu mọi lượt gọi model của Trợ lý AI; không ảnh hưởng Chat Bot AI</small></div><textarea class="input mono" id="assistant-global-prompt" rows="5">${esc(g.prompt)}</textarea><small class="faint tnum" id="assistant-global-count">${g.prompt.length} ký tự</small></div>


    <div class="dt-sec"><div class="dt-t"><b>Model hiển thị cho người dùng</b><small>Danh sách trong ô chọn Model ở màn chat. Tên hiển thị và Core Model ID chỉ áp dụng cho Trợ lý AI.</small></div>

      ${models.length ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Tên hiển thị</th><th>Core model</th><th>Cho chọn</th><th>Thinking</th><th>Effort</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<div class="empty">Chưa có model. Thêm model ở mục Cấu hình AI.</div>'}</div>

    ${profilesNote()}

  </div>${assistantSaveBar()}`;
}
function assistantInfoTab(purpose: string) {
    const d = assistantDraft!, general = purpose === "assistant_general";
    const starters = d.starters.split("\n").map((x) => x.trim()).filter(Boolean).slice(0, 4);
    const preview = general
        ? `<div class="pv-gen">${assistantFace(purpose, 44)}<div><b>${esc(d.title)}</b><p class="muted" style="font-size:13px;margin:0">${esc(d.description)}</p></div></div>`
        : assistantCardPreview({ face: assistantFace(purpose, 44), illustration: assistantIllustration(purpose), title: d.title, description: d.description, requests: profileOf(purpose).stats?.requests || 0, hidden: !d.visible });
    return `<div class="dt-grid">

    <div class="dt-sec"><div class="dt-t"><b>Thẻ trên trang chủ</b><small>Người dùng thấy thẻ này ở mục Trợ lý cá nhân</small></div>

      <div class="form-grid">

        <label class="field"><span>Tên trợ lý</span><input class="input" data-assistant-field="title" value="${esc(d.title)}"></label>

        <label class="field"><span>Slogan</span><input class="input" data-assistant-field="slogan" value="${esc(d.slogan)}"></label>

        <label class="field full"><span>Mô tả ngắn</span><input class="input" data-assistant-field="description" maxlength="80" value="${esc(d.description)}"><small class="tnum" id="assistant-desc-count">${d.description.length}/80 ký tự</small></label>

        <label class="field full"><span>Lời chào khi mở phòng</span><textarea class="input" rows="2" data-assistant-field="greeting">${esc(d.greeting)}</textarea></label>

        <label class="field full"><span>Câu hỏi gợi ý</span><textarea class="input" rows="3" data-assistant-field="starters">${esc(d.starters)}</textarea><small>Mỗi dòng một câu, tối đa 4</small></label>

        ${general ? "" : `<label class="switchRow full"><span><b>Hiển thị trên trang chủ</b><br><small class="muted">Tắt để ẩn thẻ; phòng cũ vẫn mở được từ lịch sử</small></span><input type="checkbox" class="switch" data-assistant-field="visible" ${d.visible ? "checked" : ""}></label>`}

      </div></div>

    <div class="dt-sec"><div class="dt-t"><b>Xem trước</b><small>Cập nhật theo nội dung bạn nhập</small></div>

      <div id="assistant-preview">${preview}</div>

      <div class="starters asPreviewStarters">${starters.map((t) => `<button tabindex="-1" type="button">${esc(t)}</button>`).join("")}</div></div>

  </div>`;
}
function assistantModelTab(purpose: string) {
    const d = assistantDraft!, h = assistantHealth([d.main, d.f1, d.f2]);
    const slot = (field: "main" | "f1" | "f2", label: string, hint: string) => {
        const m = models.find((x) => x.id === d[field]);
        const st = !d[field] ? ["bad", "Chưa chọn"] : m && !m.assistant_enabled ? ["warn", "Model đang ẩn"] : ["ok", "Sẵn sàng"];
        return `<div class="slot ${st[0]}"><div class="slotHead"><b>${label}</b><span class="chip ${st[0]}">${st[1]}</span></div>${assistantModelSelect(`assistant-slot-${field}`, d[field])}<small class="faint">${hint}</small></div>`;
    };
    return `<div class="dt-sec"><div class="dt-t"><b>Chuỗi model</b><small>Hệ thống gọi model chính trước; lỗi hoặc quá thời gian chờ thì chuyển sang dự phòng theo thứ tự</small></div>

      <div class="chain">${slot("main", "1 · Model chính", "Xử lý mọi yêu cầu khi hoạt động bình thường")}<span class="arrow">${ico("angle-small-right")}</span>${slot("f1", "2 · Dự phòng 1", "Dùng khi model chính lỗi")}<span class="arrow">${ico("angle-small-right")}</span>${slot("f2", "3 · Dự phòng 2", "Dùng khi cả hai model trên lỗi")}</div>

      ${h.k !== "ok" ? `<div class="note-info" style="background:var(--${h.k}-soft)">${ico("info")}<span><b>${h.t}.</b> Nên cấu hình đủ 1 model chính và 2 dự phòng để tránh gián đoạn.</span></div>` : ""}</div>

    <div class="dt-grid">

      <div class="dt-sec"><div class="dt-t"><b>Tham số theo model</b><small>Temperature và giới hạn token lấy từ cấu hình của model thực sự được gọi, kể cả model dự phòng hoặc model user chọn.</small></div><p class="muted">Sửa các tham số trong Cấu hình AI → Sửa model.</p></div>

      ${purpose === "assistant_suggestion" ? "" : `<div class="dt-sec"><div class="dt-t"><b>Lựa chọn của người dùng</b></div>

        <label class="switchRow"><span>Cho người dùng chọn model trong phòng chat<br><small class="muted">Danh sách model lấy từ Cài đặt chung</small></span><input type="checkbox" class="switch" data-assistant-field="user_pick" ${d.user_pick ? "checked" : ""}></label></div>`}

    </div>`;
}
function assistantPromptPreview(purpose: string, prompt: string) {
    return `<span class="lbl-g">Chung</span>${esc(settings?.assistant_system_instruction || "(trống)")}<hr><span class="lbl-r">${esc(assistantName(purpose))}</span>${esc(prompt || "(prompt base trong code)")}`;
}
function assistantPromptTab(purpose: string) {
    const d = assistantDraft!;
    const vars = ["{{user_name}}", "{{language}}", "{{memories}}", "{{room_files}}", "{{today}}"];
    return `<div class="dt-grid">

      <div class="dt-sec"><div class="dt-t"><b>Prompt riêng của trợ lý</b><small>Nối sau prompt chung. Để trống thì hệ thống dùng prompt base trong code.</small></div>

        <textarea class="input mono" id="assistant-prompt-main" rows="8">${esc(d.prompt)}</textarea>

        <div class="promptTools"><div class="row" style="gap:4px">${vars.map((v) => `<button type="button" class="chip promptVar" data-assistant-var="${v}" title="Chèn biến">${v}</button>`).join("")}</div><small class="faint tnum" id="assistant-prompt-count">${d.prompt.length} ký tự</small></div>

        <div class="dt-t"><b>Prompt cho model dự phòng</b><small>Dùng khi hệ thống chuyển sang dự phòng</small></div>

        <label class="field"><span>Dự phòng 1</span><textarea class="input mono" id="assistant-prompt-f1" rows="3" ${d.f1 ? "" : 'disabled placeholder="Chưa chọn model dự phòng 1"'}>${esc(d.fp1)}</textarea></label>

        <label class="field"><span>Dự phòng 2</span><textarea class="input mono" id="assistant-prompt-f2" rows="3" ${d.f2 ? "" : 'disabled placeholder="Chưa chọn model dự phòng 2"'}>${esc(d.fp2)}</textarea></label></div>

      <div class="dt-sec"><div class="dt-t"><b>Prompt hoàn chỉnh gửi tới model</b><small>Chỉ xem</small></div>

        <div class="prompt-pv" id="assistant-prompt-preview">${assistantPromptPreview(purpose, d.prompt)}</div></div>

    </div>`;
}
function assistantStatsTab(purpose: string) {
    const st = profileOf(purpose).stats;
    if (!st)
        return `<div class="empty">Chưa có số liệu thống kê cho trợ lý này.</div>`;
    const max = Math.max(1, ...st.days);
    const labels = Array.from({ length: st.days.length }, (_, i) => {
        const day = new Date(Date.now() - (st.days.length - 1 - i) * 86400000).getDay();
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
    const d = assistantDraft!, h = assistantHealth([d.main, d.f1, d.f2]), task = purpose === "assistant_suggestion";
    const tabs: [
        AssistantTab,
        string
    ][] = [...(task ? [] : [["info", "Hiển thị"]] as [
            AssistantTab,
            string
        ][]), ["model", "Model & dự phòng"], ["prompt", "Prompt"], ["stats", "Thống kê"]];
    if (task && activeAssistantTab === "info")
        activeAssistantTab = "model";
    const body = activeAssistantTab === "info" ? assistantInfoTab(purpose) : activeAssistantTab === "model" ? assistantModelTab(purpose) : activeAssistantTab === "prompt" ? assistantPromptTab(purpose) : assistantStatsTab(purpose);
    const showNote = activeAssistantTab === "info" || activeAssistantTab === "stats" || (activeAssistantTab === "model");
    return `<header class="dt-head">${assistantIcon(purpose)}<div class="grow" style="min-width:0"><h3>${esc(task ? assistantName(purpose) : d.title)}</h3><small class="muted">${esc(task ? assistantDesc(purpose) : d.description)}</small></div><span class="chip ${h.k}">${h.n}/3 model · ${h.t}</span></header>

    <div class="dt-tabs"><div class="tabs" role="tablist">${tabs.map(([t, l]) => `<button role="tab" aria-selected="${activeAssistantTab === t}" data-assistant-detail-tab="${t}">${l}</button>`).join("")}</div></div>

    <div class="pb dt-body">${body}${showNote ? profilesNote() : ""}</div>${activeAssistantTab === "stats" ? "" : assistantSaveBar()}`;
}
function renderAssistantSettings() {
    const host = document.querySelector("#assistant-config")!;
    const purpose = activeAssistantPurpose;
    if (!assistantDirty) {
        if (purpose === "global")
            assistantGlobalDraft = loadGlobalDraft();
        else
            assistantDraft = loadAssistantDraft(purpose);
    }
    const all = [...userAssistants(), "assistant_suggestion"];
    const issues = all.filter((p) => savedHealth(p).k !== "ok").length;
    const item = (p: string) => {
        const h = savedHealth(p), hidden = p !== "assistant_suggestion" && !profileOf(p).visible;
        return `<button class="tl-item" data-assistant-select="${esc(p)}" aria-current="${purpose === p}">${assistantIcon(p)}<span class="grow" style="min-width:0"><b>${esc(assistantName(p))}</b><small>${hidden ? "Đang ẩn · " : ""}${esc(purposeModel(p)?.assistant_name || "—")}</small></span><span class="dot ${h.k}" title="${h.t}"></span></button>`;
    };
    host.innerHTML = `<div class="as-cms">

    <aside class="panel tl">

      <button class="btn pri tl-create" id="assistant-create-open" ${assistantProfilesAvailable ? "" : 'disabled title="Backend chưa hỗ trợ tạo trợ lý"'}>${ico("plus")}Tạo trợ lý AI</button>

      <div class="tl-sum ${issues ? "warn" : "ok"}">${ico(issues ? "info" : "check")}<span>${issues ? `<b>${issues}/${all.length}</b> mục cần chú ý về model` : "Tất cả trợ lý đã đủ model"}</span></div>

      <div class="tl-grp">Cài đặt chung</div>

      <button class="tl-item" data-assistant-select="global" aria-current="${purpose === "global"}">${assistantIcon("global")}<span class="grow"><b>Prompt &amp; model chung</b><small>Áp dụng cho mọi trợ lý</small></span></button>

      <div class="tl-grp">Trợ lý hiển thị cho người dùng</div>

      ${userAssistants().map(item).join("")}

      <div class="tl-grp">Tác vụ nền</div>

      ${item("assistant_suggestion")}

      <div class="tl-legend"><span><i class="dot ok"></i>Đủ model</span><span><i class="dot warn"></i>Thiếu dự phòng</span><span><i class="dot bad"></i>Thiếu nghiêm trọng</span></div>

    </aside>

    <section class="panel tl-detail">${purpose === "global" ? assistantGlobalView() : assistantDetailView(purpose)}</section>

  </div>

  ${cmsModal("modal-assistant-model", "Sửa model của Trợ lý AI", "Model hiển thị", `<div class="fields"><label class="field">Tên hiển thị trên Assistant<input id="assistant-model-name"/></label><label class="field">Core Model ID trên Assistant<input id="assistant-model-core"/></label><label class="field">Thinking mode<select id="assistant-model-thinking"><option value="default">Theo mặc định gateway</option><option value="enabled">Bật</option><option value="disabled">Tắt</option></select></label><label class="field">Reasoning effort<select id="assistant-model-effort"><option value="default">Theo mặc định gateway</option><option value="low">Low</option><option value="high">High</option><option value="max">Max</option></select></label><label class="check full"><input id="assistant-model-enabled" type="checkbox"/> Cho phép chọn trên client</label></div>`, `<span class="statusText" id="assistant-model-editor-status">Không thay đổi Chat Bot AI</span><button class="btn" data-close>Hủy</button><button class="btn pri" id="save-assistant-model-editor">Lưu model</button>`, false)}

  <div class="scrim" id="modal-assistant-create" hidden><section class="dialog naDialog" role="dialog" aria-modal="true" aria-label="Tạo trợ lý AI"><header><h3>Tạo trợ lý AI</h3><button class="iconbtn" data-close aria-label="Đóng">${ico("cross-small")}</button></header><div class="body" id="assistant-create-body"></div><footer><span class="statusText" id="assistant-create-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="assistant-create-save">${ico("plus")}Tạo trợ lý</button></footer></section></div>`;
    bindAssistantSettings();
}
function markAssistantDirty() {
    if (assistantDirty)
        return;
    assistantDirty = true;
    const bar = document.querySelector<HTMLElement>("#assistant-config .savebar");
    if (!bar)
        return;
    bar.classList.add("on");
    bar.querySelector("#assistant-save-status")!.innerHTML = `${ico("info")} Có thay đổi chưa lưu`;
    bar.querySelectorAll<HTMLButtonElement>("button").forEach((b) => (b.disabled = false));
}
function confirmLeaveAssistant() {
    return !assistantDirty || confirm("Bỏ các thay đổi chưa lưu?");
}
function refreshAssistantPreview() {
    const d = assistantDraft!, purpose = activeAssistantPurpose, host = document.querySelector("#assistant-config")!;
    const preview = host.querySelector("#assistant-preview");
    if (preview)
        preview.innerHTML = purpose === "assistant_general"
            ? `<div class="pv-gen">${assistantFace(purpose, 44)}<div><b>${esc(d.title)}</b><p class="muted" style="font-size:13px;margin:0">${esc(d.description)}</p></div></div>`
            : assistantCardPreview({ face: assistantFace(purpose, 44), illustration: assistantIllustration(purpose), title: d.title, description: d.description, requests: profileOf(purpose).stats?.requests || 0, hidden: !d.visible });
    const starters = host.querySelector(".asPreviewStarters");
    if (starters)
        starters.innerHTML = d.starters.split("\n").map((x) => x.trim()).filter(Boolean).slice(0, 4).map((t) => `<button tabindex="-1" type="button">${esc(t)}</button>`).join("");
    const count = host.querySelector("#assistant-desc-count");
    if (count)
        count.textContent = `${d.description.length}/80 ký tự`;
    const head = host.querySelector(".dt-head h3"), sub = host.querySelector(".dt-head small");
    if (head && purpose !== "assistant_suggestion")
        head.textContent = d.title;
    if (sub && purpose !== "assistant_suggestion")
        sub.textContent = d.description;
}
function bindAssistantSettings() {
    const host = document.querySelector("#assistant-config")!;
    const on = <T extends HTMLElement>(sel: string, ev: string, fn: (el: T) => void) => host.querySelectorAll<T>(sel).forEach((el) => el.addEventListener(ev, () => fn(el)));
    on<HTMLButtonElement>("[data-assistant-select]", "click", (el) => {
        if (el.dataset.assistantSelect === activeAssistantPurpose || !confirmLeaveAssistant())
            return;
        assistantDirty = false;
        activeAssistantPurpose = el.dataset.assistantSelect!;
        activeAssistantTab = activeAssistantPurpose === "assistant_suggestion" ? "model" : "info";
        renderAssistantSettings();
    });
    on<HTMLButtonElement>("[data-assistant-detail-tab]", "click", (el) => {
        activeAssistantTab = el.dataset.assistantDetailTab as AssistantTab;
        renderAssistantSettings();
    });
    // Cài đặt chung
    on<HTMLTextAreaElement>("#assistant-global-prompt", "input", (el) => {
        assistantGlobalDraft!.prompt = el.value;
        host.querySelector("#assistant-global-count")!.textContent = `${el.value.length} ký tự`;
        markAssistantDirty();
    });
    on<HTMLInputElement>("[data-assistant-enable]", "change", (el) => {
        assistantGlobalDraft!.enabled[el.dataset.assistantEnable!] = el.checked;
        markAssistantDirty();
    });
    on<HTMLButtonElement>("[data-assistant-edit-model]", "click", (el) => openAssistantModelEditor(el.dataset.assistantEditModel!));
    // Hiển thị & tham số
    on<HTMLInputElement | HTMLTextAreaElement>("[data-assistant-field]", "input", (el) => {
        const d = assistantDraft! as unknown as Record<string, unknown>, key = el.dataset.assistantField!;
        if (el instanceof HTMLInputElement && el.type === "checkbox")
            d[key] = el.checked;
        else if (el instanceof HTMLInputElement && (el.type === "range" || el.type === "number"))
            d[key] = Number(el.value);
        else
            d[key] = el.value;
        refreshAssistantPreview();
        markAssistantDirty();
    });
    // Chuỗi model
    (["main", "f1", "f2"] as const).forEach((field) => on<HTMLSelectElement>(`#assistant-slot-${field}`, "change", (el) => {
        const d = assistantDraft!, purpose = activeAssistantPurpose;
        d[field] = el.value;
        const model = models.find((m) => m.id === el.value);
        if (field === "main")
            d.prompt = assistantPromptOf(model, purpose + "_instruction");
        if (field === "f1")
            d.fp1 = assistantPromptOf(model, purpose + "_fallback_instruction");
        if (field === "f2")
            d.fp2 = assistantPromptOf(model, purpose + "_fallback_2_instruction");
        markAssistantDirty();
        renderAssistantSettings();
    }));
    // Prompt
    const updateMainPrompt = (value: string) => {
        assistantDraft!.prompt = value;
        host.querySelector("#assistant-prompt-count")!.textContent = `${value.length} ký tự`;
        host.querySelector("#assistant-prompt-preview")!.innerHTML = assistantPromptPreview(activeAssistantPurpose, value);
        markAssistantDirty();
    };
    on<HTMLTextAreaElement>("#assistant-prompt-main", "input", (el) => updateMainPrompt(el.value));
    on<HTMLButtonElement>("[data-assistant-var]", "click", (el) => {
        const area = host.querySelector<HTMLTextAreaElement>("#assistant-prompt-main")!;
        const at = area.selectionStart ?? area.value.length;
        area.value = area.value.slice(0, at) + el.dataset.assistantVar + area.value.slice(area.selectionEnd ?? at);
        area.focus();
        updateMainPrompt(area.value);
    });
    on<HTMLTextAreaElement>("#assistant-prompt-f1", "input", (el) => { assistantDraft!.fp1 = el.value; markAssistantDirty(); });
    on<HTMLTextAreaElement>("#assistant-prompt-f2", "input", (el) => { assistantDraft!.fp2 = el.value; markAssistantDirty(); });
    // Thanh lưu
    on<HTMLButtonElement>("#assistant-discard", "click", () => { assistantDirty = false; renderAssistantSettings(); });
    on<HTMLButtonElement>("#assistant-save", "click", () => void saveAssistantSettings());
    on<HTMLButtonElement>("#save-assistant-model-editor", "click", () => void saveAssistantModelEditor());
    // Tạo trợ lý mới
    on<HTMLButtonElement>("#assistant-create-open", "click", () => openAssistantCreate());
    on<HTMLButtonElement>("#assistant-create-save", "click", () => void createAssistant());
}
let editingAssistantModel = "";
function openAssistantModelEditor(id: string) {
    const model = models.find((x) => x.id === id);
    if (!model)
        return;
    editingAssistantModel = id;
    const value = (sel: string, v: string) => ((document.querySelector(sel) as HTMLInputElement | HTMLSelectElement).value = v);
    value("#assistant-model-name", model.assistant_name);
    value("#assistant-model-core", model.assistant_model_id);
    value("#assistant-model-thinking", model.assistant_thinking_mode || "default");
    value("#assistant-model-effort", model.assistant_reasoning_effort || "default");
    document.querySelector<HTMLInputElement>("#assistant-model-enabled")!.checked = model.assistant_enabled;
    openCmsModal("modal-assistant-model");
}
async function saveAssistantModelEditor() {
    const status = document.querySelector("#assistant-model-editor-status")!;
    if (!editingAssistantModel)
        return;
    status.textContent = "Đang lưu…";
    mountLoadingCat(status, "inline");
    status.className = "statusText";
    const field = (sel: string) => (document.querySelector(sel) as HTMLInputElement | HTMLSelectElement).value;
    try {
        await request(`/v1/admin/assistant-models/${editingAssistantModel}`, {
            method: "PATCH",
            body: JSON.stringify({
                name: field("#assistant-model-name"),
                model_id: field("#assistant-model-core"),
                enabled: document.querySelector<HTMLInputElement>("#assistant-model-enabled")!.checked,
                thinking_mode: field("#assistant-model-thinking"),
                reasoning_effort: field("#assistant-model-effort"),
            }),
        });
        models = await request<ModelConfig[]>("/v1/admin/models");
        assistantDirty = false;
        renderAssistantSettings();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
async function saveAssistantSettings() {
    const status = document.querySelector<HTMLElement>("#assistant-save-status");
    if (status)
        status.textContent = "Đang lưu…";
    try {
        if (activeAssistantPurpose === "global") {
            const g = assistantGlobalDraft!;
            settings = await request<Settings>("/v1/admin/settings", { method: "PUT", body: JSON.stringify({ assistant_system_instruction: g.prompt }) });
            for (const model of models.filter((m) => g.enabled[m.id] !== m.assistant_enabled))
                await request(`/v1/admin/assistant-models/${model.id}`, {
                    method: "PATCH",
                    body: JSON.stringify({ name: model.assistant_name, model_id: model.assistant_model_id, enabled: g.enabled[model.id], thinking_mode: model.assistant_thinking_mode, reasoning_effort: model.assistant_reasoning_effort }),
                });
        }
        else {
            const d = assistantDraft!, purpose = activeAssistantPurpose;
            await request(`/v1/admin/assistant-purposes/${encodeURIComponent(purpose)}`, {
                method: "PUT",
                body: JSON.stringify({
                    primary_model_id: d.main || null,
                    fallback_model_id: d.f1 || null,
                    fallback_2_model_id: d.f2 || null,
                    primary_prompt: d.prompt,
                    fallback_prompt: d.fp1,
                    fallback_2_prompt: d.fp2,
                }),
            });
            if (assistantProfilesAvailable)
                await request(`/v1/admin/assistant-profiles/${encodeURIComponent(purpose)}`, {
                    method: "PUT",
                    body: JSON.stringify({
                        title: d.title, slogan: d.slogan, description: d.description, greeting: d.greeting,
                        starters: d.starters.split("\n").map((x) => x.trim()).filter(Boolean).slice(0, 4),
                        visible: d.visible, user_pick: d.user_pick,
                    }),
                });
        }
        models = await request<ModelConfig[]>("/v1/admin/models");
        await loadAssistantProfiles();
        assistantDirty = false;
        renderModels();
        renderSettings();
        renderAssistantSettings();
    }
    catch (error) {
        if (status) {
            status.textContent = String(error);
            status.className = "statusText error";
        }
    }
}
/* Hộp thoại tạo trợ lý AI */
type NewAssistantForm = {
    title: string;
    slogan: string;
    description: string;
    greeting: string;
    icon: string;
    hue: number;
    hair: number;
    main: string;
    f1: string;
    prompt: string;
    visible: boolean;
};
let newAssistant: NewAssistantForm = { title: "", slogan: "", description: "", greeting: "", icon: "sparkles", hue: 172, hair: 0, main: "", f1: "", prompt: "", visible: true };
function renderAssistantCreate() {
    const f = newAssistant, body = document.querySelector("#assistant-create-body")!;
    const options = (selected: string, empty: string, enabledOnly: boolean) => `<option value="">${empty}</option>${models.filter((m) => !enabledOnly || m.assistant_enabled).map((m) => `<option value="${esc(m.id)}" ${m.id === selected ? "selected" : ""} ${m.assistant_enabled ? "" : "disabled"}>${esc(m.assistant_name || m.name)}${m.assistant_enabled ? "" : " (đang ẩn)"}</option>`).join("")}`;
    body.innerHTML = `<div class="na-grid">

    <div class="stack" style="gap:14px">

      <div class="dt-t"><b>1. Thông tin hiển thị</b><small>Người dùng thấy ở mục Trợ lý cá nhân</small></div>

      <div class="form-grid">

        <label class="field"><span>Tên trợ lý *</span><input class="input" data-na="title" value="${esc(f.title)}" placeholder="VD: Ngoại ngữ"></label>

        <label class="field"><span>Slogan</span><input class="input" data-na="slogan" value="${esc(f.slogan)}" placeholder="VD: Mỗi ngày một câu"></label>

        <label class="field full"><span>Mô tả ngắn *</span><input class="input" data-na="description" maxlength="80" value="${esc(f.description)}" placeholder="VD: Luyện nói và sửa lỗi tiếng Anh"><small class="tnum" id="na-desc-count">${f.description.length}/80</small></label>

        <label class="field full"><span>Lời chào khi mở phòng</span><textarea class="input" rows="2" data-na="greeting">${esc(f.greeting)}</textarea></label>

      </div>

      <div class="field"><span>Biểu tượng minh họa</span><div class="pick-row">${ASSISTANT_ICONS.map(([k, l]) => `<button type="button" class="ipick" data-na-icon="${k}" aria-pressed="${f.icon === k}" title="${l}">${ico(k)}</button>`).join("")}</div></div>

      <div class="field"><span>Màu chủ đạo</span><div class="pick-row">${ASSISTANT_HUES.map((h) => `<button type="button" class="cpick" data-na-hue="${h}" aria-pressed="${f.hue === h}" style="background:hsl(${h} 55% 52%)" aria-label="Màu ${h}"></button>`).join("")}<button type="button" class="btn sm ghost" id="na-hair">${ico("refresh")}Đổi ảnh đại diện</button></div></div>

      <div class="dt-t" style="margin-top:6px"><b>2. Model &amp; prompt</b><small>Có thể cấu hình chi tiết sau khi tạo</small></div>

      <div class="form-grid">

        <label class="field"><span>Model chính *</span><select class="input" data-na-select="main">${options(f.main, "— Chọn model —", false)}</select></label>

        <label class="field"><span>Dự phòng 1</span><select class="input" data-na-select="f1">${options(f.f1, "— Chưa chọn —", true)}</select></label>

        <label class="field full"><span>Prompt riêng *</span><textarea class="input mono" rows="3" data-na="prompt" placeholder="Vai trò, giọng điệu, giới hạn của trợ lý…">${esc(f.prompt)}</textarea></label>

        <label class="switchRow full"><span><b>Hiển thị ngay trên trang chủ</b><br><small class="muted">Tắt nếu muốn hoàn thiện cấu hình trước khi ra mắt</small></span><input type="checkbox" class="switch" id="na-visible" ${f.visible ? "checked" : ""}></label>

      </div>

    </div>

    <div class="stack na-pv" style="gap:10px"><div class="dt-t"><b>Xem trước</b><small>Thẻ trên trang chủ Trợ lý AI</small></div><div id="na-preview"></div></div>

  </div>`;
    const refresh = () => {
        body.querySelector("#na-preview")!.innerHTML = assistantCardPreview({ face: faceSvg(f.hue, HAIRS[f.hair], 44), illustration: illustrationHtml("custom", f.hue, f.icon), title: f.title || "Trợ lý mới", description: f.description, requests: 0, hidden: !f.visible });
        body.querySelector("#na-desc-count")!.textContent = `${f.description.length}/80`;
    };
    refresh();
    body.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("[data-na]").forEach((el) => el.addEventListener("input", () => { (f as unknown as Record<string, string>)[el.dataset.na!] = el.value; refresh(); }));
    body.querySelectorAll<HTMLSelectElement>("[data-na-select]").forEach((el) => el.addEventListener("change", () => { (f as unknown as Record<string, string>)[el.dataset.naSelect!] = el.value; }));
    body.querySelector<HTMLInputElement>("#na-visible")!.addEventListener("change", (e) => { f.visible = (e.target as HTMLInputElement).checked; refresh(); });
    body.querySelectorAll<HTMLButtonElement>("[data-na-icon]").forEach((el) => el.addEventListener("click", () => { f.icon = el.dataset.naIcon!; renderAssistantCreate(); }));
    body.querySelectorAll<HTMLButtonElement>("[data-na-hue]").forEach((el) => el.addEventListener("click", () => { f.hue = Number(el.dataset.naHue); renderAssistantCreate(); }));
    body.querySelector("#na-hair")!.addEventListener("click", () => { f.hair = (f.hair + 1) % HAIRS.length; refresh(); });
}
function openAssistantCreate() {
    newAssistant = { title: "", slogan: "", description: "", greeting: "", icon: "sparkles", hue: 172, hair: 0, main: "", f1: "", prompt: "", visible: true };
    const status = document.querySelector("#assistant-create-status")!;
    status.textContent = "";
    status.className = "statusText";
    renderAssistantCreate();
    openCmsModal("modal-assistant-create");
}
async function createAssistant() {
    const f = newAssistant, status = document.querySelector("#assistant-create-status")!;
    const missing = !f.title.trim() ? "Nhập tên trợ lý." : !f.description.trim() ? "Nhập mô tả ngắn." : !f.main ? "Chọn model chính." : !f.prompt.trim() ? "Nhập prompt riêng." : "";
    status.className = missing ? "statusText error" : "statusText";
    if (missing)
        return void (status.textContent = missing);
    status.textContent = "Đang tạo…";
    try {
        const created = await request<{
            id: string;
        }>("/v1/admin/assistant-profiles", {
            method: "POST",
            body: JSON.stringify({ title: f.title.trim(), slogan: f.slogan, description: f.description.trim(), greeting: f.greeting, icon: f.icon, hue: f.hue, hair: f.hair, visible: f.visible }),
        });
        await request(`/v1/admin/assistant-purposes/${encodeURIComponent(created.id)}`, {
            method: "PUT",
            body: JSON.stringify({ primary_model_id: f.main, fallback_model_id: f.f1 || null, fallback_2_model_id: null, primary_prompt: f.prompt, fallback_prompt: "", fallback_2_prompt: "" }),
        });
        models = await request<ModelConfig[]>("/v1/admin/models");
        await loadAssistantProfiles();
        (document.querySelector("#modal-assistant-create") as HTMLElement).hidden = true;
        assistantDirty = false;
        activeAssistantPurpose = created.id;
        activeAssistantTab = "info";
        renderAssistantSettings();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
/* ---------- Phân công model (theo admAssign của prototype) ---------- */
const ASSIGN_TASKS: [
    string,
    string,
    string
][] = [
    ["response", "Trả lời", "Model chính trả lời người dùng trong Chat Bot AI"],
    ["suggestion", "Gợi ý", "Tạo các lựa chọn trả lời nhanh"],
    ["suggestion_fallback", "Gợi ý · dự phòng 1", "Dùng khi model gợi ý chính lỗi"],
    ["suggestion_fallback_2", "Gợi ý · dự phòng 2", "Dùng khi hai model gợi ý trước đều lỗi"],
    ["compiler", "Tạo nhân vật", "Tóm tắt mô tả và biên dịch CharacterSpec"],
    ["moderation", "Kiểm duyệt", "Phân tích an toàn nội dung và ngữ cảnh"],
    ["fallback", "Dự phòng hội thoại · lớp 1", "Trả lời khi model chính không khả dụng"],
    ["fallback_2", "Dự phòng hội thoại · lớp 2", "Trả lời khi model chính và lớp 1 đều lỗi"],
    ["avatar_image", "Tạo avatar biểu cảm", "Chỉnh ảnh nguồn thành chân dung và sinh bộ nét mặt"],
    ["emotion", "Nhận diện cảm xúc", "Phân loại cảm xúc của câu trả lời"],
    ["emotion_fallback", "Nhận diện cảm xúc · dự phòng 1", "Dùng khi model cảm xúc chính lỗi"],
    ["emotion_fallback_2", "Nhận diện cảm xúc · dự phòng 2", "Dùng khi hai model cảm xúc trước đều lỗi"],
    ["tts", "Phát giọng nói TTS", "Gọi /audio/speech khi người dùng bấm Nghe"],
];
function assignmentState(modelId: string) {
    const m = models.find((x) => x.id === modelId);
    return !m ? ["bad", "Chưa gán"] : !m.enabled ? ["warn", "Model đang ẩn"] : ["ok", "Sẵn sàng"];
}
function renderSettings() {
    const host = document.querySelector("#settings");
    if (!host)
        return;
    const rows = ASSIGN_TASKS.map(([purpose, label, hint]) => {
        const current = assignmentValue(purpose), [kind, text] = assignmentState(current);
        return `<tr><td><b>${label}</b><br><small class="faint">${hint}</small></td><td style="min-width:220px"><select class="input sm" id="purpose-${purpose}" data-assign="${purpose}">${modelOptions(current, true)}</select></td><td><span class="chip ${kind}" id="assign-state-${purpose}">${text}</span></td><td class="act"><button class="iconbtn" data-assign-edit="${purpose}" title="Cấu hình model" aria-label="Cấu hình model của ${label}" ${current ? "" : "disabled"}>${ico("settings-sliders")}</button></td></tr>`;
    }).join("");
    host.innerHTML = `<section class="panel"><header><div><h3>Gán model cho tác vụ</h3><small class="faint">Prompt và tham số chỉnh trong Cấu hình AI của từng model</small></div><div class="row"><span class="statusText" id="assignment-status"></span><button class="btn pri" id="save-assignments">Lưu và áp dụng</button></div></header>

    <div class="tbl-wrap"><table class="dt"><thead><tr><th>Tác vụ</th><th>Model</th><th>Trạng thái</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
    host.querySelector("#save-assignments")?.addEventListener("click", saveModelAssignments);
    host.querySelectorAll<HTMLSelectElement>("[data-assign]").forEach((s) => s.addEventListener("change", () => {
        const [kind, text] = assignmentState(s.value), chip = host.querySelector(`#assign-state-${s.dataset.assign}`)!;
        chip.className = `chip ${kind}`;
        chip.textContent = text;
        (host.querySelector(`[data-assign-edit="${s.dataset.assign}"]`) as HTMLButtonElement).disabled = !s.value;
        const status = host.querySelector("#assignment-status")!;
        status.textContent = "Có thay đổi chưa lưu";
        status.className = "statusText";
    }));
    host.querySelectorAll<HTMLButtonElement>("[data-assign-edit]").forEach((b) => b.addEventListener("click", () => openAssignedModelEditor((host.querySelector(`#purpose-${b.dataset.assignEdit}`) as HTMLSelectElement).value)));
}
function openAssignedModelEditor(id: string) {
    if (!id)
        return;
    document.querySelector<HTMLButtonElement>('[data-view="models"]')?.click();
    modelsTab = "models";
    renderModels();
    editingModelId = id;
    fillModelEditor();
    openCmsModal("modal-model-edit");
}
async function saveModelAssignments() {
    const status = document.querySelector("#assignment-status")!;
    status.textContent = "Đang lưu…";
    status.className = "statusText";
    const purposes = ASSIGN_TASKS.map(([purpose]) => purpose);
    const selected = Object.fromEntries(purposes.map((p) => [p, document.querySelector<HTMLSelectElement>(`#purpose-${p}`)!.value]));
    mountLoadingCat(status, "inline");
    try {
        let generation: ModelUpdate["expression_generation"];
        for (const model of models) {
            const preserved = model.purposes.filter((p) => !purposes.includes(p));
            const assigned = [...preserved, ...purposes.filter((p) => selected[p] === model.id)];
            const updated = await request<ModelUpdate>(`/v1/admin/models/${model.id}`, {
                method: "PATCH",
                body: JSON.stringify({ purposes: assigned, enabled: assigned.length ? true : model.enabled }),
            });
            if (updated.expression_generation)
                generation = updated.expression_generation;
        }
        if (generation)
            showGenerationNotice(generation);
        models = await request<ModelConfig[]>("/v1/admin/models");
        renderModels();
        renderSettings();
        renderAssistantSettings();
        const done = document.querySelector("#assignment-status");
        if (done)
            done.textContent = "Đã lưu và áp dụng";
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
/* ---------- Logchat và Nhật ký hoạt động (theo admLog / admActivity của prototype) ---------- */
type LogRow = Record<string, unknown>;
let logchatProduct = "all";
let logchatGateway = "";
const LOGCHAT_PAGE_SIZE = 100;
let logchatOffset = 0;
let logchatRequestVersion = 0;
let logchatRows: LogRow[] = [];
let actionRows: LogRow[] = [];
const logText = (value: unknown) => (value === null || value === undefined ? "" : String(value));
const shortTime = (value: unknown, withSeconds = true) => {
    const date = new Date(logText(value));
    if (Number.isNaN(date.getTime()))
        return logText(value) || "—";
    const today = new Date().toDateString() === date.toDateString();
    const time = date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", ...(withSeconds ? { second: "2-digit" } : {}) });
    return today ? time : `${date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })} ${time}`;
};
const truthy = (value: unknown) => ["true", "có", "yes", "1"].includes(logText(value).trim().toLowerCase());
const usable = (value: unknown) => {
    const v = logText(value).trim();
    return v && !/^(không phân công|chưa ghi nhận|—|-)$/i.test(v) ? v : "";
};
function logModelName(value: unknown, configId: unknown, product: unknown): string {
    const raw = usable(value);
    if (!raw) return "";
    const assistant = logText(product) === "assistant";
    const savedId = logText(configId).trim();
    const byId = models.find((item) => item.id === (savedId || raw));
    if (savedId && !byId) return raw;
    const matches = byId ? [byId] : models.filter((item) => (assistant ? item.assistant_model_id || item.model_id : item.model_id) === raw);
    if (matches.length !== 1) return raw;
    const item = matches[0];
    return (assistant ? item.assistant_name || item.name : item.name) || raw;
}
const PRODUCT_LABELS: Record<string, string> = { roleplay: "Chat Bot AI", assistant: "Trợ lý AI" };
/** Hộp thoại xem toàn bộ trường của một dòng log. */
function logSpeakerCell(row: LogRow) {
  const mode = logText(row.assistant_mode);
  if (mode) return `<div class="row ovName">${assistantFace(mode, 26)}<span>${esc(assistantName(mode))}</span></div>`;
  const name = logText(row.character_name), avatar = logText(row.character_avatar_url);
  if (!name) return '<span class="faint">—</span>';
  return `<div class="row ovName">${avatar ? `<img class="ovAvatar" src="${esc(avatar)}" alt="">` : initialAvatar(name)}<span>${esc(name)}</span></div>`;
}
function logDetailHtml(row: LogRow, columns: string[]) {
    const timingLabels: Record<string, string> = {
        server_prepare_ms: "Chuẩn bị trên server (ms)",
        gateway_headers_ms: "Gateway: nhận header (ms)",
        gateway_first_chunk_ms: "Gateway: chunk nội dung đầu (ms)",
    };
    return `<div class="kvs logKvs">${columns.map((c) => `<div class="kv"><span class="mono" title="${esc(c)}">${esc(timingLabels[c] || c)}</span><span>${esc(logText(row[c])) || '<span class="faint">—</span>'}</span></div>`).join("")}</div>`;
}
let logchatColumns: string[] = [];
let actionColumns: string[] = [];
async function loadLogChatGateways() {
    const select = document.querySelector<HTMLSelectElement>("#logchat-gateway");
    if (!select) return;
    const gateways = await request<string[]>(`/v1/admin/chat-log-gateways?product=${encodeURIComponent(logchatProduct)}`);
    select.innerHTML = `<option value="">Mọi gateway</option><option value="__unknown__">Chưa ghi nhận gateway</option>${gateways.map((base) => `<option value="${esc(base)}">${esc(base.replace(/^https?:\/\//, ""))}</option>`).join("")}`;
    select.value = logchatGateway;
}
async function renderConversations() {
    const host = document.querySelector("#conversations");
    if (!host)
        return;
    host.innerHTML = `<section class="panel"><header><div class="row"><div class="pills" id="logchat-product">${[["all", "Tất cả"], ["roleplay", "Chat Bot AI"], ["assistant", "Trợ lý AI"]].map(([k, v]) => `<button type="button" data-product="${k}" aria-pressed="${logchatProduct === k}">${v}</button>`).join("")}</div><span class="chip tnum" id="logchat-count">…</span></div><input class="input logSearch" id="logchat-search" placeholder="Từ khóa: user, nội dung, model, gateway, phòng"><select class="input" id="logchat-gateway" aria-label="Lọc gateway"><option value="">Mọi gateway</option></select><button type="button" class="btn sm" id="logchat-export">Xuất CSV</button><span class="faint" id="logchat-export-status" role="status"></span></header><div class="row" style="padding:12px 16px;gap:12px;flex-wrap:wrap">
<label>Số log tải về <input class="input" id="logchat-export-count" type="number" min="1" step="1" placeholder="Tất cả" style="width:130px"></label>
<label>Khoảng ngày <select class="input" id="logchat-export-period"><option value="all">Tất cả thời gian</option><option value="today">Hôm nay</option><option value="7">7 ngày gần đây</option><option value="30">30 ngày gần đây</option><option value="custom">Tự chọn</option></select></label>
<label>Từ ngày <input class="input" type="date" id="logchat-export-from"></label>
<label>Đến ngày <input class="input" type="date" id="logchat-export-to"></label>
<small class="faint">Ngày theo giờ Việt Nam. Để trống số lượng để lấy tất cả; có giới hạn sẽ lấy log mới nhất theo bộ lọc.</small>
</div><div id="logchat-grid"><p class="empty" style="margin:14px">Đang tải…</p></div><div class="row" style="justify-content:flex-end;padding:12px 16px;gap:10px"><button type="button" class="btn ghost sm" id="logchat-newer">Mới hơn</button><span class="faint" id="logchat-page">Trang 1</span><button type="button" class="btn ghost sm" id="logchat-older">Cũ hơn</button></div></section>${cmsModal("modal-log-detail", "Chi tiết", "Log", `<div id="log-detail-body"></div>`, `<button class="btn" data-close>Đóng</button>`)}`;
    host.querySelectorAll<HTMLButtonElement>("[data-product]").forEach((b) => b.addEventListener("click", () => {
        logchatProduct = b.dataset.product!;
        logchatGateway = "";
        logchatOffset = 0;
        host.querySelectorAll<HTMLButtonElement>("[data-product]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        void loadLogChatGateways().then(loadChatLogs);
    }));
    host.querySelector<HTMLSelectElement>("#logchat-gateway")?.addEventListener("change", (event) => {
        logchatGateway = (event.currentTarget as HTMLSelectElement).value;
        logchatOffset = 0;
        void loadChatLogs();
    });
    let timer = 0;
    host.querySelector("#logchat-search")?.addEventListener("input", () => {
        window.clearTimeout(timer);
        logchatOffset = 0;
        timer = window.setTimeout(() => void loadChatLogs(), 300);
    });
    host.querySelector("#logchat-newer")?.addEventListener("click", () => { logchatOffset = Math.max(0, logchatOffset - LOGCHAT_PAGE_SIZE); void loadChatLogs(); });
    host.querySelector("#logchat-older")?.addEventListener("click", () => { logchatOffset += LOGCHAT_PAGE_SIZE; void loadChatLogs(); });
    const fromDate = host.querySelector<HTMLInputElement>("#logchat-export-from")!;
    const toDate = host.querySelector<HTMLInputElement>("#logchat-export-to")!;
    const period = host.querySelector<HTMLSelectElement>("#logchat-export-period")!;
    const vietnamDate = (value: Date) => {
        const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(value);
        const part = (type: string) => parts.find((item) => item.type === type)!.value;
        return `${part("year")}-${part("month")}-${part("day")}`;
    };
    period.addEventListener("change", () => {
        if (period.value === "custom") return;
        if (period.value === "all") { fromDate.value = ""; toDate.value = ""; return; }
        const today = vietnamDate(new Date());
        toDate.value = today;
        const first = new Date(today + "T00:00:00+07:00");
        first.setTime(first.getTime() - (period.value === "today" ? 0 : Number(period.value) - 1) * 86400000);
        fromDate.value = vietnamDate(first);
    });
    [fromDate, toDate].forEach((input) => input.addEventListener("change", () => { period.value = "custom"; }));
    host.querySelector<HTMLButtonElement>("#logchat-export")?.addEventListener("click", async (event) => {
        const button = event.currentTarget as HTMLButtonElement;
        const status = host.querySelector<HTMLElement>("#logchat-export-status")!;
        const params = new URLSearchParams({
            product: logchatProduct, gateway: logchatGateway,
            q: host.querySelector<HTMLInputElement>("#logchat-search")!.value.trim(),
        });
        const countInput = host.querySelector<HTMLInputElement>("#logchat-export-count")!;
        const count = countInput.value.trim();
        if (count && (!countInput.checkValidity() || !Number.isSafeInteger(Number(count)) || Number(count) < 1)) {
            status.textContent = "Số log phải là số nguyên lớn hơn 0."; return;
        }
        if (fromDate.value && toDate.value && fromDate.value > toDate.value) {
            status.textContent = "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc."; return;
        }
        if (count) params.set("max_rows", count);
        if (fromDate.value) params.set("start_date", fromDate.value);
        if (toDate.value) params.set("end_date", toDate.value);
        button.disabled = true;
        status.textContent = "Đang xuất log theo lựa chọn…";
        try {
            const response = await fetch(`/v1/admin/chat-logs.csv?${params}`);
            if (!response.ok) throw new Error(response.status === 401 ? "Phiên CMS đã hết. Hãy đăng nhập lại." : "Không xuất được CSV.");
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] || "logchat.csv";
            document.body.append(link); link.click(); link.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 10000);
            status.textContent = "Đã tải CSV.";
        } catch (error) {
            status.textContent = String(error);
        } finally {
            button.disabled = false;
        }
    });
    await loadLogChatGateways();
    await loadChatLogs();
}
async function loadChatLogs() {
    const grid = document.querySelector("#logchat-grid");
    if (!grid)
        return;
    const q = document.querySelector<HTMLInputElement>("#logchat-search")!.value.trim();
    const version = ++logchatRequestVersion;
    try {
        const data = await request<{
            total: number;
            offset: number;
            has_more: boolean;
            columns: string[];
            rows: LogRow[];
        }>(`/v1/admin/chat-logs?product=${encodeURIComponent(logchatProduct)}&q=${encodeURIComponent(q)}&gateway=${encodeURIComponent(logchatGateway)}&limit=${LOGCHAT_PAGE_SIZE}&offset=${logchatOffset}`);
        if (version !== logchatRequestVersion) return;
        logchatRows = data.rows;
        logchatColumns = data.columns;
        document.querySelector("#logchat-count")!.textContent = data.rows.length ? `${logchatOffset + 1}–${logchatOffset + data.rows.length}${data.has_more ? "+" : ""} lượt chat` : "0 lượt chat";
        document.querySelector("#logchat-page")!.textContent = `Trang ${Math.floor(logchatOffset / LOGCHAT_PAGE_SIZE) + 1}`;
        (document.querySelector("#logchat-newer") as HTMLButtonElement).disabled = logchatOffset === 0;
        (document.querySelector("#logchat-older") as HTMLButtonElement).disabled = !data.has_more;
    const rows = data.rows
      .map((row, i) => {
        const fallbackUsed = truthy(row.fallback_used);
        const model = usable(row.primary_model_name) || logModelName(row.primary_model, row.primary_model_config_id, row.product) || usable(row.actual_model_name) || logModelName(row.actual_model, row.actual_model_config_id, row.product) || "—";
        const fallback = fallbackUsed ? usable(row.actual_model_name) || logModelName(row.actual_model, row.actual_model_config_id, row.product) || logModelName(row.fallback_model, "", row.product) || "Có" : "—";
        const error = logText(row.error), reason = usable(row.fallback_reason);
        const gateway = usable(row.actual_api_base) || usable(row.primary_api_base);
        const inferredGateway = logText(row.gateway_snapshot_source) === "inferred";
        const gatewayLabel = gateway ? gateway.replace(/^https?:\/\//, "").slice(0, 38) + (inferredGateway ? " (\u01b0\u1edbc t\u00ednh)" : "") : "\u2014";
        const latency = Number(row.latency_ms) || 0;
        const firstChunk = logText(row.task) === "suggestion" ? row.client_suggestion_ms : row.client_first_chunk_ms;
        const firstChunkLabel = typeof firstChunk === "number" ? `${firstChunk.toLocaleString("vi-VN")} ms` : "—";
        const issue = error ? `<span class="chip bad" title="${esc(error)}">${esc(error.slice(0, 60))}</span>` : fallbackUsed && reason ? `<span class="chip warn" title="${esc(reason)}">${esc(reason.slice(0, 60))}</span>` : "";
        const question = logText(row.user_message);
        const user = logText(row.user) || logText(row.user_id);
        const roomLabel = logText(row.room), turnId = logText(row.user_message_id);
        const output = logText(row.model_response);
        const taskLabel = logText(row.task) === "suggestion" ? "Gợi ý" : "Trả lời";
        return `<tr class="clickRow" data-log-row="${i}"><td class="mono">${esc(shortTime(row.created_at))}</td><td><span class="chip">${esc(PRODUCT_LABELS[logText(row.product)] || logText(row.product) || "—")}</span></td><td class="logUser" title="${esc(logText(row.user_id))}">${user ? esc(user) : '<span class="faint">—</span>'}</td><td class="logSpeaker">${logSpeakerCell(row)}</td><td class="logTurn" title="${esc(turnId)}"><span>${esc(roomLabel)}</span><small>${esc(taskLabel)} · ${esc(turnId.slice(0,8))}</small></td><td class="logQuestion">${question ? esc(question.slice(0, 80)) + (question.length > 80 ? "…" : "") : '<span class="faint">—</span>'}</td><td class="logAnswer" title="${esc(output)}">${esc(output.slice(0,120))}${output.length>120?"…":""}</td><td title="${esc(logText(row.primary_model) || logText(row.actual_model))}">${esc(model)}</td><td title="${esc(logText(row.actual_model))}">${esc(fallback)}</td><td class="mono" title="${esc(gateway)}">${esc(gatewayLabel)}</td><td class="num">${esc(firstChunkLabel)}</td><td class="num">${latency ? `${latency.toLocaleString("vi-VN")} ms` : "—"}</td><td>${issue}</td></tr>`;
      })
      .join("");
    grid.innerHTML = data.rows.length
      ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Thời gian</th><th>Sản phẩm</th><th>Người dùng</th><th>Nhân vật</th><th>Phòng / lượt gửi</th><th>Câu hỏi</th><th>Câu trả lời / gợi ý</th><th>Model</th><th>Fallback</th><th>Gateway</th><th class="num" title="Từ bấm gửi đến chunk nội dung đầu tiên; với suggest: đến lúc nhận gợi ý tại trình duyệt">Latency</th><th class="num" title="Thời gian server xử lý đến khi nhận xong câu trả lời">Runtime</th><th>Lỗi</th></tr></thead><tbody>${rows}</tbody></table></div>`
      : '<p class="empty" style="margin:14px">Không có lượt chat nào khớp bộ lọc.</p>';
        grid.querySelectorAll<HTMLElement>("[data-log-row]").forEach((tr) => tr.addEventListener("click", () => {
            const row = logchatRows[Number(tr.dataset.logRow)];
            document.querySelector("#modal-log-detail header h2")!.textContent = `Lượt chat · ${shortTime(row.created_at)}`;
            document.querySelector("#log-detail-body")!.innerHTML = logDetailHtml(row, logchatColumns);
            openCmsModal("modal-log-detail");
        }));
    }
    catch (error) {
        grid.innerHTML = `<div class="err" style="margin:14px">${esc(error)}</div>`;
    }
}
const ACTION_GROUPS: [
    string,
    string
][] = [["all", "Tất cả"], ["auth", "Đăng nhập"], ["navigation", "Mở app"], ["assistant", "Trợ lý AI"], ["roleplay", "Chat Bot AI"], ["document", "Tài liệu"], ["api", "API khác"]];
const ACTION_STATUS: Record<string, [
    string,
    string
]> = { success: ["ok", "Thành công"], partial: ["warn", "Câu trả lời dở"], error: ["bad", "Lỗi"] };
function renderActionLogs() {
    const host = document.querySelector("#action-logs");
    if (!host)
        return;
    host.innerHTML = `<section class="panel"><header><div class="row"><label class="mdlFilter">Nhóm <select class="sm" id="action-category">${ACTION_GROUPS.map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></label><label class="mdlFilter">Trạng thái <select class="sm" id="action-status"><option value="all">Tất cả</option>${Object.entries(ACTION_STATUS).map(([k, [, v]]) => `<option value="${k}">${v}</option>`).join("")}</select></label><input class="input logSearch" id="action-search" placeholder="Tìm user, hành động, URL hoặc lỗi"></div><span class="chip tnum" id="action-count">…</span></header><div id="action-grid"><p class="empty" style="margin:14px">Đang tải…</p></div></section>${cmsModal("modal-action-detail", "Chi tiết sự kiện", "Nhật ký hoạt động", `<div id="action-detail-body"></div>`, `<button class="btn" data-close>Đóng</button>`)}`;
    host.querySelector("#action-category")?.addEventListener("change", () => void loadActionLogs());
    host.querySelector("#action-status")?.addEventListener("change", () => void loadActionLogs());
    let timer = 0;
    host.querySelector("#action-search")?.addEventListener("input", () => {
        window.clearTimeout(timer);
        timer = window.setTimeout(() => void loadActionLogs(), 300);
    });
    void loadActionLogs();
}
async function loadActionLogs() {
    const grid = document.querySelector("#action-grid");
    if (!grid)
        return;
    const category = document.querySelector<HTMLSelectElement>("#action-category")!.value;
    const statusFilter = document.querySelector<HTMLSelectElement>("#action-status")!.value;
    const q = document.querySelector<HTMLInputElement>("#action-search")!.value.trim();
    try {
        const data = await request<{
            total: number;
            columns: string[];
            rows: LogRow[];
        }>(`/v1/admin/action-logs?category=${encodeURIComponent(category)}&status_filter=${encodeURIComponent(statusFilter)}&q=${encodeURIComponent(q)}&limit=500`);
        actionRows = data.rows;
        actionColumns = data.columns;
        document.querySelector("#action-count")!.textContent = `${data.total} sự kiện`;
        const rows = data.rows
            .map((row, i) => {
            const [kind, label] = ACTION_STATUS[logText(row.status)] || ["", logText(row.status) || "—"];
            const code = logText(row.status_code), path = logText(row.path), error = logText(row.error);
            return `<tr class="clickRow" data-action-row="${i}"><td class="mono">${esc(shortTime(row.created_at, false))}</td><td>${row.username ? `@${esc(logText(row.username))}` : '<span class="faint">khách</span>'}</td><td>${esc(logText(row.action) || path)}${Number(code) >= 400 ? ` → ${esc(code)}` : ""}${error ? `<br><small class="faint">${esc(error.slice(0, 90))}</small>` : ""}</td><td class="mono">${esc(logText(row.category))}</td><td><span class="chip ${kind}">${esc(label)}</span></td></tr>`;
        })
            .join("");
        grid.innerHTML = data.rows.length
            ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Giờ</th><th>Tài khoản</th><th>Hành động</th><th>Nhóm</th><th>Trạng thái</th></tr></thead><tbody>${rows}</tbody></table></div>`
            : '<p class="empty" style="margin:14px">Không có sự kiện nào khớp bộ lọc.</p>';
        grid.querySelectorAll<HTMLElement>("[data-action-row]").forEach((tr) => tr.addEventListener("click", () => {
            const row = actionRows[Number(tr.dataset.actionRow)];
            document.querySelector("#modal-action-detail header h2")!.textContent = logText(row.action) || "Chi tiết sự kiện";
            document.querySelector("#action-detail-body")!.innerHTML = logDetailHtml(row, actionColumns);
            openCmsModal("modal-action-detail");
        }));
    }
    catch (error) {
        grid.innerHTML = `<div class="err" style="margin:14px">${esc(error)}</div>`;
    }
}
/* ---------- Database Explorer (theo admDB của prototype) ---------- */
let dbRows: Record<string, unknown>[] = [];
let dbColumns: string[] = [];
const dbCell = (value: unknown) => (value === null || value === undefined ? "" : typeof value === "object" ? JSON.stringify(value) : String(value));
const isRedacted = (value: string) => /^\[?(redacted|đã che)\]?$/i.test(value.trim()) || /^\*{3,}$/.test(value.trim());

const { renderVoiceLogs } = createCmsLogViews(request, esc, formatVietnamLogTime);
function renderDatabase() {
    const host = document.querySelector("#database")!;
    if (!dbTables.some((t) => t.name === activeDbTable) && dbTables.length)
        activeDbTable = dbTables[0].name;
    host.innerHTML = `<section class="panel"><header><div class="row"><label class="mdlFilter">Bảng <select class="sm" id="db-table">${dbTables.map((t) => `<option value="${esc(t.name)}" ${t.name === activeDbTable ? "selected" : ""}>${esc(t.name)} (${t.rows.toLocaleString("vi-VN")})</option>`).join("")}</select></label><input class="input logSearch" id="db-user-filter" placeholder="Lọc theo user ID, VD u_01"></div><div class="row"><span class="chip tnum" id="db-count">…</span><span class="chip">Chỉ đọc</span></div></header><div id="db-grid"><p class="empty" style="margin:14px">Đang tải…</p></div></section>${cmsModal("modal-db-row", "Bản ghi", "Database", `<div id="db-row-body"></div>`, `<button class="btn" data-close>Đóng</button>`)}`;
    host.querySelector("#db-table")?.addEventListener("change", (event) => {
        activeDbTable = (event.target as HTMLSelectElement).value;
        void loadDbRows();
    });
    let timer = 0;
    host.querySelector("#db-user-filter")?.addEventListener("input", () => {
        window.clearTimeout(timer);
        timer = window.setTimeout(() => void loadDbRows(), 300);
    });
    void loadDbRows();
}
async function loadDbRows() {
    const grid = document.querySelector("#db-grid");
    if (!grid || !activeDbTable)
        return;
    grid.innerHTML = '<div class="empty" role="status">Đang tải…</div>';
    mountLoadingCat(grid.firstElementChild!);
    const user = document
        .querySelector<HTMLInputElement>("#db-user-filter")
        ?.value.trim();
    try {
        const data = await request<DbRows>(`/v1/admin/database/${encodeURIComponent(activeDbTable)}?limit=100${user ? `&user_id=${encodeURIComponent(user)}` : ""}`);
        dbRows = data.rows;
        dbColumns = data.columns;
        document.querySelector("#db-count")!.textContent = data.total > data.rows.length ? `${data.rows.length} / ${data.total.toLocaleString("vi-VN")} dòng` : `${data.total.toLocaleString("vi-VN")} dòng`;
        const rows = data.rows
            .map((row, i) => `<tr class="clickRow" data-db-row="${i}">${data.columns.map((c) => {
            const v = dbCell(row[c]);
            return `<td class="${isRedacted(v) ? "redact" : "mono"}" title="${esc(v)}">${esc(v.length > 60 ? `${v.slice(0, 60)}…` : v)}</td>`;
        }).join("")}</tr>`)
            .join("");
        grid.innerHTML = data.rows.length
            ? `<div class="tbl-wrap"><table class="dt dbTable"><thead><tr>${data.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>`
            : '<p class="empty" style="margin:14px">Không có dòng nào khớp.</p>';
        grid.querySelectorAll<HTMLElement>("[data-db-row]").forEach((tr) => tr.addEventListener("click", () => {
            const row = dbRows[Number(tr.dataset.dbRow)];
            document.querySelector("#modal-db-row header h2")!.textContent = `${activeDbTable} · ${dbCell(row.id ?? row[dbColumns[0]])}`;
            document.querySelector("#db-row-body")!.innerHTML = `<div class="kvs logKvs">${dbColumns.map((c) => {
                const v = dbCell(row[c]);
                return `<div class="kv"><span class="mono">${esc(c)}</span><span class="${isRedacted(v) ? "redact" : "mono"}">${esc(v) || '<span class="faint">—</span>'}</span></div>`;
            }).join("")}</div>`;
            openCmsModal("modal-db-row");
        }));
    }
    catch (error) {
        grid.innerHTML = `<div class="err" style="margin:14px">${esc(error)}</div>`;
    }
}
function renderAccess() {
    const host = document.querySelector("#access")!;
    if (!accessControl) {
        host.innerHTML = '<div class="empty" role="status">Đang tải…</div>';
        mountLoadingCat(host.firstElementChild!);
        return;
    }
    host.innerHTML = `<div class="accessLayout"><section class="settingPanel"><h2>Chế độ truy cập</h2><p>Khi bảo trì được bật, chỉ tài khoản có quyền quản trị mới dùng được sản phẩm. CMS vẫn hoạt động.</p><div class="accessSwitches"><label><input id="maintenance-mode" type="checkbox" ${accessControl.maintenance_mode ? "checked" : ""}/><span><b>Chế độ bảo trì</b><small>Khóa tài khoản thường và người dùng demo</small></span></label><label><input id="registration-enabled" type="checkbox" ${accessControl.registration_enabled ? "checked" : ""}/><span><b>Cho phép đăng ký mới</b><small>Tắt riêng việc tạo tài khoản mới</small></span></label></div><div class="editorActions"><span class="statusText" id="access-status">${accessControl.maintenance_mode ? "Đang chỉ cho phép admin" : "Sản phẩm đang mở công khai"}</span><button class="btn pri" id="save-access">Lưu chế độ</button></div></section><section class="settingPanel"><h2>Tạo tài khoản quản trị</h2><p>Tài khoản này đăng nhập trên giao diện sản phẩm và vẫn hoạt động khi bảo trì.</p><div class="fields"><label class="field">Tên đăng nhập<input id="admin-account-username" autocomplete="off"/></label><label class="field">Tên hiển thị<input id="admin-account-name"/></label><label class="field full">Mật khẩu ban đầu<div class="passwordField"><input id="admin-account-password" type="password" autocomplete="new-password"/><button type="button" class="passwordToggle" id="toggle-admin-password" aria-pressed="false">Hiện</button></div></label></div><div class="editorActions"><span class="statusText" id="create-account-status">Chưa tạo</span><button class="btn pri" id="create-admin-account">Tạo tài khoản admin</button></div></section><section class="panel wide"><div class="panelHead"><div><h2>Quản lý tài khoản</h2><p>Khóa sẽ thu hồi mọi phiên đăng nhập hiện có ngay lập tức.</p></div></div><div class="accountCards">${accessControl.accounts.map((a) => `<article><div><strong>${esc(a.display_name)} <small>@${esc(a.username)}</small></strong><span>${a.is_admin ? '<b class="pill">Admin</b>' : ""}<i class="accountStatus ${esc(a.status)}">${a.status === "active" ? "Hoạt động" : a.status === "suspended" ? "Tạm khóa" : "Đã cấm"}</i></span><small>${esc(a.ban_reason || a.created_at)}</small></div><div class="accountActions"><button class="mini" data-admin-toggle="${esc(a.user_id)}">${a.is_admin ? "Bỏ quyền admin" : "Cấp quyền admin"}</button><button class="mini ${a.status === "active" ? "danger" : ""}" data-status-toggle="${esc(a.user_id)}">${a.status === "active" ? "Tạm khóa" : "Mở khóa"}</button></div></article>`).join("") || '<div class="empty">Chưa có tài khoản đăng ký.</div>'}</div></section></div>`;
    document.querySelector("#save-access")?.addEventListener("click", saveAccess);
    document
        .querySelector("#toggle-admin-password")
        ?.addEventListener("click", () => {
        const input = document.querySelector<HTMLInputElement>("#admin-account-password")!;
        const button = document.querySelector<HTMLButtonElement>("#toggle-admin-password")!;
        const visible = input.type === "text";
        input.type = visible ? "password" : "text";
        button.textContent = visible ? "Hiện" : "Ẩn";
        button.setAttribute("aria-pressed", String(!visible));
    });
    document
        .querySelector("#create-admin-account")
        ?.addEventListener("click", createAdminAccount);
    host.querySelectorAll<HTMLButtonElement>("[data-admin-toggle]").forEach((b) => b.addEventListener("click", () => updateAccessAccount(b.dataset.adminToggle!, {
        is_admin: !accessControl!.accounts.find((a) => a.user_id === b.dataset.adminToggle)!.is_admin,
    })));
    host
        .querySelectorAll<HTMLButtonElement>("[data-status-toggle]")
        .forEach((b) => b.addEventListener("click", () => {
        const a = accessControl!.accounts.find((x) => x.user_id === b.dataset.statusToggle)!;
        updateAccessAccount(a.user_id, {
            status: a.status === "active" ? "suspended" : "active",
            ban_reason: a.status === "active" ? "Tạm khóa từ CMS" : "",
            suspended_until: null,
        });
    }));
}
async function saveAccess() {
    const status = document.querySelector("#access-status")!;
    status.textContent = "Đang lưu…";
    mountLoadingCat(status, "inline");
    try {
        accessControl = await request<AccessControl>("/v1/admin/access-control", {
            method: "PUT",
            body: JSON.stringify({
                maintenance_mode: document.querySelector<HTMLInputElement>("#maintenance-mode")!
                    .checked,
                registration_enabled: document.querySelector<HTMLInputElement>("#registration-enabled")!.checked,
            }),
        });
        renderAccess();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
async function createAdminAccount() {
    const status = document.querySelector("#create-account-status")!;
    status.textContent = "Đang tạo…";
    mountLoadingCat(status, "inline");
    try {
        await request("/v1/admin/accounts", {
            method: "POST",
            body: JSON.stringify({
                username: document.querySelector<HTMLInputElement>("#admin-account-username")!.value,
                display_name: document.querySelector<HTMLInputElement>("#admin-account-name")!.value,
                password: document.querySelector<HTMLInputElement>("#admin-account-password")!.value,
                is_admin: true,
            }),
        });
        accessControl = await request<AccessControl>("/v1/admin/access-control");
        renderAccess();
    }
    catch (error) {
        status.textContent = String(error);
        status.className = "statusText error";
    }
}
async function updateAccessAccount(userId: string, changes: Record<string, unknown>) {
    await request(`/v1/admin/accounts/${encodeURIComponent(userId)}`, {
        method: "PATCH",
        body: JSON.stringify(changes),
    });
    accessControl = await request<AccessControl>("/v1/admin/access-control");
    renderAccess();
}
async function load() {
    try {
        [
            overview,
            settings,
            accessControl,
            characterCatalog,
            models,
            credentials,
        ] = await Promise.all([
            request<Overview>("/v1/admin/overview"),
            request<Settings>("/v1/admin/settings"),
            request<AccessControl>("/v1/admin/access-control"),
            request<CharacterCatalog>("/v1/admin/characters"),
            request<ModelConfig[]>("/v1/admin/models"),
            request<CredentialState>("/v1/admin/credentials"),
        ]);
        adminCharacters = [
            ...characterCatalog.preset_catalog,
            ...characterCatalog.user_characters,
        ];
        renderDashboard();
        renderAccess();
        renderModels();
        renderSettings();
        await loadDeferredView(document.querySelector<HTMLElement>(".view.active")?.id);
    }
    catch (error) {
        document.querySelector("#dashboard")!.innerHTML =
            `<div class="panel error">${esc(error)}</div>`;
    }
}
// Hidden panels must not fetch logs, table rows or character media on startup.
async function loadDeferredView(view?: string) {
    const host = view ? document.getElementById(view) : null;
    try {
        if (view === "content") renderContent();
        else if (view === "home-sections") await loadHomeSections();
        else if (view === "assistant-config") {
            await loadAssistantProfiles();
            renderAssistantSettings();
        } else if (view === "database") {
            dbTables = await request<DbTable[]>("/v1/admin/database");
            renderDatabase();
        } else if (view === "action-logs") renderActionLogs();
        else if (view === "voice-logs") renderVoiceLogs();
        else if (view === "conversations") await renderConversations();
    } catch (error) {
        if (host) host.innerHTML = `<div class="panel error">${esc(error)}</div>`;
    }
}
document.querySelectorAll<HTMLButtonElement>("[data-view]").forEach((button) => button.addEventListener("click", () => {
    document
        .querySelectorAll("[data-view]")
        .forEach((x) => x.classList.remove("active"));
    if (button.dataset.view !== "action-sounds") document.querySelectorAll<HTMLAudioElement>("#action-sounds audio").forEach(audio=>audio.pause());
    if (button.dataset.view !== "background-music") document.querySelectorAll<HTMLAudioElement>("#background-music audio").forEach(audio => audio.pause());
    button.classList.add("active");
    document
        .querySelectorAll(".view")
        .forEach((x) => x.classList.remove("active"));
    document.querySelector(`#${button.dataset.view}`)!.classList.add("active");
    const labels: Record<string, [
        string,
        string
    ]> = {
        access: [
            "Quản lý truy cập",
            "Chế độ bảo trì, tài khoản quản trị và trạng thái người dùng",
        ],
        dashboard: [
            "Tổng quan sản phẩm",
            "Sức khỏe hệ thống và nội dung sản phẩm",
        ],
        content: [
            "Nhân vật",
            "Danh sách nhân vật hệ thống và nhân vật do người dùng tạo",
        ],
        "action-sounds": ["Âm hành động", "Thư viện sound, từ khóa nhận diện và âm lượng"],
        "background-music": ["Nhạc nền Role Play", "Âm lượng, danh sách bài và nhạc phát tại trang chủ"],
        "home-sections": [
            "Danh mục trang chủ",
            "Các nhóm nhân vật hiển thị trên trang chủ Chat Bot AI",
        ],
        conversations: [
            "Logchat",
            "Log hỏi đáp theo sản phẩm · bấm một dòng để xem đầy đủ",
        ],
        "voice-logs": [
            "Log voice",
            "Theo dõi tạo audio, lượt Nghe và latency",
        ],
        "action-logs": [
            "Nhật ký hoạt động",
            "Không ghi mật khẩu, token hay nội dung request",
        ],
        models: [
            "Cấu hình AI",
            "Model và kết nối dùng chung cho Chat Bot AI và Trợ lý AI",
        ],
        "assistant-config": [
            "Trợ lý AI",
            "Chọn một trợ lý bên trái để chỉnh hiển thị, model, prompt và xem thống kê",
        ],
        database: [
            "Database Explorer",
            "Chỉ đọc · dữ liệu nhạy cảm được che",
        ],
        settings: [
            "Phân công model",
            "Gán model cho từng tác vụ của hệ thống",
        ],
    };
    void loadDeferredView(button.dataset.view);
    if (button.dataset.view === "action-sounds") void renderActionSounds();
    if (button.dataset.view === "background-music") void renderBackgroundMusic();
    const label = labels[button.dataset.view!];
    document.querySelector("#page-title")!.textContent = label[0];
    document.querySelector("#page-subtitle")!.textContent = label[1];
}));
const refreshButton = document.querySelector<HTMLButtonElement>("#refresh")!;
refreshButton.addEventListener("click", async () => {
    if (refreshButton.disabled) return;
    const originalLabel = refreshButton.innerHTML;
    const activeView = document.querySelector<HTMLElement>(".view.active")?.id;
    refreshButton.disabled = true;
    refreshButton.textContent = "Đang làm mới…";
    refreshButton.setAttribute("aria-busy", "true");
    try {
        if (activeView === "conversations") {
            logchatOffset = 0;
            await Promise.all([loadLogChatGateways(), loadChatLogs()]);
        } else if (activeView === "action-sounds") {
            await renderActionSounds();
        } else if (activeView === "background-music") {
            await renderBackgroundMusic();
        } else {
            await load();
        }
    } catch (error) {
        const host = document.querySelector("#logchat-grid");
        if (activeView === "conversations" && host)
            host.innerHTML = `<div class="err" style="margin:14px">${esc(error)}</div>`;
    } finally {
        refreshButton.disabled = false;
        refreshButton.innerHTML = originalLabel;
        refreshButton.removeAttribute("aria-busy");
    }
});
load();
