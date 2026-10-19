/** characters CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import { mountLoadingCat } from "../../roleplay/loadingCatDom";
import { bindReactionSounds, refreshReactionSounds } from "../reactionSounds";
import type { AdminCharacter, ExpressionPreview } from "../types";
import { bindVoiceClone, refreshVoiceClone } from "../voiceClone";
import {
  bindVoiceSettings,
  fillVoiceSettings,
  voiceSettings,
} from "../voiceSettings";
import { refreshVoiceSources, setApiVoices } from "../voiceSources";

export function createCharactersController(runtime: AdminRuntime) {
  async function toggleCharacterVisibility(button: HTMLButtonElement) {
    const item = runtime.adminCharacters.find(
      (x) => x.id === button.dataset.toggleVisibility,
    );
    if (!item?.spec.preset_type) return;
    const next = item.home_section === "hidden" ? "auto" : "hidden";
    button.disabled = true;
    try {
      await runtime.request(
        `/v1/admin/presets/${encodeURIComponent(item.spec.preset_type)}/home-section`,
        {
          method: "PUT",
          body: JSON.stringify({ home_section: next }),
        },
      );
      item.home_section = next;
      document.querySelector("#cms-char-rows")!.innerHTML =
        runtime.contentRows();
    } catch (error) {
      button.disabled = false;
      button.title = error instanceof Error ? error.message : String(error);
      button.textContent = "Lỗi, thử lại";
    }
  }

  function contentRows() {
    const q = runtime.contentQuery.trim().toLowerCase();
    const list = runtime.adminCharacters.filter(
      (x) =>
        x.source === runtime.contentSource &&
        (!q ||
          `${x.spec.name} ${x.spec.identity.role} ${x.user_id || ""}`
            .toLowerCase()
            .includes(q)),
    );
    return (
      list
        .map(
          (x) =>
            `<tr><td><span class="cmsCharCell">${x.spec.avatar_url ? `<img src="${runtime.esc(x.spec.avatar_url)}" alt=""/>` : `<b>${runtime.esc(x.spec.name.slice(0, 1))}</b>`}<span><strong>${runtime.esc(x.spec.name)}</strong><small>${runtime.esc((x.spec.description || "").slice(0, 70))}</small></span></span></td><td>${runtime.esc(x.spec.identity.role)}</td><td>${x.source === "preset" ? (x.home_section === "hidden" ? '<span class="chip">Ẩn</span>' : '<span class="chip accent">Hiển thị</span>') : `<small>User ${runtime.esc(x.user_id)}</small>`}</td><td>${runtime.esc(x.spec.tts_voice_mode === "separate" ? "VI: " + (x.spec.tts_voice_vi || "Auto") + " / EN: " + (x.spec.tts_voice_en || "Auto") : x.spec.tts_voice_id || "Mặc định")}</td><td class="num"><span class="cmsActions">${x.source === "preset" ? runtime.visibilityButton(x) : ""}<button class="btn sm" data-edit-character="${runtime.esc(x.id)}">${runtime.ico("edit")}Sửa</button><a class="btn sm" href="/roleplay/lorebook/admin?character=${encodeURIComponent(x.source === "preset" ? x.id : "character:" + x.id)}">Lorebook</a></span></td></tr>`,
        )
        .join("") ||
      `<tr><td colspan="5"><div class="empty">Không có nhân vật phù hợp.</div></td></tr>`
    );
  }

  async function loadVbeeVoices() {
    const status = document.querySelector<HTMLElement>("#tts-voice-status");
    const list =
      document.querySelector<HTMLDataListElement>("#tts-voice-options");
    if (!status || !list) return;
    try {
      const result = await runtime.request<{
        voices: {
          id: string;
          name: string;
          gender: string;
          language: string;
        }[];
      }>("/v1/admin/tts/voices");
      if (!list.isConnected) return;
      setApiVoices(result.voices);
      list.innerHTML = result.voices
        .map(
          (voice) =>
            `<option value="${runtime.esc(voice.id)}" label="${runtime.esc(voice.name)} · ${voice.gender === "male" ? "Nam" : voice.gender === "female" ? "Nữ" : "Khác"} · ${runtime.esc(voice.language)}"></option>`,
        )
        .join("");
      status.textContent = `Đã tải ${result.voices.length} giọng từ API TTS. Để trống mã giọng để hệ thống tự chọn theo giới tính.`;
    } catch (error) {
      if (!list.isConnected) return;
      const message =
        error instanceof Error
          ? error.message
          : "Không tải được danh sách giọng API TTS.";
      setApiVoices([], message);
      if (status.isConnected) status.textContent = message;
    }
  }

  function renderContent() {
    if (!runtime.overview) return;
    const options = runtime.adminCharacters
      .map(
        (x) =>
          `<option value="${runtime.esc(x.id)}">${runtime.esc(x.spec.name)}${x.source === "preset" ? " · Preset" : ` · User ${runtime.esc(x.user_id)}`}</option>`,
      )
      .join("");
    const editFields = runtime.EDIT_FIELDS.replace(
      '<select id="character-select"></select>',
      `<select id="character-select">${options}</select>`,
    );
    document.querySelector("#content")!.innerHTML =
      `<section class="panel wide cmsPanel"><div class="cmsToolbar"><div class="tabs" role="tablist"><button class="${runtime.contentSource === "preset" ? "active" : ""}" data-content-source="preset">Nhân vật hệ thống <b>${runtime.adminCharacters.filter((x) => x.source === "preset").length}</b></button><button class="${runtime.contentSource === "user" ? "active" : ""}" data-content-source="user">Do người dùng tạo <b>${runtime.adminCharacters.filter((x) => x.source === "user").length}</b></button></div><label class="cmsSearch">${runtime.ico("search")}<input id="cms-char-q" placeholder="Tìm theo tên, vai trò, user…" value="${runtime.esc(runtime.contentQuery)}"/></label><span class="cmsSpacer"></span><button class="btn" id="backfill-system-expressions" type="button">${runtime.ico("picture")}Bổ sung ảnh biểu cảm</button><button class="btn primary" data-open="modal-create-character">${runtime.ico("plus-small")}Tạo nhân vật</button></div><div class="cmsTable"><table><thead><tr><th>Nhân vật</th><th>Vai trò</th><th>Hiển thị</th><th>Giọng TTS</th><th class="num">Thao tác</th></tr></thead><tbody id="cms-char-rows">${runtime.contentRows()}</tbody></table></div></section>` +
      runtime.cmsModal(
        "modal-create-character",
        "Tạo nhân vật hệ thống",
        "Nhân vật mới",
        `<div class="fields">${runtime.CREATE_FIELDS}</div>`,
        `<span class="statusText" id="new-character-status">Chưa tạo</span><button class="btn" data-close>Hủy</button><button class="btn primary" id="create-system-character">Tạo nhân vật</button>`,
      ) +
      runtime.cmsModal(
        "modal-edit-character",
        "Sửa nhân vật",
        "Chỉnh sửa",
        `<div class="fields">${editFields}</div>`,
        `<span class="statusText" id="character-status">Chọn nhân vật để chỉnh sửa</span><button class="btn" data-close>Đóng</button><button class="btn primary" id="save-character">Lưu nhân vật</button>`,
      );
    const select =
      document.querySelector<HTMLSelectElement>("#character-select");
    const selectField = select?.closest<HTMLElement>("label");
    if (selectField) selectField.style.display = "none";
    document
      .querySelectorAll<HTMLButtonElement>("[data-content-source]")
      .forEach((b) =>
        b.addEventListener("click", () => {
          runtime.contentSource = b.dataset.contentSource as "preset" | "user";
          runtime.renderContent();
        }),
      );
    document
      .querySelector<HTMLInputElement>("#cms-char-q")
      ?.addEventListener("input", (event) => {
        runtime.contentQuery = (event.target as HTMLInputElement).value;
        document.querySelector("#cms-char-rows")!.innerHTML =
          runtime.contentRows();
      });
    document
      .querySelector("#cms-char-rows")
      ?.addEventListener("click", (event) => {
        const toggle = (event.target as HTMLElement).closest<HTMLButtonElement>(
          "[data-toggle-visibility]",
        );
        if (toggle) return void runtime.toggleCharacterVisibility(toggle);
        const btn = (event.target as HTMLElement).closest<HTMLElement>(
          "[data-edit-character]",
        );
        if (!btn || !select) return;
        select.value = btn.dataset.editCharacter!;
        runtime.fillCharacter();
        const item = runtime.currentCharacter();
        if (item) void runtime.loadExpressionPreview(item);
        const avatarFile = document.querySelector<HTMLInputElement>(
          "#character-avatar-file",
        );
        if (avatarFile) avatarFile.value = "";
        document.querySelector("#modal-edit-character h2")!.textContent = item
          ? `Sửa · ${item.spec.name}`
          : "Sửa nhân vật";
        runtime.openCmsModal("modal-edit-character");
      });
    document
      .querySelector("#character-greeting")
      ?.closest("label")
      ?.insertAdjacentHTML(
        "afterend",
        '<label class="field">Giọng TTS<input id="character-tts-voice" list="tts-voice-options" maxlength="160" placeholder="Tự chọn theo giới tính"/><small>Để trống để tự chọn voice Vbee; nhập mã để dùng giọng riêng.</small></label><label class="field">Giới tính giọng<select id="character-tts-gender"><option value="unspecified">Tự nhận diện</option><option value="male">Nam</option><option value="female">Nữ</option></select><small>Dùng để tự chọn voice Vbee. Chọn rõ nếu nhân vật public chưa nhận diện đúng.</small></label>',
      );
    document
      .querySelector("#new-character-greeting")
      ?.closest("label")
      ?.insertAdjacentHTML(
        "afterend",
        '<label class="field">Giọng TTS<input id="new-character-tts-voice" list="tts-voice-options" maxlength="160" placeholder="Tự chọn theo giới tính"/></label><label class="field">Giới tính giọng<select id="new-character-tts-gender"><option value="unspecified">Tự nhận diện</option><option value="male">Nam</option><option value="female">Nữ</option></select></label>',
      );
    document
      .querySelector<HTMLButtonElement>("#backfill-system-expressions")
      ?.addEventListener("click", async (event) => {
        const button = event.currentTarget as HTMLButtonElement;
        button.disabled = true;
        try {
          const result = await runtime.request<{
            characters_queued: number;
            images_queued: number;
          }>("/v1/admin/system-characters/expressions/backfill", {
            method: "POST",
          });
          button.textContent = result.characters_queued
            ? `Đã xếp hàng ${result.characters_queued} nhân vật · ${result.images_queued} ảnh`
            : "Tất cả nhân vật có ảnh đã đủ biểu cảm";
          const selected = runtime.currentCharacter();
          if (selected) void runtime.loadExpressionPreview(selected);
        } catch (error) {
          button.textContent =
            error instanceof Error
              ? error.message
              : "Không thể tạo ảnh biểu cảm";
        } finally {
          button.disabled = false;
        }
      });
    document
      .querySelector("#content")
      ?.insertAdjacentHTML(
        "beforeend",
        '<datalist id="tts-voice-options"></datalist><p id="tts-voice-status" class="hint"></p>',
      );
    void runtime.loadVbeeVoices();
    bindVoiceSettings(runtime.loadVbeeVoices);
    bindVoiceClone(
      runtime.currentCharacter,
      (value) => {
        refreshReactionSounds();
        const updated = value as AdminCharacter;
        runtime.adminCharacters = runtime.adminCharacters.map((item) =>
          item.id === updated.id ? { ...item, ...updated } : item,
        );
        document.querySelector("#cms-char-rows")!.innerHTML =
          runtime.contentRows();
      },
      runtime.loadVbeeVoices,
    );
    bindReactionSounds(runtime.currentCharacter);
    runtime.bindCharacterEditor();
    runtime.bindAdminCreate();
  }

  function currentCharacter() {
    const id =
      document.querySelector<HTMLSelectElement>("#character-select")?.value;
    return runtime.adminCharacters.find((item) => item.id === id);
  }

  function fillCharacter() {
    const item = runtime.currentCharacter();
    if (!item) return;
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
      const input = document.querySelector<
        HTMLInputElement | HTMLTextAreaElement
      >(`#${id}`);
      if (input) input.value = value;
    });
    refreshVoiceSources();
    refreshVoiceClone();
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
      host = document.querySelector<HTMLElement>(
        "#character-expression-preview",
      );
    }
    if (!host) return;
    host.innerHTML = "<span>Đang kiểm tra bộ ảnh biểu cảm…</span>";
    mountLoadingCat(host, "compact");
    try {
      const data = await runtime.request<ExpressionPreview>(
        `/v1/admin/characters/${encodeURIComponent(item.id)}/expressions`,
      );
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
        fallback:
          "Đã dùng bộ ảnh xử lý từ avatar vì model ảnh không trả kết quả",
        missing: "Chưa tải ảnh nguồn hoặc chưa có bộ biểu cảm",
      };
      host.innerHTML = `<div class="expressionPreviewHead"><b>Bộ ảnh biểu cảm</b><span>${runtime.esc(meaning[data.quality] || data.quality)}${data.error ? `: ${runtime.esc(data.error)}` : ""} · ${Object.keys(data.images).length}/6 ảnh</span></div><div class="expressionPreviewGrid">${
        Object.entries(data.images)
          .map(
            ([emotion, url]) =>
              `<figure><img src="${runtime.esc(url)}?v=${Date.now()}" alt="${runtime.esc(labels[emotion] || emotion)}"/><figcaption>${runtime.esc(labels[emotion] || emotion)}</figcaption></figure>`,
          )
          .join("") || "<p>Chưa có ảnh được tạo.</p>"
      }</div>`;
      if (
        (data.status === "queued" || data.status === "processing") &&
        attempt < 60
      )
        window.setTimeout(() => {
          if (runtime.currentCharacter()?.id === item.id)
            void runtime.loadExpressionPreview(item, attempt + 1);
        }, 3000);
    } catch (error) {
      host.innerHTML = `<span>Chưa có bộ ảnh: ${runtime.esc(error)}</span>`;
    }
  }

  function bindCharacterEditor() {
    const select =
      document.querySelector<HTMLSelectElement>("#character-select");
    if (!select) return;
    select.addEventListener("change", () => {
      runtime.fillCharacter();
      const item = runtime.currentCharacter();
      if (item) runtime.loadExpressionPreview(item);
    });
    document
      .querySelector("#save-character")
      ?.addEventListener("click", runtime.saveCharacter);
    runtime.fillCharacter();
    const item = runtime.currentCharacter();
    if (item) runtime.loadExpressionPreview(item);
  }

  async function saveCharacter() {
    const item = runtime.currentCharacter();
    const status = document.querySelector("#character-status");
    if (!item || !status) return;
    status.textContent = "Đang lưu…";
    mountLoadingCat(status, "inline");
    status.className = "statusText";
    const value = (id: string) =>
      document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`)!
        .value;
    try {
      const endpoint =
        item.source === "preset"
          ? `/v1/admin/presets/${item.spec.preset_type}`
          : `/v1/admin/characters/${item.id}`;
      const updated = await runtime.request<AdminCharacter>(endpoint, {
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
        const placement = document.querySelector<HTMLSelectElement>(
          "#character-home-section",
        )!.value;
        await runtime.request(
          `/v1/admin/presets/${item.spec.preset_type}/home-section`,
          {
            method: "PUT",
            body: JSON.stringify({ home_section: placement }),
          },
        );
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
        const uploaded = await runtime.uploadAdminAvatar(avatarPath, avatar);
        updated.spec.avatar_url = uploaded.avatar_url;
      }
      runtime.adminCharacters = runtime.adminCharacters.map((x) =>
        x.id === updated.id ? { ...x, ...updated } : x,
      );
      const rows = document.querySelector("#cms-char-rows");
      if (rows) rows.innerHTML = runtime.contentRows();
      const option = document.querySelector<HTMLOptionElement>(
        `#character-select option[value="${CSS.escape(item.id)}"]`,
      );
      if (option)
        option.textContent = `${updated.spec.name}${item.source === "preset" ? " · Preset" : ` · User ${item.user_id}`}`;
      status.textContent = "Đã lưu và áp dụng cho cuộc trò chuyện mới";
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  function bindAdminCreate() {
    document
      .querySelector("#create-system-character")
      ?.addEventListener("click", runtime.createAdminCharacter);
  }

  async function uploadAdminAvatar(path: string, file: File) {
    const data = new FormData();
    data.append("file", file);
    const response = await fetch(path, { method: "PUT", body: data });
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<{
      avatar_url: string;
      expression_status?: string;
      images_queued?: number;
    }>;
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
      status.className = "statusText error";
      return;
    }
    status.textContent = "Đang tạo…";
    mountLoadingCat(status, "inline");
    status.className = "statusText";
    try {
      const created = await runtime.request<AdminCharacter>(
        "/v1/admin/presets",
        {
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
        },
      );
      const avatar = document.querySelector<HTMLInputElement>(
        "#new-character-avatar",
      )?.files?.[0];
      let imagesQueued = 0;
      if (avatar) {
        const uploaded = await runtime.uploadAdminAvatar(
          `/v1/admin/presets/${created.spec.preset_type}/avatar`,
          avatar,
        );
        created.spec.avatar_url = uploaded.avatar_url;
        imagesQueued = uploaded.images_queued || 0;
      }
      runtime.adminCharacters = [created, ...runtime.adminCharacters];
      runtime.characterCatalog.preset_catalog = [
        created,
        ...runtime.characterCatalog.preset_catalog,
      ];
      runtime.renderContent();
      const select =
        document.querySelector<HTMLSelectElement>("#character-select");
      if (select) {
        select.value = created.id;
        runtime.fillCharacter();
        void runtime.loadExpressionPreview(created);
      }
      runtime.openCmsModal("modal-edit-character");
      const createdStatus = document.querySelector("#character-status");
      if (createdStatus)
        createdStatus.textContent = imagesQueued
          ? `Đã tạo nhân vật · đang tạo ${imagesQueued} ảnh biểu cảm`
          : "Đã tạo nhân vật · tải ảnh nguồn để tạo biểu cảm";
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  return {
    toggleCharacterVisibility,
    contentRows,
    loadVbeeVoices,
    renderContent,
    currentCharacter,
    fillCharacter,
    loadExpressionPreview,
    bindCharacterEditor,
    saveCharacter,
    bindAdminCreate,
    uploadAdminAvatar,
    createAdminCharacter,
  };
}
