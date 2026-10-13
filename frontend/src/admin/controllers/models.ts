/** models CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import { mountLoadingCat } from "../../roleplay/loadingCatDom";
import type {
  Connection,
  CredentialState,
  ModelConfig,
  ModelUpdate,
} from "../types";

export function createModelsController(runtime: AdminRuntime) {
  function modelKeySource(m: ModelConfig) {
    if (m.has_api_key)
      return { ok: true, label: "Key riêng", hint: m.api_key_hint };
    const base = runtime.normBase(m.api_base);
    const entry = runtime.credentials?.bases?.find(
      (item) => runtime.normBase(item.api_base) === base,
    );
    if (entry)
      return { ok: true, label: "Key theo API base", hint: entry.hint };
    if (base === runtime.GATEWAY_BASE && runtime.credentials?.avibi.configured)
      return {
        ok: true,
        label: "Key gateway chung",
        hint: runtime.credentials.avibi.hint,
      };
    return { ok: false, label: "Chưa có API key", hint: "" };
  }

  function connections(): Connection[] {
    const bases = new Map<string, Connection>();
    const add = (base: string) => {
      const key = runtime.normBase(base);
      if (!bases.has(key)) {
        const gateway = key === runtime.GATEWAY_BASE;
        const entry = runtime.credentials?.bases?.find(
          (item) => runtime.normBase(item.api_base) === key,
        );
        const hint =
          entry?.hint ||
          (gateway && runtime.credentials?.avibi.configured
            ? runtime.credentials.avibi.hint
            : "");
        const source = entry
          ? "Key theo API base"
          : gateway
            ? runtime.credentials?.avibi.source === "modal_secret"
              ? "Modal Secret"
              : runtime.credentials?.avibi.configured
                ? "Lưu trong CMS"
                : "Chưa cấu hình"
            : "Chưa cấu hình";
        bases.set(key, {
          base: key,
          gateway,
          hint,
          source,
          ok: Boolean(hint),
          baseKeyId: entry?.id,
          models: [],
        });
      }
      return bases.get(key)!;
    };
    add(runtime.GATEWAY_BASE);
    (runtime.credentials?.bases || []).forEach((item) => add(item.api_base));
    runtime.models.forEach((m) => add(m.api_base).models.push(m));
    return [...bases.values()];
  }

  function renderModels() {
    const conns = runtime.connections();
    const brokenConns = conns.filter((c) => !c.ok && c.models.length).length;
    const tabs = `<div class="tabs mdlTabs" role="tablist"><button role="tab" aria-selected="${runtime.modelsTab === "models"}" data-models-tab="models">Model <span class="chip tnum">${runtime.models.length}</span></button><button role="tab" aria-selected="${runtime.modelsTab === "conns"}" data-models-tab="conns">Kết nối &amp; API key <span class="chip tnum${brokenConns ? " bad" : ""}">${conns.length}</span></button></div>`;
    let body = "";
    if (runtime.modelsTab === "conns") {
      body = `${brokenConns ? `<div class="note-info" style="background:var(--bad-soft)">${runtime.ico("info")}<span><b>${brokenConns} kết nối chưa có API key.</b> Các model dùng kết nối này sẽ lỗi hoặc phải chuyển sang dự phòng.</span></div>` : ""}

      <div class="mdlBar"><p class="muted" style="font-size:13px;margin:0">Model dùng key riêng nếu có; nếu không thì dùng key của API base tương ứng. Gateway AVIBI là kết nối mặc định.</p><button class="btn pri" id="conn-add">${runtime.ico("plus")}Thêm kết nối</button></div>

      <div class="conn-grid">${conns
        .map(
          (
            c,
          ) => `<article class="panel conn${c.ok || !c.models.length ? "" : " down"}">

        <header><div class="row" style="flex-wrap:nowrap;gap:10px;min-width:0"><span class="tl-ic">${runtime.ico(c.gateway ? "globe" : "link")}</span><div style="min-width:0"><h3>${runtime.esc(c.gateway ? "Gateway AVIBI" : runtime.baseHost(c.base))}</h3><small class="mono faint">${runtime.esc(c.base)}</small></div></div>

          <span class="chip ${c.ok ? "ok" : "bad"}">${c.ok ? "Đã có key" : "Thiếu key"}</span></header>

        <div class="pb">

          <div class="kvs">

            <div class="kv"><span>API key</span><span>${c.hint ? `<code class="mono">${runtime.esc(c.hint)}</code>` : '<span class="faint">Chưa có</span>'}</span></div>

            <div class="kv"><span>Nguồn key</span><span>${runtime.esc(c.source)}</span></div>

            <div class="kv"><span>Model dùng</span><span>${c.models.length ? c.models.map((m) => `<span class="chip">${runtime.esc(m.name)}</span>`).join(" ") : '<span class="faint">Chưa có model</span>'}</span></div>

          </div>

          <div class="row"><button class="btn sm" data-conn-edit="${runtime.esc(c.base)}">${runtime.ico("edit")}${c.ok ? "Đổi key" : "Cập nhật key"}</button>${c.gateway && runtime.credentials?.avibi.source === "cms" ? `<button class="btn sm" id="reset-credential">Dùng Modal Secret</button>` : ""}${c.baseKeyId ? `<button class="btn sm danger" data-delete-base-key="${runtime.esc(c.baseKeyId)}">Xóa key</button>` : ""}</div>

        </div></article>`,
        )
        .join("")}</div>`;
    } else {
      const q = runtime.modelFilter.q.toLowerCase();
      const providers = [
        ...new Set(runtime.models.map((m) => m.provider).filter(Boolean)),
      ];
      const list = runtime.models.filter(
        (m) =>
          (!q || `${m.name} ${m.model_id}`.toLowerCase().includes(q)) &&
          (runtime.modelFilter.provider === "all" ||
            m.provider === runtime.modelFilter.provider) &&
          (runtime.modelFilter.type === "all" ||
            runtime.modelType(m) === runtime.modelFilter.type) &&
          (runtime.modelFilter.status === "all" ||
            (runtime.modelFilter.status === "on") === m.enabled),
      );
      const on = runtime.models.filter((m) => m.enabled).length;
      const noKey = runtime.models.filter(
        (m) => !runtime.modelKeySource(m).ok,
      ).length;
      const unused = runtime.models.filter((m) => !m.purposes.length).length;
      const rows = list
        .map((m) => {
          const key = runtime.modelKeySource(m),
            use = runtime.modelUsage(m);
          return `<tr class="${m.enabled ? "" : "muted-row"}">

        <td><div class="row" style="flex-wrap:nowrap">${runtime.modelLogo(m)}<span><b>${runtime.esc(m.name)}</b><br><small class="mono faint">${runtime.esc(m.provider)} · ${runtime.esc(m.model_id)}</small></span></div></td>

        <td><span class="chip">${runtime.modelType(m)}</span></td>

        <td><span class="row" style="flex-wrap:nowrap;gap:6px" title="${runtime.esc(key.label)}${key.hint ? ` · ${runtime.esc(key.hint)}` : ""}"><span class="dot ${key.ok ? "ok" : "bad"}"></span>${runtime.esc(runtime.baseHost(m.api_base))}</span></td>

        <td>${
          use.length
            ? `<span title="${runtime.esc(use.join(", "))}">${use
                .slice(0, 2)
                .map((u) => `<span class="chip">${runtime.esc(u)}</span>`)
                .join(
                  " ",
                )}${use.length > 2 ? ` <span class="faint" style="font-size:12px">+${use.length - 2}</span>` : ""}</span>`
            : '<span class="faint">Chưa dùng</span>'
        }</td>

        <td><input type="checkbox" class="switch" data-toggle="${runtime.esc(m.id)}" ${m.enabled ? "checked" : ""} aria-label="Bật ${runtime.esc(m.name)}"></td>

        <td class="act"><div class="row" style="flex-wrap:nowrap;justify-content:flex-end"><button class="btn sm" data-edit="${runtime.esc(m.id)}">Cấu hình</button><button class="iconbtn" data-delete="${runtime.esc(m.id)}" aria-label="Xóa ${runtime.esc(m.name)}" style="color:var(--bad)">${runtime.ico("trash")}</button></div></td></tr>`;
        })
        .join("");
      body = `<div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))">

        <div class="kpi"><span>Tổng số model</span><b>${runtime.models.length}</b><small class="faint">${providers.length} nhà cung cấp</small></div>

        <div class="kpi"><span>Đang bật</span><b>${on}</b><small class="faint">${runtime.models.length - on} đang ẩn</small></div>

        <div class="kpi"><span>Thiếu API key</span><b style="color:var(--${noKey ? "bad" : "ink"})">${noKey}</b><small style="color:var(--${noKey ? "bad" : "ok"})">${noKey ? "model sẽ lỗi khi gọi" : "tất cả đã có key"}</small></div>

        <div class="kpi"><span>Chưa phân công</span><b>${unused}</b><small class="faint">${unused ? "chưa dùng cho tác vụ nào" : "mọi model đều được dùng"}</small></div></div>

      <section class="panel"><header><div class="filters mdlFilters">

          <label class="mdlSearch">${runtime.ico("search")}<input id="m-q" placeholder="Tìm tên hoặc model ID" value="${runtime.esc(runtime.modelFilter.q)}"></label>

          <label class="mdlFilter">Nhà cung cấp <select data-model-filter="provider" class="sm"><option value="all">Tất cả</option>${providers.map((p) => `<option ${runtime.modelFilter.provider === p ? "selected" : ""}>${runtime.esc(p)}</option>`).join("")}</select></label>

          <label class="mdlFilter">Loại <select data-model-filter="type" class="sm"><option value="all">Tất cả</option>${["Chat", "TTS", "Ảnh"].map((t) => `<option ${runtime.modelFilter.type === t ? "selected" : ""}>${t}</option>`).join("")}</select></label>

          <label class="mdlFilter">Trạng thái <select data-model-filter="status" class="sm"><option value="all">Tất cả</option><option value="on" ${runtime.modelFilter.status === "on" ? "selected" : ""}>Đang bật</option><option value="off" ${runtime.modelFilter.status === "off" ? "selected" : ""}>Đang ẩn</option></select></label></div>

        <button class="btn pri" id="model-add-open">${runtime.ico("plus")}Thêm model</button></header>

        ${runtime.models.length ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th>Model</th><th>Loại</th><th>Kết nối</th><th>Đang dùng cho</th><th>Bật</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div>` : ""}

        ${list.length ? "" : `<p class="empty" style="margin:14px">${runtime.models.length ? "Không có model phù hợp bộ lọc." : "Chưa có model. Bấm Thêm model để bắt đầu."}</p>`}</section>`;
    }
    const dialogs =
      runtime.cmsModal(
        "modal-model-add",
        "Thêm model",
        "Cấu hình AI",
        `<div class="dt-t"><b>Thông tin</b></div><div class="fields"><label class="field">Tên hiển thị *<input id="model-name"/></label><label class="field">Nhà cung cấp<input id="model-provider" value="AVIBI"/></label><label class="field">Model ID *<input id="model-id" class="mono" placeholder="openai/gpt-4.1-mini"/></label><label class="field">Logo chữ<input id="model-logo" maxlength="4" value="AI"/></label><label class="field full">API base<input id="model-base" class="mono" value="${runtime.GATEWAY_BASE}"/><small>Dùng chung key của kết nối nếu không nhập key riêng</small></label><label class="field full">API key riêng<input type="password" id="model-key" class="mono" placeholder="Để trống để dùng key của kết nối"/><small>Key được mã hóa khi lưu và chỉ hiện 4 ký tự cuối</small></label></div>`,
        `<span class="statusText" id="model-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="add-model">Thêm model</button>`,
      ) +
      runtime.cmsModal(
        "modal-model-edit",
        "Cấu hình model",
        "Cấu hình AI",
        `<div class="modelPurposeSummary" id="model-purpose-summary"></div><div class="dt-t"><b>Thông tin</b></div><div class="fields"><label class="field">Tên hiển thị<input id="edit-model-name"/></label><label class="field">Nhà cung cấp<input id="edit-model-provider"/></label><label class="field full">Model ID<input id="edit-model-id" class="mono"/></label><label class="field full">API base<input id="edit-model-base" class="mono"/></label><label class="field full" data-config-purpose="tts">Mã giọng TTS mặc định<input id="edit-model-tts-voice" maxlength="160" placeholder="Voice ID từ gateway"/><small>Áp dụng cho nhân vật chưa có mã giọng riêng. API base cần kết thúc bằng /v1.</small></label><label class="field full">API key mới<input id="edit-model-key" type="password" class="mono" placeholder="Để trống để giữ key hiện tại"/></label></div><div class="dt-t"><b>Tham số mặc định</b><small>Trợ lý hoặc tác vụ có thể ghi đè</small></div><div class="fields"><label class="field" data-config-generation="text">Temperature mặc định<input id="edit-model-temperature" type="number" min="0" max="2" step="0.05"/></label><label class="field" data-config-generation="text">Temperature câu ngắn<input id="edit-model-short-temperature" type="number" min="0" max="2" step="0.05"/></label><label class="field" data-config-generation="text">Max tokens mặc định<input id="edit-model-max-tokens" type="number" min="50" max="8000"/></label><label class="field" data-config-generation="text">Max tokens câu ngắn<input id="edit-model-short-max-tokens" type="number" min="50" max="8000"/></label><label class="field">Thinking mode<select id="edit-model-thinking"><option value="default">Theo mặc định gateway</option><option value="enabled">Bật</option><option value="disabled">Tắt</option></select></label><label class="field">Reasoning effort<select id="edit-model-effort"><option value="default">Theo mặc định gateway</option><option value="low">Low</option><option value="high">High</option><option value="max">Max</option></select></label><label class="field">Chờ gateway tối đa (giây)<input id="edit-model-gateway-timeout" type="number" min="4" max="45" step="1"/><small>Quá thời gian sẽ chuyển sang dự phòng</small></label></div><div class="dt-t" id="model-prompt-title"><b>System prompt theo tác vụ</b><small>Chỉ hiện các tác vụ model này đang được phân công</small></div><div class="fields"><label class="field full" data-config-purpose="response">Trả lời hội thoại<textarea class="largePrompt" id="edit-response-prompt"></textarea></label><label class="field full" data-config-purpose="suggestion">Gợi ý trả lời<textarea class="largePrompt" id="edit-suggestion-prompt"></textarea></label><label class="field full" data-config-purpose="compiler">Tạo nhân vật<textarea class="largePrompt" id="edit-compiler-prompt"></textarea></label><label class="field full" data-config-purpose="moderation">Kiểm duyệt<textarea class="largePrompt" id="edit-moderation-prompt"></textarea></label><label class="field full" data-config-purpose="emotion">Nhận diện cảm xúc<textarea class="largePrompt" id="edit-emotion-prompt"></textarea></label></div>`,
        `<span class="statusText" id="model-edit-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="save-model-profile">Lưu thay đổi</button>`,
      ) +
      runtime.cmsModal(
        "modal-conn",
        "Kết nối",
        "Kết nối &amp; API key",
        `<label class="field full">API base *<input id="credential-base-url" class="mono" placeholder="https://…/v1"/></label><label class="field full">API key *<input id="credential-base-key" type="password" class="mono" autocomplete="new-password" placeholder="Dán key vào đây"/><small>Key được mã hóa khi lưu và chỉ hiện 4 ký tự cuối</small></label>`,
        `<span class="statusText" id="credential-base-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="save-base-credential">Lưu key</button>`,
        false,
      );
    document.querySelector("#models")!.innerHTML = tabs + body + dialogs;
    runtime.bindModels();
  }

  function bindModels() {
    const host = document.querySelector("#models")!;
    host.querySelectorAll<HTMLButtonElement>("[data-models-tab]").forEach((b) =>
      b.addEventListener("click", () => {
        runtime.modelsTab = b.dataset.modelsTab as typeof runtime.modelsTab;
        runtime.renderModels();
      }),
    );
    host
      .querySelector<HTMLInputElement>("#m-q")
      ?.addEventListener("input", (event) => {
        runtime.modelFilter.q = (event.target as HTMLInputElement).value;
        runtime.renderModels();
        const input = document.querySelector<HTMLInputElement>("#m-q")!;
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      });
    host
      .querySelectorAll<HTMLSelectElement>("[data-model-filter]")
      .forEach((s) =>
        s.addEventListener("change", () => {
          (runtime.modelFilter as Record<string, string>)[
            s.dataset.modelFilter!
          ] = s.value;
          runtime.renderModels();
        }),
      );
    host
      .querySelector("#model-add-open")
      ?.addEventListener("click", () =>
        runtime.openCmsModal("modal-model-add"),
      );
    host
      .querySelector("#add-model")
      ?.addEventListener("click", runtime.addModel);
    host.querySelectorAll<HTMLButtonElement>("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => {
        runtime.editingModelId = b.dataset.edit!;
        runtime.fillModelEditor();
        runtime.openCmsModal("modal-model-edit");
      }),
    );
    host
      .querySelector("#save-model-profile")
      ?.addEventListener("click", runtime.saveModelProfile);
    host
      .querySelectorAll<HTMLInputElement>("[data-toggle]")
      .forEach((x) =>
        x.addEventListener(
          "change",
          () =>
            void runtime.patchModel(x.dataset.toggle!, { enabled: x.checked }),
        ),
      );
    host
      .querySelectorAll<HTMLButtonElement>("[data-delete]")
      .forEach((x) =>
        x.addEventListener("click", () =>
          runtime.deleteModel(x.dataset.delete!),
        ),
      );
    host.querySelector("#conn-add")?.addEventListener("click", () => {
      (host.querySelector("#credential-base-url") as HTMLInputElement).value =
        "";
      (
        host.querySelector("#credential-base-url") as HTMLInputElement
      ).readOnly = false;
      runtime.openCmsModal("modal-conn");
    });
    host.querySelectorAll<HTMLButtonElement>("[data-conn-edit]").forEach((b) =>
      b.addEventListener("click", () => {
        const url = host.querySelector(
          "#credential-base-url",
        ) as HTMLInputElement;
        url.value = b.dataset.connEdit!;
        url.readOnly = true;
        runtime.openCmsModal("modal-conn");
      }),
    );
    host
      .querySelector("#save-base-credential")
      ?.addEventListener("click", runtime.saveConnectionKey);
    host
      .querySelectorAll<HTMLButtonElement>("[data-delete-base-key]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () =>
            void runtime.deleteBaseCredential(
              button.dataset.deleteBaseKey || "",
            ),
        ),
      );
    host
      .querySelector("#reset-credential")
      ?.addEventListener("click", runtime.resetCredential);
  }

  async function saveConnectionKey() {
    const base = runtime.normBase(
      (
        document.querySelector("#credential-base-url") as HTMLInputElement
      ).value.trim(),
    );
    const key = (
      document.querySelector("#credential-base-key") as HTMLInputElement
    ).value.trim();
    const status = document.querySelector<HTMLElement>(
      "#credential-base-status",
    )!;
    if (!base || !key) {
      status.textContent = "Nhập API base và API key.";
      status.className = "statusText error";
      return;
    }
    status.textContent = "Đang lưu…";
    status.className = "statusText";
    try {
      if (base === runtime.GATEWAY_BASE) {
        const result = await runtime.request<CredentialState["avibi"]>(
          "/v1/admin/credentials/avibi",
          { method: "PUT", body: JSON.stringify({ api_key: key }) },
        );
        runtime.credentials = { ...runtime.credentials, avibi: result };
      } else {
        await runtime.request("/v1/admin/credentials/bases", {
          method: "PUT",
          body: JSON.stringify({ api_base: base, api_key: key }),
        });
        runtime.credentials = await runtime.request<CredentialState>(
          "/v1/admin/credentials",
        );
      }
      runtime.renderModels();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  function selectedModel() {
    return runtime.models.find((x) => x.id === runtime.editingModelId);
  }

  function fillModelEditor() {
    if (!document.querySelector("#edit-model-tts-voice")) {
      document
        .querySelector("#edit-model-base")
        ?.closest("label")
        ?.insertAdjacentHTML(
          "afterend",
          '<label class="field full" data-config-purpose="tts">Mã giọng TTS mặc định<input id="edit-model-tts-voice" maxlength="160" placeholder="Voice ID từ gateway"/><small>Áp dụng cho nhân vật chưa có mã giọng riêng. API base cần kết thúc bằng /v1.</small></label>',
        );
    }
    const model = runtime.selectedModel();
    if (!model) return;
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
      const node = document.querySelector<
        HTMLInputElement | HTMLTextAreaElement
      >(`#${id}`);
      if (node) node.value = value || "";
    });
    const textGeneration =
      !model.purposes.length ||
      model.purposes.some(
        (purpose) => purpose !== "tts" && purpose !== "avatar_image",
      );
    document
      .querySelectorAll<HTMLElement>(
        "#modal-model-edit [data-config-generation]",
      )
      .forEach((node) => {
        node.hidden = !textGeneration;
      });
    let promptCount = 0;
    document
      .querySelectorAll<HTMLElement>("#modal-model-edit [data-config-purpose]")
      .forEach((node) => {
        const purpose = node.dataset.configPurpose!;
        node.hidden = !(
          model.purposes.includes(purpose) ||
          model.purposes.includes(purpose + "_fallback") ||
          (purpose === "response" && model.purposes.includes("fallback"))
        );
        if (!node.hidden && node.querySelector("textarea")) promptCount++;
      });
    (document.querySelector("#model-prompt-title") as HTMLElement).hidden =
      !promptCount;
    const title = document.querySelector("#modal-model-edit header h2");
    if (title) title.textContent = `Cấu hình ${model.name}`;
    const summary = document.querySelector("#model-purpose-summary");
    if (summary)
      summary.innerHTML = model.purposes.length
        ? `<span class="faint" style="font-size:12px">Đang dùng cho:</span> ${model.purposes.map((p) => `<span class="chip">${runtime.esc(runtime.purposeLabel(p))}</span>`).join(" ")}`
        : `<span class="faint" style="font-size:12px">Chưa được dùng ở tác vụ nào.</span>`;
    const status = document.querySelector("#model-edit-status");
    if (status) {
      status.textContent = "";
      status.className = "statusText";
    }
  }

  async function saveModelProfile() {
    const model = runtime.selectedModel();
    const status = document.querySelector("#model-edit-status")!;
    if (!model) return;
    const value = (id: string) =>
      document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`)!
        .value;
    status.textContent = "\u0110ang l\u01b0u\u2026";
    mountLoadingCat(status, "inline");
    try {
      const updated = await runtime.request<ModelUpdate>(
        `/v1/admin/models/${model.id}`,
        {
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
        },
      );
      if (updated.expression_generation) {
        const plan = updated.expression_generation;
        runtime.showGenerationNotice(plan);
      }
      await runtime.reloadModels();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  async function resetCredential() {
    try {
      const result = await runtime.request<CredentialState["avibi"]>(
        "/v1/admin/credentials/avibi",
        { method: "DELETE" },
      );
      runtime.credentials = { ...runtime.credentials, avibi: result };
      runtime.renderModels();
    } catch (error) {
      alert(String(error));
    }
  }

  async function deleteBaseCredential(id: string) {
    try {
      await runtime.request(
        `/v1/admin/credentials/bases/${encodeURIComponent(id)}`,
        { method: "DELETE" },
      );
      runtime.credentials = await runtime.request<CredentialState>(
        "/v1/admin/credentials",
      );
      runtime.renderModels();
    } catch (error) {
      alert(String(error));
    }
  }

  async function reloadModels() {
    runtime.models = await runtime.request<ModelConfig[]>("/v1/admin/models");
    runtime.renderModels();
    runtime.renderSettings();
  }

  async function addModel() {
    const status = document.querySelector("#model-status")!;
    const value = (id: string) =>
      document.querySelector<HTMLInputElement>(`#${id}`)!.value;
    status.textContent = "Đang mã hóa và lưu…";
    mountLoadingCat(status, "inline");
    try {
      await runtime.request("/v1/admin/models", {
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
      await runtime.reloadModels();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  async function patchModel(id: string, body: Record<string, unknown>) {
    try {
      await runtime.request(`/v1/admin/models/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      await runtime.reloadModels();
    } catch (error) {
      alert(String(error));
      await runtime.reloadModels();
    }
  }

  async function deleteModel(id: string) {
    if (!confirm("Xóa cấu hình model này?")) return;
    try {
      await runtime.request(`/v1/admin/models/${id}?force=true`, {
        method: "DELETE",
      });
      await runtime.reloadModels();
    } catch (error) {
      alert(String(error));
    }
  }

  return {
    modelKeySource,
    connections,
    renderModels,
    bindModels,
    saveConnectionKey,
    selectedModel,
    fillModelEditor,
    saveModelProfile,
    resetCredential,
    deleteBaseCredential,
    reloadModels,
    addModel,
    patchModel,
    deleteModel,
  };
}
