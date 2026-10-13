/** assignments CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import { mountLoadingCat } from "../../roleplay/loadingCatDom";
import type { ModelConfig, ModelUpdate } from "../types";

export function createAssignmentsController(runtime: AdminRuntime) {
  function modelOptions(selected = "", includeEmpty = false) {
    const options = runtime.models
      .map(
        (x) =>
          `<option value="${runtime.esc(x.id)}" ${x.id === selected ? "selected" : ""}>${runtime.esc(x.name)} &middot; ${runtime.esc(x.model_id)}${x.enabled ? "" : " (\u0111ang \u1ea9n)"}</option>`,
      )
      .join("");
    return `${includeEmpty ? '<option value="">Ch\u01b0a ph\u00e2n c\u00f4ng</option>' : ""}${options}`;
  }

  function assignmentValue(purpose: string) {
    return runtime.models.find((x) => x.purposes.includes(purpose))?.id || "";
  }

  function assignmentState(modelId: string) {
    const m = runtime.models.find((x) => x.id === modelId);
    return !m
      ? ["bad", "Chưa gán"]
      : !m.enabled
        ? ["warn", "Model đang ẩn"]
        : ["ok", "Sẵn sàng"];
  }

  function renderSettings() {
    const host = document.querySelector("#settings");
    if (!host) return;
    const rows = runtime.ASSIGN_TASKS.map(([purpose, label, hint]) => {
      const current = runtime.assignmentValue(purpose),
        [kind, text] = runtime.assignmentState(current);
      return `<tr><td><b>${label}</b><br><small class="faint">${hint}</small></td><td style="min-width:220px"><select class="input sm" id="purpose-${purpose}" data-assign="${purpose}">${runtime.modelOptions(current, true)}</select></td><td><span class="chip ${kind}" id="assign-state-${purpose}">${text}</span></td><td class="act"><button class="iconbtn" data-assign-edit="${purpose}" title="Cấu hình model" aria-label="Cấu hình model của ${label}" ${current ? "" : "disabled"}>${runtime.ico("settings-sliders")}</button></td></tr>`;
    }).join("");
    host.innerHTML = `<section class="panel"><header><div><h3>Gán model cho tác vụ</h3><small class="faint">Prompt và tham số chỉnh trong Cấu hình AI của từng model</small></div><div class="row"><span class="statusText" id="assignment-status"></span><button class="btn pri" id="save-assignments">Lưu và áp dụng</button></div></header>

    <div class="tbl-wrap"><table class="dt"><thead><tr><th>Tác vụ</th><th>Model</th><th>Trạng thái</th><th class="act"></th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
    host
      .querySelector("#save-assignments")
      ?.addEventListener("click", runtime.saveModelAssignments);
    host.querySelectorAll<HTMLSelectElement>("[data-assign]").forEach((s) =>
      s.addEventListener("change", () => {
        const [kind, text] = runtime.assignmentState(s.value),
          chip = host.querySelector(`#assign-state-${s.dataset.assign}`)!;
        chip.className = `chip ${kind}`;
        chip.textContent = text;
        (
          host.querySelector(
            `[data-assign-edit="${s.dataset.assign}"]`,
          ) as HTMLButtonElement
        ).disabled = !s.value;
        const status = host.querySelector("#assignment-status")!;
        status.textContent = "Có thay đổi chưa lưu";
        status.className = "statusText";
      }),
    );
    host
      .querySelectorAll<HTMLButtonElement>("[data-assign-edit]")
      .forEach((b) =>
        b.addEventListener("click", () =>
          runtime.openAssignedModelEditor(
            (
              host.querySelector(
                `#purpose-${b.dataset.assignEdit}`,
              ) as HTMLSelectElement
            ).value,
          ),
        ),
      );
  }

  function openAssignedModelEditor(id: string) {
    if (!id) return;
    document.querySelector<HTMLButtonElement>('[data-view="models"]')?.click();
    runtime.modelsTab = "models";
    runtime.renderModels();
    runtime.editingModelId = id;
    runtime.fillModelEditor();
    runtime.openCmsModal("modal-model-edit");
  }

  async function saveModelAssignments() {
    const status = document.querySelector("#assignment-status")!;
    status.textContent = "Đang lưu…";
    status.className = "statusText";
    const purposes = runtime.ASSIGN_TASKS.map(([purpose]) => purpose);
    const selected = Object.fromEntries(
      purposes.map((p) => [
        p,
        document.querySelector<HTMLSelectElement>(`#purpose-${p}`)!.value,
      ]),
    );
    mountLoadingCat(status, "inline");
    try {
      let generation: ModelUpdate["expression_generation"];
      for (const model of runtime.models) {
        const preserved = model.purposes.filter((p) => !purposes.includes(p));
        const assigned = [
          ...preserved,
          ...purposes.filter((p) => selected[p] === model.id),
        ];
        const updated = await runtime.request<ModelUpdate>(
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
      if (generation) runtime.showGenerationNotice(generation);
      runtime.models = await runtime.request<ModelConfig[]>("/v1/admin/models");
      runtime.renderModels();
      runtime.renderSettings();
      runtime.renderAssistantSettings();
      const done = document.querySelector("#assignment-status");
      if (done) done.textContent = "Đã lưu và áp dụng";
    } catch (error) {
      status.textContent = String(error);
      status.className = "statusText error";
    }
  }

  return {
    modelOptions,
    assignmentValue,
    assignmentState,
    renderSettings,
    openAssignedModelEditor,
    saveModelAssignments,
  };
}
