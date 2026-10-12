/** homeSections CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import type { CmsHomeSection } from "../types";

export function createHomeSectionsController(runtime: AdminRuntime) {
  async function loadHomeSections() {
    try {
      const data = await runtime.request<CmsHomeSection[]>("/v1/home-sections");
      runtime.homeSections = Array.isArray(data) ? data : [];
    } catch {
      runtime.homeSections = [];
    }
    runtime.renderHomeSections();
  }

  function sectionMatches(rule: string, tags: string[]) {
    const presets = runtime.adminCharacters.filter(
      (x) => x.source === "preset" && x.home_section !== "hidden",
    );
    if (rule !== "tags") return presets;
    const wanted = tags.map((t) => t.toLowerCase()).filter(Boolean);
    return presets.filter((x) => {
      const text =
        `${x.spec.identity.role} ${x.spec.name} ${x.spec.description} ${x.spec.creation_type}`.toLowerCase();
      return wanted.some((t) => text.includes(t));
    });
  }

  function renderHomeSections() {
    const host = document.querySelector("#home-sections");
    if (!host) return;
    const rows = runtime.homeSections
      .map((s, i) => {
        const rule = s.rule || "tags",
          matches = runtime.sectionMatches(rule, s.tags || []);
        return `<tr><td class="num">${i + 1}</td><td><b>${runtime.esc(s.name)}</b></td><td>${runtime.esc(runtime.SECTION_RULES[rule] || rule)}<br><small class="faint">${runtime.esc(runtime.SECTION_RULE_HINTS[rule] || "")}</small></td>

        <td>${(s.tags || []).map((t) => `<span class="chip">${runtime.esc(t)}</span>`).join(" ") || '<span class="faint">—</span>'}</td>

        <td><div class="secAvatars">${matches
          .slice(0, 4)
          .map((c) => runtime.sectionAvatar(c))
          .join("")}<span class="faint tnum">${matches.length}</span></div></td>

        <td><input type="checkbox" class="switch" data-section-visible="${runtime.esc(s.id)}" ${s.hidden ? "" : "checked"} aria-label="Hiển thị ${runtime.esc(s.name)}"></td>

        <td class="act"><div class="row" style="flex-wrap:nowrap;justify-content:flex-end"><button class="iconbtn" data-section-move="${runtime.esc(s.id)}" data-dir="-1" aria-label="Lên" ${i ? "" : "disabled"}>${runtime.ico("arrow-small-up")}</button><button class="iconbtn" data-section-move="${runtime.esc(s.id)}" data-dir="1" aria-label="Xuống" ${i < runtime.homeSections.length - 1 ? "" : "disabled"}>${runtime.ico("arrow-small-down")}</button><button class="btn sm" data-section-edit="${runtime.esc(s.id)}">Sửa</button><button class="btn sm danger" data-section-delete="${runtime.esc(s.id)}">Xóa</button></div></td></tr>`;
      })
      .join("");
    host.innerHTML =
      `<section class="panel"><header><div><h3>Danh mục</h3><small class="faint">Thứ tự hiển thị từ trên xuống trên trang chủ</small></div><div class="row"><span class="statusText" id="section-list-status"></span><button class="btn pri" id="section-create-open">${runtime.ico("plus")}Tạo danh mục mới</button></div></header>

      ${runtime.homeSections.length ? `<div class="tbl-wrap"><table class="dt"><thead><tr><th class="num">Thứ tự</th><th>Tên danh mục</th><th>Luật lọc</th><th>Tag khớp</th><th>Nhân vật khớp</th><th>Hiển thị</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="empty" style="margin:14px">Chưa có danh mục. Bấm Tạo danh mục mới để thêm.</p>'}</section>` +
      runtime.cmsModal(
        "modal-section",
        "Tạo danh mục mới",
        "Danh mục trang chủ",
        `<label class="field full">Tên danh mục *<input id="section-name" placeholder="VD: Luyện ngoại ngữ"/></label><label class="field full">Luật lọc<select id="section-rule">${Object.entries(
          runtime.SECTION_RULES,
        )
          .filter(([k]) => k !== "featured")
          .map(([k, v]) => `<option value="${k}">${v}</option>`)
          .join(
            "",
          )}</select><small id="section-rule-hint"></small></label><label class="field full" id="section-tags-field">Tag khớp *<input id="section-tags" placeholder="tiếng Anh, JLPT, study"/><small>Phân tách bằng dấu phẩy</small></label><label class="switchRow full"><span><b>Hiển thị trên trang chủ</b></span><input type="checkbox" class="switch" id="section-visible" checked></label><div class="field full"><span>Xem trước <small class="faint" id="section-preview-count"></small></span><div class="hrow secPreview" id="section-preview"></div></div>`,
        `<span class="statusText" id="section-status"></span><button class="btn" data-close>Hủy</button><button class="btn pri" id="section-save">Tạo danh mục</button>`,
        false,
      );
    runtime.bindHomeSections();
  }

  function refreshSectionDialog() {
    const rule = (document.querySelector("#section-rule") as HTMLSelectElement)
      .value;
    const tags = (
      document.querySelector("#section-tags") as HTMLInputElement
    ).value
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
    (document.querySelector("#section-tags-field") as HTMLElement).hidden =
      rule !== "tags";
    document.querySelector("#section-rule-hint")!.textContent =
      runtime.SECTION_RULE_HINTS[rule] || "";
    const matches = runtime.sectionMatches(rule, tags);
    document.querySelector("#section-preview-count")!.textContent =
      `· ${matches.length} nhân vật khớp, hiển thị tối đa 8`;
    document.querySelector("#section-preview")!.innerHTML =
      matches
        .slice(0, 8)
        .map(
          (c) =>
            `<div class="secPreviewItem">${runtime.sectionAvatar(c, 44)}<span>${runtime.esc(c.spec.name)}</span></div>`,
        )
        .join("") ||
      '<span class="faint" style="font-size:12px">Chưa có nhân vật khớp.</span>';
  }

  function openSectionDialog(section?: CmsHomeSection) {
    runtime.editingSectionId = section?.id || "";
    (document.querySelector("#section-name") as HTMLInputElement).value =
      section?.name || "";
    (document.querySelector("#section-rule") as HTMLSelectElement).value =
      section?.rule && runtime.SECTION_RULES[section.rule]
        ? section.rule
        : "tags";
    (document.querySelector("#section-tags") as HTMLInputElement).value = (
      section?.tags || []
    ).join(", ");
    (document.querySelector("#section-visible") as HTMLInputElement).checked =
      !section?.hidden;
    document.querySelector("#modal-section header h2")!.textContent = section
      ? "Sửa danh mục"
      : "Tạo danh mục mới";
    document.querySelector("#section-save")!.textContent = section
      ? "Lưu thay đổi"
      : "Tạo danh mục";
    const status = document.querySelector("#section-status")!;
    status.textContent = "";
    status.className = "statusText";
    runtime.refreshSectionDialog();
    runtime.openCmsModal("modal-section");
  }

  function bindHomeSections() {
    const host = document.querySelector("#home-sections")!;
    host
      .querySelector("#section-create-open")
      ?.addEventListener("click", () => runtime.openSectionDialog());
    host
      .querySelectorAll<HTMLButtonElement>("[data-section-edit]")
      .forEach((b) =>
        b.addEventListener("click", () =>
          runtime.openSectionDialog(
            runtime.homeSections.find((s) => s.id === b.dataset.sectionEdit),
          ),
        ),
      );
    host
      .querySelector("#section-rule")
      ?.addEventListener("change", runtime.refreshSectionDialog);
    host
      .querySelector("#section-tags")
      ?.addEventListener("input", runtime.refreshSectionDialog);
    host
      .querySelector("#section-save")
      ?.addEventListener("click", () => void runtime.saveHomeSection());
    host
      .querySelectorAll<HTMLInputElement>("[data-section-visible]")
      .forEach((x) =>
        x.addEventListener(
          "change",
          () =>
            void runtime.updateHomeSection(x.dataset.sectionVisible!, {
              hidden: !x.checked,
            }),
        ),
      );
    host
      .querySelectorAll<HTMLButtonElement>("[data-section-move]")
      .forEach((b) =>
        b.addEventListener(
          "click",
          () =>
            void runtime.moveHomeSection(
              b.dataset.sectionMove!,
              Number(b.dataset.dir),
            ),
        ),
      );
    host
      .querySelectorAll<HTMLButtonElement>("[data-section-delete]")
      .forEach((b) =>
        b.addEventListener("click", () => {
          const section = runtime.homeSections.find(
            (s) => s.id === b.dataset.sectionDelete,
          );
          if (section && confirm(`Xóa danh mục “${section.name}”?`))
            void runtime.deleteHomeSection(section.id);
        }),
      );
  }

  function sectionListError(error: unknown) {
    const status = document.querySelector<HTMLElement>("#section-list-status");
    if (status) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  async function saveHomeSection() {
    const name = (
      document.querySelector("#section-name") as HTMLInputElement
    ).value.trim();
    const rule = (document.querySelector("#section-rule") as HTMLSelectElement)
      .value;
    const tags = (
      document.querySelector("#section-tags") as HTMLInputElement
    ).value
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
    const hidden = !(
      document.querySelector("#section-visible") as HTMLInputElement
    ).checked;
    const status = document.querySelector("#section-status")!;
    const missing = !name
      ? "Nhập tên danh mục."
      : rule === "tags" && !tags.length
        ? "Nhập ít nhất một tag."
        : "";
    status.className = missing ? "statusText error" : "statusText";
    if (missing) return void (status.textContent = missing);
    status.textContent = "Đang lưu…";
    try {
      const body = JSON.stringify({
        name,
        rule,
        tags: rule === "tags" ? tags : [],
        hidden,
      });
      if (runtime.editingSectionId)
        await runtime.request(
          `/v1/admin/home-sections/${encodeURIComponent(runtime.editingSectionId)}`,
          { method: "PATCH", body },
        );
      else
        await runtime.request("/v1/admin/home-sections", {
          method: "POST",
          body,
        });
      await runtime.loadHomeSections();
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  async function updateHomeSection(
    id: string,
    changes: Partial<CmsHomeSection>,
  ) {
    try {
      await runtime.request(
        `/v1/admin/home-sections/${encodeURIComponent(id)}`,
        { method: "PATCH", body: JSON.stringify(changes) },
      );
      await runtime.loadHomeSections();
    } catch (error) {
      await runtime.loadHomeSections();
      runtime.sectionListError(error);
    }
  }

  async function moveHomeSection(id: string, dir: number) {
    const ids = runtime.homeSections.map((s) => s.id),
      i = ids.indexOf(id),
      j = i + dir;
    if (i < 0 || j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    try {
      await runtime.request("/v1/admin/home-sections/order", {
        method: "PUT",
        body: JSON.stringify({ ids }),
      });
      await runtime.loadHomeSections();
    } catch (error) {
      runtime.sectionListError(error);
    }
  }

  async function deleteHomeSection(id: string) {
    try {
      await runtime.request(
        `/v1/admin/home-sections/${encodeURIComponent(id)}`,
        { method: "DELETE" },
      );
      await runtime.loadHomeSections();
    } catch (error) {
      runtime.sectionListError(error);
    }
  }

  return {
    loadHomeSections,
    sectionMatches,
    renderHomeSections,
    refreshSectionDialog,
    openSectionDialog,
    bindHomeSections,
    sectionListError,
    saveHomeSection,
    updateHomeSection,
    moveHomeSection,
    deleteHomeSection,
  };
}
