/** bootstrap CMS operations. State stays in admin.ts; this module owns its handlers. */
import type { AdminRuntime } from "../../admin";
import type {
  AccessControl,
  CharacterCatalog,
  CredentialState,
  DbTable,
  ModelConfig,
  Overview,
  Settings,
} from "../types";

export function createBootstrapController(runtime: AdminRuntime) {
  async function load() {
    try {
      [
        runtime.overview,
        runtime.settings,
        runtime.accessControl,
        runtime.characterCatalog,
        runtime.models,
        runtime.credentials,
      ] = await Promise.all([
        runtime.request<Overview>("/v1/admin/overview"),
        runtime.request<Settings>("/v1/admin/settings"),
        runtime.request<AccessControl>("/v1/admin/access-control"),
        runtime.request<CharacterCatalog>("/v1/admin/characters"),
        runtime.request<ModelConfig[]>("/v1/admin/models"),
        runtime.request<CredentialState>("/v1/admin/credentials"),
      ]);
      runtime.adminCharacters = [
        ...runtime.characterCatalog.preset_catalog,
        ...runtime.characterCatalog.user_characters,
      ];
      runtime.renderDashboard();
      runtime.renderAccess();
      runtime.renderModels();
      runtime.renderSettings();
      await runtime.loadDeferredView(
        document.querySelector<HTMLElement>(".view.active")?.id,
      );
    } catch (error) {
      document.querySelector("#dashboard")!.innerHTML =
        `<div class="panel error">${runtime.esc(error)}</div>`;
    }
  }

  async function loadDeferredView(view?: string) {
    const host = view ? document.getElementById(view) : null;
    try {
      if (view === "content") runtime.renderContent();
      else if (view === "home-sections") await runtime.loadHomeSections();
      else if (view === "assistant-config") {
        await runtime.loadAssistantProfiles();
        runtime.renderAssistantSettings();
      } else if (view === "database") {
        runtime.dbTables =
          await runtime.request<DbTable[]>("/v1/admin/database");
        runtime.renderDatabase();
      } else if (view === "action-logs") runtime.renderActionLogs();
      else if (view === "voice-logs") runtime.renderVoiceLogs();
      else if (view === "conversations") await runtime.renderConversations();
    } catch (error) {
      if (host)
        host.innerHTML = `<div class="panel error">${runtime.esc(error)}</div>`;
    }
  }

  return { load, loadDeferredView };
}
