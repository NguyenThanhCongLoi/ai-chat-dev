import "./admin.css";

type Overview = {
  stats: Record<string, number>;
  characters: {
    id: string;
    name: string;
    role: string;
    type: string;
    category: string;
    updated_at: string;
  }[];
  rooms: {
    id: string;
    name: string;
    members: number;
    messages: number;
    updated_at: string;
  }[];
  documents: { id: string; filename: string; status: string; error?: string }[];
  ai_activity: {
    id: string;
    layers: number;
    memories: number;
    documents: number;
    created_at: string;
  }[];
};
type Settings = {
  assistant_system_instruction: string;
  llm_model: string;
  fallback_model: string;
  moderation_model: string;
  llm_api_base: string;
  response_instruction: string;
  suggestion_instruction: string;
  compiler_instruction: string;
  default_temperature: string;
  short_temperature: string;
  default_max_tokens: string;
  short_max_tokens: string;
  _base_prompts: { response: string; suggestion: string; compiler: string };
};
type CredentialState = {
  avibi: {
    configured: boolean;
    source: "cms" | "modal_secret" | "missing";
    hint: string;
  };
  bases?: { id: string; api_base: string; hint: string }[];
};
type AccessAccount = {
  user_id: string;
  username: string;
  display_name: string;
  status: "active" | "suspended" | "banned";
  is_admin: boolean;
  suspended_until: string | null;
  ban_reason: string;
  created_at: string;
  updated_at: string;
};
type AccessControl = {
  maintenance_mode: boolean;
  registration_enabled: boolean;
  accounts: AccessAccount[];
};
type DbRows = {
  table: string;
  total: number;
  limit: number;
  offset: number;
  columns: string[];
  rows: Record<string, unknown>[];
};
type AdminCharacter = {
  id: string;
  user_id: string | null;
  source: "preset" | "user";
  home_section?: "auto" | "featured" | "popular" | "top_rated" | "hidden";
  spec: {
    preset_type?: string;
    avatar_url?: string | null;
    creation_type: string;
    name: string;
    description: string;
    system_prompt: string;
    scenario: string;
    initial_greeting: string;
    tts_voice_id?: string;
    tts_gender?: "male" | "female" | "unspecified";
    tts_emotion_enabled?: boolean;
    identity: { role: string };
    goals: string[];
    behavior_rules: string[];
  };
};
type CharacterCatalog = {
  preset_catalog: AdminCharacter[];
  user_characters: AdminCharacter[];
};
type DbTable = { name: string; rows: number; columns: string[] };
type ModelConfig = {
  id: string;
  name: string;
  provider: string;
  model_id: string;
  api_base: string;
  logo: string;
  enabled: boolean;
  assistant_name: string;
  assistant_model_id: string;
  assistant_enabled: boolean;
  assistant_thinking_mode: string;
  assistant_reasoning_effort: string;
  role: "available" | "primary" | "fallback";
  has_api_key: boolean;
  api_key_hint: string;
  purposes: string[];
  response_instruction: string;
  suggestion_instruction: string;
  compiler_instruction: string;
  moderation_instruction: string;
  emotion_instruction: string;
  assistant_general_instruction: string;
  assistant_psychology_instruction: string;
  assistant_health_instruction: string;
  assistant_homework_instruction: string;
  assistant_tarot_instruction: string;
  assistant_general_fallback_instruction: string;
  assistant_psychology_fallback_instruction: string;
  assistant_health_fallback_instruction: string;
  assistant_homework_fallback_instruction: string;
  assistant_tarot_fallback_instruction: string;
  temperature: string;
  short_temperature: string;
  max_tokens: string;
  short_max_tokens: string;
  gateway_read_timeout_seconds: string;
  tts_default_voice: string;
  thinking_mode: string;
  reasoning_effort: string;
};
type ExpressionPreview = {
  character_id: string;
  status: "queued" | "processing" | "ready" | "failed" | "no-image-model" | "missing";
  quality: string;
  error?: string;
  images: Record<string, string>;
};
type ModelUpdate = ModelConfig & {
  expression_generation?: {
    characters: number;
    unique_sources: number;
    images: number;
  };
};
const root = document.querySelector<HTMLDivElement>("#admin-root")!;
root.innerHTML = `<div class="adminShell"><aside class="adminSide"><div class="adminBrand"><b>AI</b><span>Role Play CMS<small>Product administration</small></span></div><nav class="adminNav"><button class="active" data-view="dashboard">▦ &nbsp;Tổng quan</button><button data-view="access">♙ &nbsp;Truy cập</button><button data-view="content">☺ &nbsp;Nhân vật</button><button data-view="conversations">▤ &nbsp;Logchat</button><button data-view="action-logs">&#9673; &nbsp;Nh&#7853;t k&#253; ho&#7841;t &#273;&#7897;ng</button><button data-view="models">◈ &nbsp;C&#7845;u h&#236;nh AI</button><button data-view="assistant-config">✦ &nbsp;AI Assistant</button><button data-view="database">▤ &nbsp;Database</button><button data-view="settings">⚙ &nbsp;Ph&#226;n c&#244;ng model</button></nav><div class="adminMeta">Khu vực quản trị riêng<br/>Được bảo vệ bằng tài khoản admin</div></aside><main class="adminMain"><div class="top"><div><h1 id="page-title">Tổng quan sản phẩm</h1><p id="page-subtitle">Dữ liệu vận hành trực tiếp từ hệ thống</p></div><div class="topActions"><a class="btn secondary" href="/role-play-ai" style="text-decoration:none">Mở AI Role Play</a><button class="btn secondary" id="refresh">↻ Làm mới</button></div></div><section class="view active" id="dashboard"></section><section class="view" id="access"></section><section class="view" id="content"></section><section class="view" id="conversations"></section><section class="view" id="action-logs"></section><section class="view" id="models"></section><section class="view" id="assistant-config"></section><section class="view" id="database"></section><section class="view" id="settings"></section></main></div>`;
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
const esc = (value: unknown) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ]!,
  );
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok)
    throw new Error(
      response.status === 401
        ? "Bạn chưa đăng nhập CMS hoặc phiên đăng nhập đã hết."
        : await response.text(),
    );
  return response.json();
}
function showGenerationNotice(
  plan: NonNullable<ModelUpdate["expression_generation"]>,
) {
  const message = plan.images
    ? `Đã lưu model ảnh. Hệ thống sẽ tạo ${plan.images} ảnh cho ${plan.unique_sources} nguồn avatar duy nhất, tương ứng ${plan.characters} nhân vật. Nhân vật không có avatar và bộ đã đủ 6 ảnh không được tính.`
    : `Đã lưu model ảnh. Không có nhân vật có avatar nào thiếu bộ 6 ảnh, vì vậy model ảnh sẽ không được gọi.`;
  let notice = document.querySelector<HTMLDivElement>(
    "#expression-generation-notice",
  );
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
function renderDashboard() {
  if (!overview) return;
  const s = overview.stats;
  document.querySelector("#dashboard")!.innerHTML = `<div class="metrics">${[
    ["Người dùng", s.users],
    ["Nhân vật", s.characters],
    ["Phòng chat", s.rooms],
    ["Tin nhắn", s.messages],
    ["Ký ức", s.memories],
  ]
    .map(
      ([a, b]) =>
        `<article class="metric"><span>${a}</span><strong>${b}</strong><small>Dữ liệu toàn hệ thống</small></article>`,
    )
    .join(
      "",
    )}</div><div class="layout"><section class="panel wide"><div class="panelHead"><div><h2>Danh mục nhân vật</h2><p>Nhân vật đang được người dùng sử dụng</p></div></div><div class="table"><div class="row head"><span>Tên</span><span>Vai trò</span><span>Nhóm</span><span>Trạng thái</span></div>${
    overview.characters
      .slice(0, 10)
      .map(
        (x) =>
          `<div class="row"><strong>${esc(x.name)}</strong><span>${esc(x.role)}</span><span>${x.category === "entertainment" ? "Giải trí" : "Hữu ích"}</span><span class="pill">Hoạt động</span></div>`,
      )
      .join("") || '<div class="empty">Chưa có dữ liệu.</div>'
  }</div></section><section class="panel"><div class="panelHead"><div><h2>Tài liệu</h2><p>${s.ready_documents || 0} sẵn sàng · ${s.failed_documents || 0} lỗi</p></div></div><div class="list">${
    overview.documents
      .slice(0, 7)
      .map(
        (x) =>
          `<div class="listItem"><i class="dot ${esc(x.status)}"></i><span><strong>${esc(x.filename)}</strong><small>${esc(x.status)}</small></span></div>`,
      )
      .join("") || '<div class="empty">Chưa có tài liệu.</div>'
  }</div></section><section class="panel"><div class="panelHead"><div><h2>AI pipeline</h2><p>Các lượt tạo phản hồi gần đây</p></div></div><div class="list">${
    overview.ai_activity
      .slice(0, 7)
      .map(
        (x) =>
          `<div class="listItem"><i class="dot ready"></i><span><strong>${x.layers} lớp context</strong><small>${x.memories} memory · ${x.documents} tài liệu</small></span></div>`,
      )
      .join("") || '<div class="empty">Chưa có hoạt động.</div>'
  }</div></section></div>`;
}
async function loadVbeeVoices() {
  const status = document.querySelector<HTMLElement>("#tts-voice-status");
  const list = document.querySelector<HTMLDataListElement>("#tts-voice-options");
  if (!status || !list) return;
  try {
    const result = await request<{ voices: { id: string; name: string; gender: string; language: string }[] }>("/v1/admin/tts/voices");
    if (!list.isConnected) return;
    list.innerHTML = result.voices.map((voice) => `<option value="${esc(voice.id)}" label="${esc(voice.name)} · ${voice.gender === "male" ? "Nam" : voice.gender === "female" ? "Nữ" : "Khác"} · ${esc(voice.language)}"></option>`).join("");
    status.textContent = `Đã tải ${result.voices.length} giọng Vbee. Để trống mã giọng để hệ thống tự chọn theo giới tính.`;
  } catch {
    if (status.isConnected) status.textContent = "Danh sách giọng Vbee sẽ hiện sau khi cấu hình model và API key TTS trong CMS.";
  }
}

function renderContent() {
  if (!overview) return;
  document.querySelector("#content")!.innerHTML =
    `<div class="layout"><section class="panel wide"><div class="panelHead"><div><h2>Tạo nhân vật hệ thống</h2><p>Nhân vật do admin tạo có thể được xếp vào các khu vực trang chủ.</p></div></div><div class="fields"><label class="field">Tên nhân vật<input id="new-character-name" placeholder="Ví dụ: Linh"/></label><label class="field">Vai trò<input id="new-character-role" value="companion" placeholder="companion, study, work..."/></label><label class="field">Nhóm<select id="new-character-category"><option value="utility">Hữu ích</option><option value="entertainment">Giải trí</option></select></label><label class="field">Ảnh nhân vật<input type="file" id="new-character-avatar" accept="image/png,image/jpeg,image/webp,image/gif"/><span class="hint">JPG, PNG, WEBP hoặc GIF · tối đa 5 MB</span></label><label class="field full">Mô tả<textarea id="new-character-description"></textarea></label><label class="field full">System prompt<textarea class="largePrompt" id="new-character-prompt"></textarea></label><label class="field full">Lời chào đầu tiên<textarea id="new-character-greeting"></textarea></label></div><div class="editorActions"><span class="toast" id="new-character-status">Chưa tạo</span><button class="btn" id="create-system-character">Tạo nhân vật</button></div></section><section class="panel wide"><div class="panelHead"><div><h2>Tạo danh mục trang chủ</h2><p>Nhân vật public và nhân vật hệ thống sẽ tự vào mục khi vai trò hoặc tag phù hợp.</p></div></div><div class="fields"><label class="field">Tên danh mục<input id="new-section-name" placeholder="Ví dụ: Học tập"/></label><label class="field">Tag / vai trò khớp<input id="new-section-tags" placeholder="study, academy, tutor"/></label></div><div class="editorActions"><span class="toast" id="new-section-status">Chưa tạo</span><button class="btn" id="create-home-section">Tạo danh mục</button></div></section><section class="panel wide"><div class="panelHead"><div><h2>Chỉnh sửa từng nhân vật</h2><p>Thay system prompt và nội dung nhân vật mà không sửa core</p></div></div><div class="fields"><label class="field full">Chọn nhân vật<select id="character-select">${adminCharacters
      .filter((x) => x.source === "preset")
      .map(
        (x) =>
          `<option value="${esc(x.id)}">${esc(x.spec.name)} · Preset</option>`,
      )
      .join("")}${adminCharacters
      .filter((x) => x.source === "user")
      .map(
        (x) =>
          `<option value="${esc(x.id)}">${esc(x.spec.name)} · User ${esc(x.user_id)}</option>`,
      )
      .join(
        "",
      )}</select></label><label class="field full" id="home-section-field">Vị trí trên trang chủ<select id="character-home-section"><option value="auto">Hiện trong Nhân vật hệ thống</option><option value="hidden">Ẩn khỏi trang chủ</option></select><span class="hint">Chỉ áp dụng cho nhân vật hệ thống do admin quản lý.</span></label><label class="field">Tên<input id="character-name"/></label><label class="field">Vai trò<input id="character-role"/></label><label class="field full">Mô tả<textarea id="character-description"></textarea></label><label class="field full">System prompt riêng<textarea class="largePrompt" id="character-system-prompt"></textarea></label><label class="field full">Scenario<textarea id="character-scenario"></textarea></label><label class="field full">Lời chào đầu tiên<textarea id="character-greeting"></textarea></label><label class="field full">Thay Ảnh nhân vật<input type="file" id="character-avatar-file" accept="image/png,image/jpeg,image/webp,image/gif"/><span class="hint">Để trống nếu muốn giữ ảnh hiện tại.</span></label><label class="field">Goals, mỗi dòng một mục<textarea id="character-goals"></textarea></label><label class="field">Behavior rules, mỗi dòng một mục<textarea id="character-rules"></textarea></label></div><div class="editorActions"><span class="toast" id="character-status">Chọn nhân vật để chỉnh sửa</span><button class="btn" id="save-character">Lưu nhân vật</button></div></section><section class="panel wide"><div class="panelHead"><div><h2>Cuộc trò chuyện</h2><p>Thống kê nội dung theo phòng</p></div></div><div class="table"><div class="row head"><span>Tên phòng</span><span>Số thành viên</span><span>Tin nhắn</span><span>Trạng thái</span></div>${overview.rooms.map((x) => `<div class="row"><strong>${esc(x.name)}</strong><span>${x.members} nhân vật</span><span>${x.messages}</span><span class="pill">Hoạt động</span></div>`).join("") || '<div class="empty">Chưa có phòng chat.</div>'}</div></section><section class="panel wide"><div class="panelHead"><div><h2>Tài liệu người dùng</h2><p>Kiểm tra trạng thái ingestion và moderation</p></div></div><div class="table"><div class="row head"><span>Tên file</span><span>ID</span><span>Trạng thái</span><span>Kết quả</span></div>${overview.documents.map((x) => `<div class="row"><strong>${esc(x.filename)}</strong><span>${esc(x.id.slice(0, 12))}…</span><span>${esc(x.status)}</span><span class="pill">${x.status === "failed" ? "Cần xem" : "Bình thường"}</span></div>`).join("") || '<div class="empty">Chưa có tài liệu.</div>'}</div></section></div>`;
  document.querySelector("#save-character")?.insertAdjacentHTML("beforebegin", '<button class="btn secondary" id="backfill-system-expressions" type="button">Tạo ảnh biểu cảm còn thiếu</button>');
  document.querySelector("#character-greeting")?.closest("label")?.insertAdjacentHTML("afterend", '<label class="field">Giới tính giọng<select id="character-tts-gender"><option value="unspecified">Tự nhận diện</option><option value="male">Nam</option><option value="female">Nữ</option></select><small>Dùng để tự chọn voice Vbee. Chọn rõ nếu nhân vật public chưa nhận diện đúng.</small></label><label class="field">Giọng TTS<input id="character-tts-voice" list="tts-voice-options" maxlength="160" placeholder="Tự chọn theo giới tính"/><small>Để trống để tự chọn voice Vbee; nhập mã để dùng giọng riêng.</small></label>');
  document.querySelector("#new-character-greeting")?.closest("label")?.insertAdjacentHTML("afterend", '<label class="field">Giới tính giọng<select id="new-character-tts-gender"><option value="unspecified">Tự nhận diện</option><option value="male">Nam</option><option value="female">Nữ</option></select></label><label class="field">Giọng TTS<input id="new-character-tts-voice" list="tts-voice-options" maxlength="160" placeholder="Tự chọn theo giới tính"/></label>');
  document.querySelector("#content")?.insertAdjacentHTML("beforeend", '<datalist id="tts-voice-options"></datalist><p id="tts-voice-status" class="hint"></p>');
  void loadVbeeVoices();
  document.querySelector<HTMLButtonElement>("#backfill-system-expressions")?.addEventListener("click", async (event) => {
    const button = event.currentTarget as HTMLButtonElement;
    button.disabled = true;
    try {
      const result = await request<{ characters_queued: number; images_queued: number }>("/v1/admin/system-characters/expressions/backfill", { method: "POST" });
      button.textContent = result.characters_queued ? `Đã xếp hàng ${result.characters_queued} nhân vật · ${result.images_queued} ảnh` : "Tất cả nhân vật có ảnh đã đủ biểu cảm";
      const selected = currentCharacter();
      if (selected) void loadExpressionPreview(selected);
    } catch (error) {
      button.textContent = error instanceof Error ? error.message : "Không thể tạo ảnh biểu cảm";
    } finally {
      button.disabled = false;
    }
  });
  bindCharacterEditor();
  bindAdminCreate();
  bindHomeSectionCreate();
}
function currentCharacter() {
  const id =
    document.querySelector<HTMLSelectElement>("#character-select")?.value;
  return adminCharacters.find((item) => item.id === id);
}
function fillCharacter() {
  const item = currentCharacter();
  if (!item) return;
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
    const input = document.querySelector<
      HTMLInputElement | HTMLTextAreaElement
    >(`#${id}`);
    if (input) input.value = value;
  });
  const placement = document.querySelector<HTMLSelectElement>(
    "#character-home-section",
  );
  const placementField = document.querySelector<HTMLElement>(
    "#home-section-field",
  );
  if (placement) placement.value = item.home_section || "hidden";
  if (placementField)
    placementField.style.display = item.source === "preset" ? "grid" : "none";
  const status = document.querySelector("#character-status");
  if (status) status.textContent = `Đang sửa ${item.spec.name}`;
}
async function loadExpressionPreview(item: AdminCharacter, attempt = 0) {
  let host = document.querySelector<HTMLElement>(
    "#character-expression-preview",
  );
  if (!host) {
    const field = document
      .querySelector("#character-avatar-file")
      ?.closest("label");
    field?.insertAdjacentHTML(
      "afterend",
      '<div id="character-expression-preview" class="expressionPreview"><span>Đang kiểm tra bộ ảnh biểu cảm…</span></div>',
    );
    host = document.querySelector<HTMLElement>("#character-expression-preview");
  }
  if (!host) return;
  host.innerHTML = "<span>Đang kiểm tra bộ ảnh biểu cảm…</span>";
  try {
    const data = await request<ExpressionPreview>(
      `/v1/admin/characters/${encodeURIComponent(item.id)}/expressions`,
    );
    const labels: Record<string, string> = {
      neutral: "Bình thường",
      happy: "Vui",
      sad: "Buồn",
      angry: "Giận",
      surprised: "Bất ngờ",
      shy: "Ngại",
    };
    const meaning: Record<string, string> = {
      queued: "Đang chờ tạo ảnh",
      processing: "Đang tạo ảnh",
      failed: "Tạo ảnh thất bại; kiểm tra model ảnh hoặc gateway",
      "no-image-model": "Chưa phân công model cho tác vụ tạo ảnh nhân vật",
      fallback: "Đã dùng bộ ảnh xử lý từ avatar vì model ảnh không trả kết quả",
      missing: "Chưa tải ảnh nguồn hoặc chưa có bộ biểu cảm",
    };
    host.innerHTML = `<div class="expressionPreviewHead"><b>Bộ ảnh biểu cảm</b><span>${esc(meaning[data.quality] || data.quality)}${data.error ? `: ${esc(data.error)}` : ""} · ${Object.keys(data.images).length}/6 ảnh</span></div><div class="expressionPreviewGrid">${
      Object.entries(data.images)
        .map(
          ([emotion, url]) =>
            `<figure><img src="${esc(url)}?v=${Date.now()}" alt="${esc(labels[emotion] || emotion)}"/><figcaption>${esc(labels[emotion] || emotion)}</figcaption></figure>`,
        )
        .join("") || "<p>Chưa có ảnh được tạo.</p>"
    }</div>`;
    if ((data.status === "queued" || data.status === "processing") && attempt < 60)
      window.setTimeout(() => { if (currentCharacter()?.id === item.id) void loadExpressionPreview(item, attempt + 1); }, 3000);
  } catch (error) {
    host.innerHTML = `<span>Chưa có bộ ảnh: ${esc(error)}</span>`;
  }
}
function bindCharacterEditor() {
  const select = document.querySelector<HTMLSelectElement>("#character-select");
  if (!select) return;
  select.addEventListener("change", () => {
    fillCharacter();
    const item = currentCharacter();
    if (item) loadExpressionPreview(item);
  });
  document
    .querySelector("#save-character")
    ?.addEventListener("click", saveCharacter);
  fillCharacter();
  const item = currentCharacter();
  if (item) loadExpressionPreview(item);
}
async function saveCharacter() {
  const item = currentCharacter();
  const status = document.querySelector("#character-status");
  if (!item || !status) return;
  status.textContent = "Đang lưu…";
  status.className = "toast";
  const value = (id: string) =>
    document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`)!
      .value;
  try {
    const endpoint =
      item.source === "preset"
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
      const placement = document.querySelector<HTMLSelectElement>(
        "#character-home-section",
      )!.value;
      await request(`/v1/admin/presets/${item.spec.preset_type}/home-section`, {
        method: "PUT",
        body: JSON.stringify({ home_section: placement }),
      });
      updated.home_section = placement as AdminCharacter["home_section"];
    }
    const avatar = document.querySelector<HTMLInputElement>(
      "#character-avatar-file",
    )?.files?.[0];
    if (avatar) {
      const avatarPath =
        item.source === "preset"
          ? `/v1/admin/presets/${item.spec.preset_type}/avatar`
          : `/v1/admin/characters/${item.id}/avatar`;
      const uploaded = await uploadAdminAvatar(avatarPath, avatar);
      updated.spec.avatar_url = uploaded.avatar_url;
    }
    adminCharacters = adminCharacters.map((x) =>
      x.id === updated.id ? { ...x, ...updated } : x,
    );
    status.textContent = "Đã lưu và áp dụng cho cuộc trò chuyện mới";
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
function bindHomeSectionCreate() {
  document
    .querySelector("#create-home-section")
    ?.addEventListener("click", createHomeSection);
}
async function createHomeSection() {
  const name = document
    .querySelector<HTMLInputElement>("#new-section-name")!
    .value.trim();
  const tags = document
    .querySelector<HTMLInputElement>("#new-section-tags")!
    .value.split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const status = document.querySelector("#new-section-status")!;
  if (!name || !tags.length) {
    status.textContent = "Hãy nhập tên và tag";
    status.className = "toast error";
    return;
  }
  try {
    await request("/v1/admin/home-sections", {
      method: "POST",
      body: JSON.stringify({ name, tags }),
    });
    status.textContent = "Đã tạo danh mục và áp dụng lên trang chủ";
    document.querySelector<HTMLInputElement>("#new-section-name")!.value = "";
    document.querySelector<HTMLInputElement>("#new-section-tags")!.value = "";
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
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
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<{ avatar_url: string; expression_status?: string; images_queued?: number }>;
}
async function createAdminCharacter() {
  const status = document.querySelector("#new-character-status")!;
  const value = (id: string) =>
    document
      .querySelector<
        HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
      >(`#${id}`)!
      .value.trim();
  if (!value("new-character-name")) {
    status.textContent = "Hãy nhập tên nhân vật";
    status.className = "toast error";
    return;
  }
  status.textContent = "Đang tạo…";
  status.className = "toast";
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
        tts_voice_id: value("new-character-tts-voice").trim(),
        tts_gender: value("new-character-tts-gender"),
      }),
    });
    const avatar = document.querySelector<HTMLInputElement>(
      "#new-character-avatar",
    )?.files?.[0];
    let imagesQueued = 0;
    if (avatar) {
      const uploaded = await uploadAdminAvatar(
        `/v1/admin/presets/${created.spec.preset_type}/avatar`,
        avatar,
      );
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
    if (select) { select.value = created.id; fillCharacter(); void loadExpressionPreview(created); }
    const createdStatus = document.querySelector("#new-character-status");
    if (createdStatus) createdStatus.textContent = imagesQueued ? `Đã tạo nhân vật · đang tạo ${imagesQueued} ảnh biểu cảm` : "Đã tạo nhân vật · tải ảnh nguồn để tạo biểu cảm";
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
function modelOptions(selected = "", includeEmpty = false) {
  const options = models
    .map(
      (x) =>
        `<option value="${esc(x.id)}" ${x.id === selected ? "selected" : ""}>${esc(x.name)} &middot; ${esc(x.model_id)}${x.enabled ? "" : " (\u0111ang \u1ea9n)"}</option>`,
    )
    .join("");
  return `${includeEmpty ? '<option value="">Ch\u01b0a ph\u00e2n c\u00f4ng</option>' : ""}${options}`;
}
function assistantModelOptions(selected = "", includeEmpty = false) {
  const options = models
    .filter((x) => x.assistant_enabled)
    .map(
      (x) =>
        `<option value="${esc(x.id)}" ${x.id === selected ? "selected" : ""}>${esc(x.assistant_name)} &middot; ${esc(x.assistant_model_id)}</option>`,
    )
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
function selectedModel() {
  const id = document.querySelector<HTMLSelectElement>(
    "#model-config-select",
  )?.value;
  return models.find((x) => x.id === id);
}
function renderModels() {
  const selected = models[0];
  document.querySelector("#models")!.innerHTML =
    `<section class="settingPanel credentialPanel"><h2>Kh&#243;a API d&#249;ng chung</h2><p>D&#249;ng cho c&#225;c model kh&#244;ng c&#243; API key ri&#234;ng.</p><div class="fields"><label class="field full">API key m&#7899;i<input type="password" id="shared-avibi-key" autocomplete="new-password"/></label></div><div class="editorActions"><span class="toast" id="credential-status">${credentials?.avibi.configured ? `&#272;&#227; c&#7845;u h&#236;nh &middot; ${esc(credentials.avibi.hint)}` : "Ch&#432;a c&#7845;u h&#236;nh"}</span><div><button class="btn secondary" id="reset-credential">D&#249;ng Modal Secret</button> <button class="btn" id="save-credential">L&#432;u key</button></div></div></section><div class="modelLayout"><section class="settingPanel"><h2>Th&#234;m model</h2><div class="fields"><label class="field">T&#234;n hi&#7875;n th&#7883;<input id="model-name"/></label><label class="field">Provider<input id="model-provider" value="AVIBI"/></label><label class="field">Model ID<input id="model-id" placeholder="openai/gpt-4.1-mini"/></label><label class="field">Logo ch&#7919;<input id="model-logo" maxlength="4" value="AI"/></label><label class="field full">API base<input id="model-base" value="https://gateway.avibi.ai/v1"/></label><label class="field full">API key ri&#234;ng<input type="password" id="model-key"/></label></div><div class="editorActions"><span class="toast" id="model-status">Ch&#432;a l&#432;u</span><button class="btn" id="add-model">Th&#234;m model</button></div></section><section class="modelRegistry"><div class="registryHead"><h2>Danh s&#225;ch model</h2><p>Ch&#7885;n model &#273;&#7875; m&#7903; c&#7845;u h&#236;nh ri&#234;ng.</p></div><div class="modelCards">${models.map((model) => `<article class="modelCard"><div class="modelLogo">${esc(model.logo || "AI")}</div><div class="modelInfo"><div><strong>${esc(model.name)}</strong>${model.purposes.map((x) => `<span class="pill">${esc(x)}</span>`).join("")}</div><p>${esc(model.provider)} &middot; ${esc(model.model_id)}</p><small>${model.enabled ? "&#272;ang b&#7853;t" : "&#272;&#227; &#7849;n"} &middot; ${model.has_api_key ? `Key ${esc(model.api_key_hint)}` : "Key d&#249;ng chung"}</small></div><div class="modelActions"><button class="mini" data-edit="${model.id}">C&#7845;u h&#236;nh</button><button class="mini" data-toggle="${model.id}">${model.enabled ? "&#7848;n" : "B&#7853;t"}</button><button class="mini danger" data-delete="${model.id}">X&#243;a</button></div></article>`).join("") || '<div class="empty">Ch&#432;a c&#243; model.</div>'}</div></section></div><section class="settingPanel modelEditor"><h2>C&#7845;u h&#236;nh theo model</h2><p>M&#7895;i model c&#243; system prompt v&#224; tham s&#7889; sinh ri&#234;ng.</p><label class="field full">Model<select id="model-config-select">${modelOptions(selected?.id)}</select></label><div class="modelPurposeSummary" id="model-purpose-summary"></div><div class="fields"><label class="field">T&#234;n<input id="edit-model-name"/></label><label class="field">Provider<input id="edit-model-provider"/></label><label class="field full">Model ID<input id="edit-model-id"/></label><label class="field full">API base<input id="edit-model-base"/></label><label class="field" data-config-purpose="response">Temperature m&#7863;c &#273;&#7883;nh<input id="edit-model-temperature" type="number" min="0" max="2" step="0.05"/></label><label class="field" data-config-purpose="response">Temperature c&#226;u ng&#7855;n<input id="edit-model-short-temperature" type="number" min="0" max="2" step="0.05"/></label><label class="field" data-config-purpose="response">Max tokens m&#7863;c &#273;&#7883;nh<input id="edit-model-max-tokens" type="number" min="50" max="8000"/></label><label class="field" data-config-purpose="response">Max tokens c&#226;u ng&#7855;n<input id="edit-model-short-max-tokens" type="number" min="50" max="8000"/></label><label class="field">Thinking mode<select id="edit-model-thinking"><option value="default">Theo mặc định gateway</option><option value="enabled">Bật</option><option value="disabled">Tắt</option></select></label><label class="field">Reasoning effort<select id="edit-model-effort"><option value="default">Theo mặc định gateway</option><option value="low">Low</option><option value="high">High</option><option value="max">Max</option></select></label><label class="field full">API key m&#7899;i<input id="edit-model-key" type="password" placeholder="&#272;&#7875; tr&#7889;ng &#273;&#7875; gi&#7919; key hi&#7879;n t&#7841;i"/></label><label class="field full" data-config-purpose="response">System prompt tr&#7843; l&#7901;i<textarea class="largePrompt" id="edit-response-prompt"></textarea></label><label class="field full" data-config-purpose="suggestion">System prompt g&#7907;i &#253; tr&#7843; l&#7901;i<textarea class="largePrompt" id="edit-suggestion-prompt"></textarea></label><label class="field full" data-config-purpose="compiler">System prompt t&#7841;o nh&#226;n v&#7853;t<textarea class="largePrompt" id="edit-compiler-prompt"></textarea></label><label class="field full" data-config-purpose="moderation">System prompt ki&#7875;m duy&#7879;t<textarea class="largePrompt" id="edit-moderation-prompt"></textarea></label><label class="field full" data-config-purpose="emotion">System prompt nh&#7853;n di&#7879;n c&#7843;m x&#250;c<textarea class="largePrompt" id="edit-emotion-prompt"></textarea></label></div><div class="editorActions"><span class="toast" id="model-edit-status">Ch&#7885;n m&#7897;t model</span><button class="btn" id="save-model-profile">L&#432;u c&#7845;u h&#236;nh model</button></div></section>`;
  document.querySelector("#edit-model-short-max-tokens")?.closest("label")?.insertAdjacentHTML(
    "afterend",
    '<label class="field">Chờ gateway tối đa (giây)<input id="edit-model-gateway-timeout" type="number" min="4" max="45" step="1"/><small>Mặc định 12 giây; chỉ tăng cho model cần thêm thời gian.</small></label>',
  );
  document.querySelector("#edit-model-base")?.closest("label")?.insertAdjacentHTML("afterend", '<label class="field full" data-config-purpose="tts">Mã giọng TTS mặc định<input id="edit-model-tts-voice" maxlength="160" placeholder="Voice ID từ gateway"/><small>Áp dụng cho nhân vật chưa có mã giọng riêng. API base cần kết thúc bằng /v1.</small></label>');
  const sharedHelp = document.querySelector<HTMLElement>("#models .credentialPanel p");
  if (sharedHelp) sharedHelp.textContent = "Key gateway AVIBI cũ, chỉ dùng cho https://gateway.avibi.ai/v1. API base khác cần key riêng hoặc key theo API base.";
  document.querySelectorAll<HTMLElement>("#models .modelRegistry .modelCard small").forEach((label, index) => {
    const model = models[index];
    if (!model || model.has_api_key) return;
    const base = model.api_base.replace(/\/+$/, "").toLowerCase();
    const entry = credentials?.bases?.find((item) => item.api_base === base);
    const source = entry ? `Key API base ${entry.hint}` : base === "https://gateway.avibi.ai/v1" && credentials?.avibi.configured ? "Key gateway chung" : "Chưa cấu hình key cho API base";
    label.textContent = `${model.enabled ? "Đang bật" : "Đã ẩn"} · ${source}`;
  });
  document.querySelector("#models .credentialPanel")?.insertAdjacentHTML("afterend", `<section class="settingPanel credentialPanel"><h2>API key theo API base</h2><p>Mỗi API base có key riêng. Model có key riêng sẽ dùng key của chính model; nếu không, dùng key của API base tương ứng.</p><div class="fields"><label class="field">API base<input id="credential-base-url" placeholder="https://openrouter.ai/api/v1"/></label><label class="field">API key<input id="credential-base-key" type="password" autocomplete="new-password"/></label></div><div class="editorActions"><span class="toast" id="credential-base-status">Chưa lưu</span><button class="btn" id="save-base-credential">Lưu key cho API base</button></div><div class="modelCards">${(credentials?.bases || []).map((item) => `<article class="modelCard"><div class="modelInfo"><strong>${esc(item.api_base)}</strong><small>Key ${esc(item.hint)}</small></div><button class="mini danger" data-delete-base-key="${esc(item.id)}">Xóa key</button></article>`).join("")}</div></section>`);
  document.querySelector("#save-base-credential")?.addEventListener("click", saveBaseCredential);
  document.querySelectorAll<HTMLButtonElement>("[data-delete-base-key]").forEach((button) => button.addEventListener("click", () => void deleteBaseCredential(button.dataset.deleteBaseKey || "")));
  document
    .querySelector("#save-credential")
    ?.addEventListener("click", saveCredential);
  document
    .querySelector("#reset-credential")
    ?.addEventListener("click", resetCredential);
  document.querySelector("#add-model")?.addEventListener("click", addModel);
  document
    .querySelector("#model-config-select")
    ?.addEventListener("change", fillModelEditor);
  document
    .querySelector("#save-model-profile")
    ?.addEventListener("click", saveModelProfile);
  document.querySelectorAll<HTMLButtonElement>("[data-edit]").forEach((x) =>
    x.addEventListener("click", () => {
      const select = document.querySelector<HTMLSelectElement>(
        "#model-config-select",
      )!;
      select.value = x.dataset.edit!;
      fillModelEditor();
      document
        .querySelector(".modelEditor")
        ?.scrollIntoView({ behavior: "smooth" });
    }),
  );
  document.querySelectorAll<HTMLButtonElement>("[data-toggle]").forEach((x) =>
    x.addEventListener("click", () => {
      const model = models.find((m) => m.id === x.dataset.toggle);
      if (model) patchModel(model.id, { enabled: !model.enabled });
    }),
  );
  document
    .querySelectorAll<HTMLButtonElement>("[data-delete]")
    .forEach((x) =>
      x.addEventListener("click", () => deleteModel(x.dataset.delete!)),
    );
  fillModelEditor();
}
function fillModelEditor() {
  const model = selectedModel();
  if (!model) return;
  const values: Record<string, string> = {
    "edit-model-name": model.name,
    "edit-model-provider": model.provider,
    "edit-model-id": model.model_id,
    "edit-model-base": model.api_base,
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
    const node = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(
      `#${id}`,
    );
    if (node) node.value = value || "";
  });
  document
    .querySelectorAll<HTMLElement>("[data-config-purpose]")
    .forEach((node) => {
      node.hidden = !(
        model.purposes.includes(node.dataset.configPurpose!) ||
        model.purposes.includes(node.dataset.configPurpose! + "_fallback") ||
        (node.dataset.configPurpose === "emotion" &&
          model.purposes.includes("emotion_fallback")) ||
        (node.dataset.configPurpose === "response" &&
          model.purposes.includes("fallback")) ||
        (node.dataset.configPurpose === "suggestion" &&
          model.purposes.includes("suggestion_fallback"))
      );
    });
  const summary = document.querySelector("#model-purpose-summary");
  if (summary)
    summary.innerHTML = model.purposes.length
      ? model.purposes
          .map(
            (p) =>
              `<span class="pill">${esc(modelPurposeLabels[p] || p)}</span>`,
          )
          .join("")
      : `<span class="unassignedPurpose">Ch&#432;a ph&#226;n c&#244;ng t&#225;c v&#7909; cho model n&#224;y.</span>`;
  const status = document.querySelector("#model-edit-status");
  if (status) status.textContent = `\u0110ang s\u1eeda ${model.name}`;
}
async function saveModelProfile() {
  const model = selectedModel();
  const status = document.querySelector("#model-edit-status")!;
  if (!model) return;
  const value = (id: string) =>
    document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`)!
      .value;
  status.textContent = "\u0110ang l\u01b0u\u2026";
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
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
async function saveCredential() {
  const input = document.querySelector<HTMLInputElement>("#shared-avibi-key")!;
  const status = document.querySelector("#credential-status")!;
  try {
    const result = await request<CredentialState["avibi"]>(
      "/v1/admin/credentials/avibi",
      { method: "PUT", body: JSON.stringify({ api_key: input.value }) },
    );
    credentials = { ...credentials, avibi: result };
    input.value = "";
    renderModels();
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
async function resetCredential() {
  try {
    const result = await request<CredentialState["avibi"]>(
      "/v1/admin/credentials/avibi",
      { method: "DELETE" },
    );
    credentials = { ...credentials, avibi: result };
    renderModels();
  } catch (error) {
    alert(String(error));
  }
}
async function saveBaseCredential() {
  const status = document.querySelector<HTMLElement>("#credential-base-status")!;
  const api_base = document.querySelector<HTMLInputElement>("#credential-base-url")!.value.trim();
  const api_key = document.querySelector<HTMLInputElement>("#credential-base-key")!.value.trim();
  try {
    await request("/v1/admin/credentials/bases", { method: "PUT", body: JSON.stringify({ api_base, api_key }) });
    credentials = await request<CredentialState>("/v1/admin/credentials");
    renderModels();
  } catch (error) { status.textContent = String(error); status.className = "toast error"; }
}
async function deleteBaseCredential(id: string) {
  try {
    await request(`/v1/admin/credentials/bases/${encodeURIComponent(id)}`, { method: "DELETE" });
    credentials = await request<CredentialState>("/v1/admin/credentials");
    renderModels();
  } catch (error) { alert(String(error)); }
}
async function reloadModels() {
  models = await request<ModelConfig[]>("/v1/admin/models");
  renderModels();
  renderSettings();
}
async function addModel() {
  const status = document.querySelector("#model-status")!;
  const value = (id: string) =>
    document.querySelector<HTMLInputElement>(`#${id}`)!.value;
  status.textContent = "Đang mã hóa và lưu…";
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
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
async function patchModel(id: string, body: Record<string, unknown>) {
  try {
    await request(`/v1/admin/models/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
    await reloadModels();
  } catch (error) {
    alert(String(error));
    await reloadModels();
  }
}
async function deleteModel(id: string) {
  if (!confirm("Xóa cấu hình model này?")) return;
  try {
    await request(`/v1/admin/models/${id}?force=true`, { method: "DELETE" });
    await reloadModels();
  } catch (error) {
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
let activeAssistantPurpose = "assistant_general";
function assistantCatalogOptions(selected = "") {
  return models
    .map(
      (x) =>
        `<option value="${esc(x.id)}" ${x.id === selected ? "selected" : ""}>${esc(x.assistant_name)} · ${esc(x.assistant_model_id)}</option>`,
    )
    .join("");
}
function fillAssistantModelEditor() {
  const id = document.querySelector<HTMLSelectElement>(
    "#assistant-model-editor",
  )?.value;
  const model = models.find((x) => x.id === id);
  if (!model) return;
  document.querySelector<HTMLInputElement>("#assistant-model-name")!.value =
    model.assistant_name;
  document.querySelector<HTMLInputElement>("#assistant-model-core")!.value =
    model.assistant_model_id;
  document.querySelector<HTMLInputElement>(
    "#assistant-model-enabled",
  )!.checked = model.assistant_enabled;
  document.querySelector<HTMLSelectElement>(
    "#assistant-model-thinking",
  )!.value = model.assistant_thinking_mode;
  document.querySelector<HTMLSelectElement>("#assistant-model-effort")!.value =
    model.assistant_reasoning_effort;
}
async function saveAssistantModelEditor() {
  const id = document.querySelector<HTMLSelectElement>(
    "#assistant-model-editor",
  )?.value;
  const status = document.querySelector("#assistant-model-editor-status")!;
  if (!id) return;
  status.textContent = "Đang lưu…";
  try {
    await request(`/v1/admin/assistant-models/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        name: document.querySelector<HTMLInputElement>("#assistant-model-name")!
          .value,
        model_id: document.querySelector<HTMLInputElement>(
          "#assistant-model-core",
        )!.value,
        enabled: document.querySelector<HTMLInputElement>(
          "#assistant-model-enabled",
        )!.checked,
        thinking_mode: document.querySelector<HTMLSelectElement>(
          "#assistant-model-thinking",
        )!.value,
        reasoning_effort: document.querySelector<HTMLSelectElement>(
          "#assistant-model-effort",
        )!.value,
      }),
    });
    models = await request<ModelConfig[]>("/v1/admin/models");
    renderAssistantSettings();
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
function renderAssistantSettings() {
  const host = document.querySelector("#assistant-config")!;
  const purpose = activeAssistantPurpose;
  const fallbackPurpose = purpose + "_fallback";
  const fallbackPurpose2 = purpose + "_fallback_2";
  const assigned = models.find((x) => x.purposes.includes(purpose));
  const fallback = models.find((x) => x.purposes.includes(fallbackPurpose));
  const fallback2 = models.find((x) => x.purposes.includes(fallbackPurpose2));
  const promptField = (purpose + "_instruction") as keyof ModelConfig;
  const fallbackPromptField = (purpose +
    "_fallback_instruction") as keyof ModelConfig;
  const fallbackPromptField2 = (purpose +
    "_fallback_2_instruction") as keyof ModelConfig;
  host.innerHTML = `<div class="settings"><section class="settingPanel"><h2>Model riêng của AI Assistant</h2><p>Dùng chung kết nối model đã thêm, nhưng tên hiển thị, Core Model ID và trạng thái bật/tắt chỉ áp dụng cho AI Assistant.</p><div class="fields"><label class="field full">Model nguồn<select id="assistant-model-editor">${assistantCatalogOptions(models[0]?.id)}</select></label><label class="field">Tên hiển thị trên Assistant<input id="assistant-model-name"/></label><label class="field">Core Model ID trên Assistant<input id="assistant-model-core"/></label><label class="field"><span>Cho phép chọn trên client</span><input id="assistant-model-enabled" type="checkbox"/></label><label class="field">Thinking mode<select id="assistant-model-thinking"><option value="default">Theo mặc định gateway</option><option value="enabled">Bật</option><option value="disabled">Tắt</option></select></label><label class="field">Reasoning effort<select id="assistant-model-effort"><option value="default">Theo mặc định gateway</option><option value="low">Low</option><option value="high">High</option><option value="max">Max</option></select></label></div><div class="editorActions"><span class="toast" id="assistant-model-editor-status">Cấu hình này không thay đổi AI Role Play</span><button class="btn" id="save-assistant-model-editor">Lưu model Assistant</button></div></section><div class="assistantConfigTabs">${assistantPurposes.map((p) => `<button class="${p === purpose ? "active" : ""}" data-assistant-tab="${p}">${esc(modelPurposeLabels[p])}</button>`).join("")}</div><section class="settingPanel"><h2>${esc(modelPurposeLabels[purpose])}</h2><p>Mỗi tác vụ có model chính, model dự phòng và prompt riêng. Prompt Admin được ưu tiên; nếu để trống hệ thống dùng prompt base trong code.</p><div class="fields"><label class="field">Model chính<select id="assistant-active-model">${assistantModelOptions(assigned?.id, true)}</select></label><label class="field">Fallback 1<select id="assistant-fallback-model">${assistantModelOptions(fallback?.id, true)}</select></label><label class="field">Fallback 2<select id="assistant-fallback-model-2">${assistantModelOptions(fallback2?.id, true)}</select></label><label class="field full">System prompt của model chính<textarea class="largePrompt" id="assistant-active-prompt">${esc(assigned ? String(assigned[promptField] || "") : "")}</textarea></label><label class="field full">Prompt fallback 1<textarea class="largePrompt" id="assistant-fallback-prompt">${esc(fallback ? String(fallback[fallbackPromptField] || "") : "")}</textarea></label><label class="field full">Prompt fallback 2<textarea class="largePrompt" id="assistant-fallback-prompt-2">${esc(fallback2 ? String(fallback2[fallbackPromptField2] || "") : "")}</textarea></label></div></section><div class="saveBar"><span class="toast" id="assistant-assignment-status">Chính: ${assigned ? esc(assigned.assistant_name) : "Chưa phân công"} · Dự phòng: ${fallback ? esc(fallback.assistant_name) : "Chưa phân công"}</span><button class="btn" id="save-assistant-assignment">Lưu ${esc(modelPurposeLabels[purpose])}</button></div></div>`;
  host.insertAdjacentHTML("afterbegin", `<section class="settingPanel"><h2>System prompt chung cho AI Assistant</h2><p>Áp dụng cho mọi chức năng và model chính/dự phòng; prompt theo tác vụ trong code và ghi đè riêng từng model vẫn được giữ.</p><label class="field full">Quy tắc chung<textarea class="largePrompt" id="assistant-global-prompt">${esc(settings?.assistant_system_instruction || "")}</textarea></label><div class="editorActions"><span class="toast" id="assistant-global-prompt-status">Lưu riêng, không ảnh hưởng AI Role Play.</span><button class="btn" id="save-assistant-global-prompt">Lưu prompt chung</button></div></section>`);
  const purposeReadiness = assistantPurposes.map((item) => {
    const names = [item, item + "_fallback", item + "_fallback_2"].map((role) => models.find((model) => model.purposes.includes(role))?.assistant_name || "Chưa phân công");
    const complete = names.every((name) => name !== "Chưa phân công");
    return `<div><b>${esc(modelPurposeLabels[item])}</b><span>Chính: ${esc(names[0])} · Fallback 1: ${esc(names[1])} · Fallback 2: ${esc(names[2])}</span><strong>${complete ? "Đủ 3 model" : "Thiếu phân công"}</strong></div>`;
  }).join("");
  host.insertAdjacentHTML("afterbegin", `<section class="settingPanel"><h2>Kiểm tra model dự phòng theo tác vụ</h2><p>Mỗi tác vụ cần một model chính và hai model dự phòng riêng biệt.</p><div class="assignmentSummary">${purposeReadiness}</div></section>`);
  document.querySelector<HTMLButtonElement>("#save-assistant-global-prompt")?.addEventListener("click", saveAssistantGlobalPrompt);
  document
    .querySelectorAll<HTMLButtonElement>("[data-assistant-tab]")
    .forEach((button) =>
      button.addEventListener("click", () => {
        activeAssistantPurpose = button.dataset.assistantTab!;
        renderAssistantSettings();
      }),
    );
  const syncPrompt = (selectId: string, promptId: string) =>
    document.querySelector(selectId)?.addEventListener("change", (event) => {
      const model = models.find(
        (item) => item.id === (event.target as HTMLSelectElement).value,
      );
      const textarea = document.querySelector<HTMLTextAreaElement>(promptId);
      if (textarea)
        textarea.value = model ? String(model[promptField] || "") : "";
    });
  syncPrompt("#assistant-active-model", "#assistant-active-prompt");
  document
    .querySelector("#assistant-fallback-model")
    ?.addEventListener("change", (event) => {
      const model = models.find(
        (item) => item.id === (event.target as HTMLSelectElement).value,
      );
      const textarea = document.querySelector<HTMLTextAreaElement>(
        "#assistant-fallback-prompt",
      );
      if (textarea)
        textarea.value = model ? String(model[fallbackPromptField] || "") : "";
    });
  document
    .querySelector("#assistant-fallback-model-2")
    ?.addEventListener("change", (event) => {
      const model = models.find(
        (item) => item.id === (event.target as HTMLSelectElement).value,
      );
      const textarea = document.querySelector<HTMLTextAreaElement>(
        "#assistant-fallback-prompt-2",
      );
      if (textarea)
        textarea.value = model ? String(model[fallbackPromptField2] || "") : "";
    });
  document
    .querySelector("#save-assistant-assignment")
    ?.addEventListener("click", saveAssistantAssignment);
  document
    .querySelector("#assistant-model-editor")
    ?.addEventListener("change", fillAssistantModelEditor);
  document
    .querySelector("#save-assistant-model-editor")
    ?.addEventListener("click", saveAssistantModelEditor);
  fillAssistantModelEditor();
}
async function saveAssistantAssignment() {
  const status = document.querySelector("#assistant-assignment-status")!;
  const selected = document.querySelector<HTMLSelectElement>(
    "#assistant-active-model",
  )!.value;
  const fallback = document.querySelector<HTMLSelectElement>(
    "#assistant-fallback-model",
  )!.value;
  const fallback2 = document.querySelector<HTMLSelectElement>(
    "#assistant-fallback-model-2",
  )!.value;
  const prompt = document.querySelector<HTMLTextAreaElement>(
    "#assistant-active-prompt",
  )!.value;
  const fallbackPrompt = document.querySelector<HTMLTextAreaElement>(
    "#assistant-fallback-prompt",
  )!.value;
  const fallbackPrompt2 = document.querySelector<HTMLTextAreaElement>(
    "#assistant-fallback-prompt-2",
  )!.value;
  const fallbackPurpose = activeAssistantPurpose + "_fallback";
  const fallbackPurpose2 = activeAssistantPurpose + "_fallback_2";
  status.textContent = "Đang lưu…";
  try {
    await request(`/v1/admin/assistant-purposes/${encodeURIComponent(activeAssistantPurpose)}`, {
      method: "PUT",
      body: JSON.stringify({
        primary_model_id: selected || null,
        fallback_model_id: fallback || null,
        fallback_2_model_id: fallback2 || null,
        primary_prompt: prompt,
        fallback_prompt: fallbackPrompt,
        fallback_2_prompt: fallbackPrompt2,
      }),
    });
    models = await request<ModelConfig[]>("/v1/admin/models");
    renderModels();
    renderSettings();
    renderAssistantSettings();
    return;
    for (const model of models) {
      const purposes = model.purposes.filter(
        (p) =>
          p !== activeAssistantPurpose &&
          p !== fallbackPurpose &&
          p !== fallbackPurpose2,
      );
      if (model.id === selected) purposes.push(activeAssistantPurpose);
      if (model.id === fallback) purposes.push(fallbackPurpose);
      if (model.id === fallback2) purposes.push(fallbackPurpose2);
      const body: Record<string, unknown> = { purposes };
      if (model.id === selected)
        body[activeAssistantPurpose + "_instruction"] = prompt;
      if (model.id === fallback)
        body[activeAssistantPurpose + "_fallback_instruction"] = fallbackPrompt;
      if (model.id === fallback2)
        body[activeAssistantPurpose + "_fallback_2_instruction"] =
          fallbackPrompt2;
      await request(`/v1/admin/models/${model.id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
    }
    models = await request<ModelConfig[]>("/v1/admin/models");
    renderModels();
    renderSettings();
    renderAssistantSettings();
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
async function saveAssistantGlobalPrompt() {
  const status=document.querySelector<HTMLElement>("#assistant-global-prompt-status");
  const prompt=document.querySelector<HTMLTextAreaElement>("#assistant-global-prompt")?.value||"";
  if(status){status.textContent="Đang lưu…";status.className="toast";}
  try {
    settings=await request<Settings>("/v1/admin/settings",{method:"PUT",body:JSON.stringify({assistant_system_instruction:prompt})});
    if(status)status.textContent="Đã lưu prompt chung cho AI Assistant.";
  } catch(error) {
    if(status){status.textContent=String(error);status.className="toast error";}
  }
}
function renderSettingsBase() {
  document.querySelector("#settings")!.innerHTML =
    `<div class="settings"><section class="settingPanel"><h2>Ph&#226;n c&#244;ng model theo t&#225;c v&#7909;</h2><p>Ch&#7885;n model th&#7921;c hi&#7879;n t&#7915;ng c&#244;ng vi&#7879;c. Prompt v&#224; tham s&#7889; &#273;&#432;&#7907;c ch&#7881;nh trong C&#7845;u h&#236;nh AI c&#7911;a t&#7915;ng model.</p><div class="assignmentManage"><select id="assignment-edit-model">${modelOptions(models[0]?.id)}</select><button class="btn secondary" id="assignment-edit-button">S&#7917;a model &#273;&#227; l&#432;u</button></div><div class="fields"><label class="field">Tr&#7843; l&#7901;i h&#7897;i tho&#7841;i<select id="purpose-response">${modelOptions(assignmentValue("response"), true)}</select><small>Model ch&#237;nh tr&#7843; l&#7901;i ng&#432;&#7901;i d&#249;ng.</small></label><label class="field">G&#7907;i &#253; tr&#7843; l&#7901;i<select id="purpose-suggestion">${modelOptions(assignmentValue("suggestion"), true)}</select><small>T&#7841;o c&#225;c l&#7921;a ch&#7885;n tr&#7843; l&#7901;i nhanh.</small></label><label class="field">D&#7921; ph&#242;ng g&#7907;i &#253;<select id="purpose-suggestion_fallback">${modelOptions(assignmentValue("suggestion_fallback"), true)}</select><small>D&#249;ng khi model t&#7841;o g&#7907;i &#253; ch&#237;nh b&#7883; l&#7895;i.</small></label><label class="field">T&#7841;o nh&#226;n v&#7853;t<select id="purpose-compiler">${modelOptions(assignmentValue("compiler"), true)}</select><small>T&#243;m t&#7855;t m&#244; t&#7843; v&#224; bi&#234;n d&#7883;ch CharacterSpec.</small></label><label class="field">Ki&#7875;m duy&#7879;t<select id="purpose-moderation">${modelOptions(assignmentValue("moderation"), true)}</select><small>Ph&#226;n t&#237;ch an to&#224;n n&#7897;i dung v&#224; ng&#7919; c&#7843;nh.</small></label><label class="field">D&#7921; ph&#242;ng<select id="purpose-fallback">${modelOptions(assignmentValue("fallback"), true)}</select><small>D&#249;ng khi model ch&#237;nh kh&#244;ng kh&#7843; d&#7909;ng.</small></label><label class="field">T&#7841;o avatar bi&#7875;u c&#7843;m<select id="purpose-avatar_image">${modelOptions(assignmentValue("avatar_image"), true)}</select><small>Ch&#7881;nh &#7843;nh ngu&#7891;n th&#224;nh ch&#226;n dung ch&#237;nh di&#7879;n v&#224; sinh b&#7897; n&#233;t m&#7863;t.</small></label><label class="field">Nh&#7853;n di&#7879;n c&#7843;m x&#250;c<select id="purpose-emotion">${modelOptions(assignmentValue("emotion"), true)}</select><small>Model nh&#7865; ph&#226;n lo&#7841;i c&#7843;m x&#250;c c&#7911;a c&#226;u tr&#7843; l&#7901;i.</small></label><label class="field">D&#7921; ph&#242;ng c&#7843;m x&#250;c<select id="purpose-emotion_fallback">${modelOptions(assignmentValue("emotion_fallback"), true)}</select><small>T&#7921; chuy&#7875;n sang model n&#224;y khi model c&#7843;m x&#250;c ch&#237;nh l&#7895;i.</small></label></div></section><section class="settingPanel"><h2>Tr&#7841;ng th&#225;i ph&#226;n c&#244;ng</h2><div class="assignmentSummary">${[
      "response",
      "suggestion",
      "suggestion_fallback",
      "suggestion_fallback_2",
      "compiler",
      "moderation",
      "fallback",
      "fallback_2",
      "avatar_image",
      "emotion",
      "emotion_fallback",
      "emotion_fallback_2",
      "tts",
    ]
      .map((p) => {
        const m = models.find((x) => x.purposes.includes(p));
        return `<div><span>${p}</span><strong>${m ? esc(m.name) : "Ch&#432;a ph&#226;n c&#244;ng"}</strong></div>`;
      })
      .join(
        "",
      )}</div></section><div class="saveBar"><span class="toast" id="assignment-status">Ch&#432;a c&#243; thay &#273;&#7893;i</span><button class="btn" id="save-assignments">L&#432;u v&#224; &#225;p d&#7909;ng</button></div></div>`;
  document
    .querySelector("#save-assignments")
    ?.addEventListener("click", saveModelAssignments);
  document
    .querySelector("#assignment-edit-button")
    ?.addEventListener("click", openAssignedModelEditor);
}
function renderSettings() {
  renderSettingsBase();
  const additions: [string, string, string, string][] = [
    [
      "#purpose-suggestion_fallback",
      "suggestion_fallback_2",
      "Dự phòng gợi ý 2",
      "Dùng khi model gợi ý chính và fallback 1 đều lỗi.",
    ],
    [
      "#purpose-fallback",
      "fallback_2",
      "Dự phòng hội thoại 2",
      "Model thứ ba trả lời khi model chính và fallback 1 đều lỗi.",
    ],
    [
      "#purpose-emotion_fallback",
      "emotion_fallback_2",
      "Dự phòng cảm xúc 2",
      "Model thứ ba nhận diện cảm xúc khi hai model trước đều lỗi.",
    ],
    [
      "#purpose-emotion_fallback",
      "tts",
      "Phát giọng nói Role Play",
      "Gọi /audio/speech từ API base đã cấu hình khi người dùng bấm Nghe.",
    ],
  ];
  for (const [anchor, purpose, label, help] of additions) {
    const field = document.querySelector(anchor)?.closest("label");
    if (field && !document.querySelector(`#purpose-${purpose}`))
      field.insertAdjacentHTML(
        "afterend",
        `<label class="field">${label}<select id="purpose-${purpose}">${modelOptions(assignmentValue(purpose), true)}</select><small>${help}</small></label>`,
      );
  }
}
function openAssignedModelEditor() {
  const id = document.querySelector<HTMLSelectElement>(
    "#assignment-edit-model",
  )?.value;
  if (!id) return;
  const nav = document.querySelector<HTMLButtonElement>('[data-view="models"]');
  nav?.click();
  const select = document.querySelector<HTMLSelectElement>(
    "#model-config-select",
  );
  if (select) {
    select.value = id;
    fillModelEditor();
    document
      .querySelector(".modelEditor")
      ?.scrollIntoView({ behavior: "smooth" });
  }
}
async function saveModelAssignments() {
  const status = document.querySelector("#assignment-status")!;
  status.textContent = "\u0110ang l\u01b0u\u2026";
  status.className = "toast";
  const purposes = [
    "response",
    "suggestion",
    "suggestion_fallback",
    "suggestion_fallback_2",
    "compiler",
    "moderation",
    "fallback",
    "fallback_2",
    "avatar_image",
    "emotion",
    "emotion_fallback",
    "emotion_fallback_2",
    "tts",
  ];
  const selected = Object.fromEntries(
    purposes.map((p) => [
      p,
      document.querySelector<HTMLSelectElement>(`#purpose-${p}`)!.value,
    ]),
  );
  try {
    let generation: ModelUpdate["expression_generation"];
    for (const model of models) {
      const preserved = model.purposes.filter((p) => !purposes.includes(p));
      const assigned = [
        ...preserved,
        ...purposes.filter((p) => selected[p] === model.id),
      ];
      const updated = await request<ModelUpdate>(
        `/v1/admin/models/${model.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            purposes: assigned,
            enabled: assigned.length ? true : model.enabled,
          }),
        },
      );
      if (updated.expression_generation)
        generation = updated.expression_generation;
    }
    if (generation) {
      showGenerationNotice(generation);
    }
    models = await request<ModelConfig[]>("/v1/admin/models");
    renderModels();
    renderSettings();
    renderAssistantSettings();
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
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
  grid.innerHTML = '<div class="empty">Đang tải…</div>';
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
    grid.innerHTML = `<div class="dbMeta">${data.total} lượt chat · cuộn ngang và dọc để xem toàn bộ</div><div class="dbTable logchatTable"><table><thead><tr>${data.columns.map((column) => `<th>${esc(column)}</th>`).join("")}</tr></thead><tbody>${data.rows.map((row) => `<tr>${data.columns.map((column) => `<td class="logchat-${esc(column)}" title="${esc(row[column])}">${esc(row[column])}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${data.columns.length}">Chưa có logchat.</td></tr>`}</tbody></table></div>`;
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
  grid.innerHTML = '<div class="empty">Đang tải…</div>';
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
function renderDatabase() {
  const host = document.querySelector("#database")!;
  host.innerHTML = `<section class="panel wide"><div class="panelHead"><div><h2>Database Explorer</h2><p>Chỉ đọc; secrets mã hóa không được đưa vào đây.</p></div><div class="dbFilters"><input id="db-user-filter" placeholder="Lọc user ID (nếu bảng hỗ trợ)"/><button class="btn secondary" id="db-refresh">Làm mới</button></div></div><div class="dbTabs">${dbTables.map((t) => `<button class="mini ${t.name === activeDbTable ? "active" : ""}" data-table="${esc(t.name)}">${esc(t.name)} <b>${t.rows}</b></button>`).join("")}</div><div id="db-grid" class="dbGrid"><div class="empty">Đang tải…</div></div></section>`;
  host.querySelectorAll<HTMLButtonElement>("[data-table]").forEach((b) =>
    b.addEventListener("click", () => {
      activeDbTable = b.dataset.table!;
      renderDatabase();
    }),
  );
  document
    .querySelector("#db-refresh")
    ?.addEventListener("click", () => loadDbRows());
  loadDbRows();
}
async function loadDbRows() {
  const grid = document.querySelector("#db-grid");
  if (!grid) return;
  grid.innerHTML = '<div class="empty">Đang tải…</div>';
  const user = document
    .querySelector<HTMLInputElement>("#db-user-filter")
    ?.value.trim();
  try {
    const data = await request<DbRows>(
      `/v1/admin/database/${encodeURIComponent(activeDbTable)}?limit=100${user ? `&user_id=${encodeURIComponent(user)}` : ""}`,
    );
    grid.innerHTML = `<div class="dbMeta">${data.total} bản ghi · đang hiển thị ${data.rows.length}</div><div class="dbTable"><table><thead><tr>${data.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${data.rows.map((row) => `<tr>${data.columns.map((c) => `<td title="${esc(typeof row[c] === "object" ? JSON.stringify(row[c]) : row[c])}">${esc(typeof row[c] === "object" ? JSON.stringify(row[c]) : row[c])}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${data.columns.length}">Chưa có dữ liệu.</td></tr>`}</tbody></table></div>`;
  } catch (error) {
    grid.innerHTML = `<div class="error">${esc(error)}</div>`;
  }
}
function renderAccess() {
  const host = document.querySelector("#access")!;
  if (!accessControl) {
    host.innerHTML = '<div class="empty">Đang tải…</div>';
    return;
  }
  host.innerHTML = `<div class="accessLayout"><section class="settingPanel"><h2>Chế độ truy cập</h2><p>Khi bảo trì được bật, chỉ tài khoản có quyền quản trị mới dùng được sản phẩm. CMS vẫn hoạt động.</p><div class="accessSwitches"><label><input id="maintenance-mode" type="checkbox" ${accessControl.maintenance_mode ? "checked" : ""}/><span><b>Chế độ bảo trì</b><small>Khóa tài khoản thường và người dùng demo</small></span></label><label><input id="registration-enabled" type="checkbox" ${accessControl.registration_enabled ? "checked" : ""}/><span><b>Cho phép đăng ký mới</b><small>Tắt riêng việc tạo tài khoản mới</small></span></label></div><div class="editorActions"><span class="toast" id="access-status">${accessControl.maintenance_mode ? "Đang chỉ cho phép admin" : "Sản phẩm đang mở công khai"}</span><button class="btn" id="save-access">Lưu chế độ</button></div></section><section class="settingPanel"><h2>Tạo tài khoản quản trị</h2><p>Tài khoản này đăng nhập trên giao diện sản phẩm và vẫn hoạt động khi bảo trì.</p><div class="fields"><label class="field">Tên đăng nhập<input id="admin-account-username" autocomplete="off"/></label><label class="field">Tên hiển thị<input id="admin-account-name"/></label><label class="field full">Mật khẩu ban đầu<div class="passwordField"><input id="admin-account-password" type="password" autocomplete="new-password"/><button type="button" class="passwordToggle" id="toggle-admin-password" aria-pressed="false">Hiện</button></div></label></div><div class="editorActions"><span class="toast" id="create-account-status">Chưa tạo</span><button class="btn" id="create-admin-account">Tạo tài khoản admin</button></div></section><section class="panel wide"><div class="panelHead"><div><h2>Quản lý tài khoản</h2><p>Khóa sẽ thu hồi mọi phiên đăng nhập hiện có ngay lập tức.</p></div></div><div class="accountCards">${accessControl.accounts.map((a) => `<article><div><strong>${esc(a.display_name)} <small>@${esc(a.username)}</small></strong><span>${a.is_admin ? '<b class="pill">Admin</b>' : ""}<i class="accountStatus ${esc(a.status)}">${a.status === "active" ? "Hoạt động" : a.status === "suspended" ? "Tạm khóa" : "Đã cấm"}</i></span><small>${esc(a.ban_reason || a.created_at)}</small></div><div class="accountActions"><button class="mini" data-admin-toggle="${esc(a.user_id)}">${a.is_admin ? "Bỏ quyền admin" : "Cấp quyền admin"}</button><button class="mini ${a.status === "active" ? "danger" : ""}" data-status-toggle="${esc(a.user_id)}">${a.status === "active" ? "Tạm khóa" : "Mở khóa"}</button></div></article>`).join("") || '<div class="empty">Chưa có tài khoản đăng ký.</div>'}</div></section></div>`;
  document.querySelector("#save-access")?.addEventListener("click", saveAccess);
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
    ?.addEventListener("click", createAdminAccount);
  host.querySelectorAll<HTMLButtonElement>("[data-admin-toggle]").forEach((b) =>
    b.addEventListener("click", () =>
      updateAccessAccount(b.dataset.adminToggle!, {
        is_admin: !accessControl!.accounts.find(
          (a) => a.user_id === b.dataset.adminToggle,
        )!.is_admin,
      }),
    ),
  );
  host
    .querySelectorAll<HTMLButtonElement>("[data-status-toggle]")
    .forEach((b) =>
      b.addEventListener("click", () => {
        const a = accessControl!.accounts.find(
          (x) => x.user_id === b.dataset.statusToggle,
        )!;
        updateAccessAccount(a.user_id, {
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
  try {
    accessControl = await request<AccessControl>("/v1/admin/access-control", {
      method: "PUT",
      body: JSON.stringify({
        maintenance_mode:
          document.querySelector<HTMLInputElement>("#maintenance-mode")!
            .checked,
        registration_enabled: document.querySelector<HTMLInputElement>(
          "#registration-enabled",
        )!.checked,
      }),
    });
    renderAccess();
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
async function createAdminAccount() {
  const status = document.querySelector("#create-account-status")!;
  status.textContent = "Đang tạo…";
  try {
    await request("/v1/admin/accounts", {
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
    accessControl = await request<AccessControl>("/v1/admin/access-control");
    renderAccess();
  } catch (error) {
    status.textContent = String(error);
    status.className = "toast error";
  }
}
async function updateAccessAccount(
  userId: string,
  changes: Record<string, unknown>,
) {
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
      dbTables,
      credentials,
    ] = await Promise.all([
      request<Overview>("/v1/admin/overview"),
      request<Settings>("/v1/admin/settings"),
      request<AccessControl>("/v1/admin/access-control"),
      request<CharacterCatalog>("/v1/admin/characters"),
      request<ModelConfig[]>("/v1/admin/models"),
      request<DbTable[]>("/v1/admin/database"),
      request<CredentialState>("/v1/admin/credentials"),
    ]);
    adminCharacters = [
      ...characterCatalog.preset_catalog,
      ...characterCatalog.user_characters,
    ];
    renderDashboard();
    renderAccess();
    renderContent();
    renderActionLogs();
    renderModels();
    renderAssistantSettings();
    renderDatabase();
    renderSettings();
  } catch (error) {
    document.querySelector("#dashboard")!.innerHTML =
      `<div class="panel error">${esc(error)}</div>`;
  }
}
document.querySelectorAll<HTMLButtonElement>("[data-view]").forEach((button) =>
  button.addEventListener("click", () => {
    document
      .querySelectorAll("[data-view]")
      .forEach((x) => x.classList.remove("active"));
    button.classList.add("active");
    document
      .querySelectorAll(".view")
      .forEach((x) => x.classList.remove("active"));
    document.querySelector(`#${button.dataset.view}`)!.classList.add("active");
    const labels: Record<string, [string, string]> = {
      access: [
        "Quản lý truy cập",
        "Chế độ bảo trì, tài khoản quản trị và trạng thái người dùng",
      ],
      dashboard: [
        "Tổng quan sản phẩm",
        "Dữ liệu vận hành trực tiếp từ hệ thống",
      ],
      content: [
        "Quản trị nội dung",
        "Nhân vật, phòng chat và tài liệu người dùng",
      ],
      conversations: [
        "Logchat",
        "Tổng hợp nội dung hỏi đáp, model, fallback và latency",
      ],
      "action-logs": [
        "Nhật ký hoạt động",
        "Theo dõi đăng nhập, truy cập chức năng, lỗi và thời gian xử lý",
      ],
      models: [
        "AI Role Play",
        "Danh sách model, API key, tham số và system prompt riêng",
      ],
      "assistant-config": [
        "AI Assistant",
        "Model chính, model dự phòng và prompt riêng cho từng tác vụ",
      ],
      database: [
        "Database Explorer",
        "Xem dữ liệu vận hành, user ID, job ID và nội dung",
      ],
      settings: [
        "Phân công model",
        "Chọn model cho từng tác vụ trong hệ thống",
      ],
    };
    if (button.dataset.view === "conversations") renderConversations();
    const label = labels[button.dataset.view!];
    document.querySelector("#page-title")!.textContent = label[0];
    document.querySelector("#page-subtitle")!.textContent = label[1];
  }),
);
document.querySelector("#refresh")!.addEventListener("click", load);
load();
