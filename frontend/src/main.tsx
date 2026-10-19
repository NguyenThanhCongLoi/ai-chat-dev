import { UiLanguageLoading } from "./UiLanguageLoading";
import "./app-styles.css";
import { lazy, Suspense } from "react";
const LorebookCms = lazy(() => import("./admin/RoleplayLorebook"));
const lorebookRoute = window.location.pathname === "/roleplay/lorebook/admin";
const WorldApp = lazy(() => import("./worlds/WorldApp"));
import { createRoot } from "react-dom/client";
import AssistantApp from "./assistant/AssistantApp";
import RolePlayApp from "./roleplay/RolePlayApp";

const worldRoute = window.location.pathname === "/worlds" || window.location.pathname === "/worlds/admin";
const rolePlayRoute =
  window.location.pathname === "/role-play-ai" ||
  window.location.pathname.startsWith("/role-play-ai/");
const assistantRoute =
  window.location.pathname === "/ai-assistant" ||
  window.location.pathname.startsWith("/ai-assistant/");
const internalWorkspaceRoute = new URLSearchParams(window.location.search).get("workspace") === "1";
if ((rolePlayRoute || assistantRoute) && !internalWorkspaceRoute) {
  window.history.replaceState(window.history.state, "", "/avibi-platform");
}
document.documentElement.dataset.app = rolePlayRoute && internalWorkspaceRoute ? "roleplay" : "assistant";
createRoot(document.getElementById("root")!).render(
  <>{lorebookRoute ? <Suspense fallback={<div style={{padding:40}}>Đang tải lorebook…</div>}><LorebookCms /></Suspense> : worldRoute ? <Suspense fallback={<div style={{padding:40}}>✧</div>}><WorldApp /></Suspense> : rolePlayRoute && internalWorkspaceRoute ? <RolePlayApp /> : assistantRoute && internalWorkspaceRoute ? <AssistantApp /> : <AssistantApp landingOnly />}<UiLanguageLoading /></>,
);
