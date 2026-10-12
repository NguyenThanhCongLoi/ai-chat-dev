/** presentation CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import type { ModelUpdate } from "../types";

export function createPresentationController(runtime: AdminRuntime) {
  function formatVietnamLogTime(value: unknown): string {
    const raw = String(value ?? "").trim();
    if (!raw) return "";
    // Older database rows may omit the offset even though they were stored in UTC.
    const timestamp = new Date(
      /^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/i.test(raw) ? raw : `${raw}Z`,
    );
    return Number.isNaN(timestamp.getTime())
      ? raw
      : runtime.vietnamLogTime.format(timestamp);
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
    notice.innerHTML = `<b>Tạo ảnh biểu cảm</b><span>${runtime.esc(message)}</span><button aria-label="Đóng">×</button>`;
    notice.classList.add("show");
    notice
      .querySelector("button")
      ?.addEventListener("click", () => notice?.classList.remove("show"));
    window.setTimeout(() => notice?.classList.remove("show"), 15000);
    window.sessionStorage.setItem("expression_generation_notice", message);
  }

  function cmsModal(
    id: string,
    title: string,
    eyebrow: string,
    body: string,
    footer: string,
    wide = true,
  ) {
    return `<div class="scrim" id="${id}" hidden><section class="dialog${wide ? " wide" : ""}" role="dialog" aria-modal="true"><header><div><span class="eyebrow">${eyebrow}</span><h2>${title}</h2></div><button class="iconbtn" data-close aria-label="Đóng">${runtime.ico("cross-small")}</button></header><div class="body">${body}</div><footer>${footer}</footer></section></div>`;
  }

  function openCmsModal(id: string) {
    const el = document.getElementById(id);
    if (!el) return;
    el.hidden = false;
    el.classList.add("enter");
    setTimeout(() => el.classList.remove("enter"), 200);
  }

  function closeCmsModal(el: Element | null) {
    if (el instanceof HTMLElement) el.hidden = true;
  }

  return {
    formatVietnamLogTime,
    showGenerationNotice,
    cmsModal,
    openCmsModal,
    closeCmsModal,
  };
}
