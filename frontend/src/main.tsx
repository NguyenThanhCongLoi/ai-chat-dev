import { UiLanguageLoading } from "./UiLanguageLoading";
import "./app-styles.css";
import { createRoot } from "react-dom/client";
import AssistantApp from "./assistant/AssistantApp";
import RolePlayApp from "./roleplay/RolePlayApp";

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
  <>{rolePlayRoute && internalWorkspaceRoute ? <RolePlayApp /> : assistantRoute && internalWorkspaceRoute ? <AssistantApp /> : <AssistantApp landingOnly />}<UiLanguageLoading /></>,
);
