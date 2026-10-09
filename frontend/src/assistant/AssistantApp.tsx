import { afterUiLanguagePaint, loadCompleteUiTranslations, setUiLanguageGate, uiLanguageErrorMessage } from "../uiLocales";
import { reportFirstChunk } from "../chatTiming";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  localizeInterface,
  setRuntimeTranslations,
  rememberLanguage,
  restoredLanguage,
  storedLanguage,
  supportedUiLanguage,
  UI_LANGUAGES,
  type UiLanguage,
} from "../i18n";
import { AutoGrowTextarea, Icon, ModeAvatar, ModeIllustration } from "../ui";
import { EmojiPicker } from "../EmojiPicker";
import { AssistantMarkdown } from "./AssistantMarkdown";
import { RolePlayLoadingCat } from "../roleplay/RolePlayLoadingCat";
import type { Account, Chat, WorkspaceRoom, WorkspaceCharacter, ChatMessage, UploadedFile, AssistantModel, SavedMemory, AssistantReminder, Mode } from "./types";
import { MODES, STARTERS, EN } from "./config";

const headers = (): Record<string, string> => {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};
async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: {
      ...headers(),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: path === "/v1/auth/me" && method === "GET" ? AbortSignal.timeout(15000) : undefined,
  });
  if (!response.ok) throw Object.assign(new Error(String(response.status)), { status: response.status });
  if (response.status === 204) return undefined as T;
  return response.json();
}
const localDateTimeValue = (value = new Date()) =>
  new Date(value.getTime() - value.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
function errorSource(value: string) {
  const normalized = value.replace(/^Error:\s*/, "");
  const authDetail = normalized.match(/^(?:400|403|409|422|503):\s*(.+)$/);
  if (authDetail) return authDetail[1];
  if (value.includes("401")) return "Phiên đăng nhập không hợp lệ.";
  if (value.includes("413")) return "Tệp tải lên quá lớn.";
  if (value.includes("429") || value.includes("503"))
    return "Dịch vụ AI tạm thời không khả dụng.";
  return "Đã xảy ra lỗi. Vui lòng thử lại.";
}

export default function AssistantApp({ landingOnly = false, }: {
    landingOnly?: boolean;
}) {
    const [account, setAccount] = useState<Account | null>(null), [ready, setReady] = useState(false), [authMode, setAuthMode] = useState<"login" | "register">("login"), [username, setUsername] = useState(""), [password, setPassword] = useState(""), [lampOn, setLampOn] = useState(false), [owlAway, setOwlAway] = useState(false), [loginTheme, setLoginTheme] = useState<"light" | "dark">(() => localStorage.getItem("preferred_theme") === "dark" ? "dark" : "light"), [displayName, setDisplayName] = useState(""), [language, setLanguage] = useState<UiLanguage>(storedLanguage), [translations, setTranslations] = useState<Record<string, string>>({}), [error, setError] = useState("");
    const [mode, setMode] = useState<Mode>(() => {
        const requested = new URLSearchParams(window.location.search).get("mode");
        return MODES.some((item) => item.id === requested) ? requested as Mode : "assistant_general";
    }), [chats, setChats] = useState<Chat[]>([]), [chat, setChat] = useState<Chat | null>(null), [messages, setMessages] = useState<ChatMessage[]>([]), [roomFiles, setRoomFiles] = useState<UploadedFile[]>([]), [text, setText] = useState(""), [file, setFile] = useState<File | null>(null), [availableModels, setAvailableModels] = useState<AssistantModel[]>([]), [selectedModel, setSelectedModel] = useState(""), [busy, setBusy] = useState(false), [sidebarOpen, setSidebarOpen] = useState(false);
    const [workspacePath, setWorkspacePath] = useState("/ai-assistant?workspace=1");
    useEffect(() => {
        if (landingOnly)
            document.documentElement.dataset.app = workspacePath.includes('/role-play-ai') ? 'roleplay' : 'assistant';
    }, [landingOnly, workspacePath]);
    const [workspaceFramePaths, setWorkspaceFramePaths] = useState([
        "/ai-assistant?workspace=1",
        "about:blank",
    ]);
    const [activeWorkspaceFrame, setActiveWorkspaceFrame] = useState(0);
    const [workspaceFrameReady, setWorkspaceFrameReady] = useState(false);
    const [workspaceLoadError, setWorkspaceLoadError] = useState(false);
    const [workspaceLoadingSession, setWorkspaceLoadingSession] = useState(0);
    useEffect(() => {
        if (!landingOnly || workspaceFrameReady) { setWorkspaceLoadError(false); return; }
        setWorkspaceLoadError(false);
        const timer = window.setTimeout(() => setWorkspaceLoadError(true), 20000);
        return () => window.clearTimeout(timer);
    }, [landingOnly, workspaceFrameReady, workspaceLoadingSession]);
    const workspaceTransitionStartedAt = useRef(0);
    const workspaceTransitionSequence = useRef(0);
    const workspaceRevealTimer = useRef<number | null>(null);
    useEffect(() => () => {
        if (workspaceRevealTimer.current !== null)
            window.clearTimeout(workspaceRevealTimer.current);
    }, []);
    const workspaceFrameRefs = useRef<Array<HTMLIFrameElement | null>>([]);
    const pendingWorkspaceFrame = useRef<number | null>(0);
    const loadedWorkspaceFrames = useRef(new Set<string>());
    const desiredWorkspacePath = useRef("/ai-assistant?workspace=1");
    const [rolePlayRooms, setRolePlayRooms] = useState<WorkspaceRoom[]>([]);
    const [workspaceCharacters, setWorkspaceCharacters] = useState<WorkspaceCharacter[]>([]);
    const loadWorkspaceCharacters = () => request<WorkspaceCharacter[]>("/v1/characters").then(setWorkspaceCharacters).catch(() => { });
    const [historyError, setHistoryError] = useState(false);
    const [chatsLoaded, setChatsLoaded] = useState(false);
    const [sessionHistoryOpen, setSessionHistoryOpen] = useState(() => window.matchMedia("(min-width: 1051px)").matches);
    const [workspaceCollapsed, setWorkspaceCollapsed] = useState(() => localStorage.getItem("avibi_workspace_collapsed") === "true");
    const [workspaceAccountMenuOpen, setWorkspaceAccountMenuOpen] = useState(false);
    const [workspaceAccountPanel, setWorkspaceAccountPanel] = useState<"profile" | "security" | null>(null);
    const [workspaceProfileName, setWorkspaceProfileName] = useState("");
    const [workspaceProfileBio, setWorkspaceProfileBio] = useState("");
    const [workspaceCurrentPassword, setWorkspaceCurrentPassword] = useState("");
    const [workspaceNewPassword, setWorkspaceNewPassword] = useState("");
    const [workspaceShowPasswords, setWorkspaceShowPasswords] = useState(false);
    const [workspaceAccountBusy, setWorkspaceAccountBusy] = useState(false);
    const [workspaceAccountMessage, setWorkspaceAccountMessage] = useState("");
    const [workspaceAccountError, setWorkspaceAccountError] = useState("");
    useEffect(() => {
        if (!workspaceAccountMenuOpen)
            return;
        const onEscape = (event: KeyboardEvent) => {
            if (event.key === "Escape")
                setWorkspaceAccountMenuOpen(false);
        };
        window.addEventListener("keydown", onEscape);
        return () => window.removeEventListener("keydown", onEscape);
    }, [workspaceAccountMenuOpen]);
    const [memoryPanelTab, setMemoryPanelTab] = useState<"memory" | "reminders">("memory");
    const [copiedId, setCopiedId] = useState("");
    const [memoryPanelOpen, setMemoryPanelOpen] = useState(() => new URLSearchParams(window.location.search).get("panel") === "memory"), [memoryEnabled, setMemoryEnabled] = useState(false), [savedMemories, setSavedMemories] = useState<SavedMemory[]>([]), [editingMemoryId, setEditingMemoryId] = useState(""), [editingMemoryDraft, setEditingMemoryDraft] = useState(""), [reminders, setReminders] = useState<AssistantReminder[]>([]), [memoryDraft, setMemoryDraft] = useState(""), [reminderDraft, setReminderDraft] = useState(""), [reminderTime, setReminderTime] = useState(""), [reminderToast, setReminderToast] = useState(""), [notificationsEnabled, setNotificationsEnabled] = useState(() => localStorage.getItem("assistant_client_notifications") !== "false");
    const fileInput = useRef<HTMLInputElement>(null);
    const loginPasswordInput = useRef<HTMLInputElement>(null);
    const loginCard = useRef<HTMLElement>(null);
    const loginLampButton = useRef<HTMLButtonElement>(null);
    const loginPasswordReveal = useRef<HTMLSpanElement>(null);
    const loginBeamPath = useRef<SVGPathElement>(null);
    const loginBeamSpot = useRef<SVGCircleElement>(null);
    const loginOwl = useRef<HTMLButtonElement>(null);
    useEffect(() => {
        if (!owlAway)
            return;
        const timer = window.setTimeout(() => setOwlAway(false), 10000);
        return () => window.clearTimeout(timer);
    }, [owlAway]);
    const activeChatIdRef = useRef<string | null>(null);
    const taskOpenSequence = useRef(0);
    const workspaceInitialChatRef = useRef("");
    const assistantStreamRef = useRef<AbortController | null>(null);
    const assistantStreams = useRef(new Set<AbortController>());
    const assistantStreamSequence = useRef(0);
    const memoryLoadSequence = useRef(0);
    function beginWorkspaceTransition() {
        workspaceTransitionSequence.current += 1;
        if (workspaceRevealTimer.current !== null)
            window.clearTimeout(workspaceRevealTimer.current);
        workspaceTransitionStartedAt.current = performance.now();
        setWorkspaceFrameReady(false);
        setWorkspaceLoadingSession(workspaceTransitionSequence.current);
    }
    function revealWorkspaceFrame(frameIndex: number) {
        const sequence = workspaceTransitionSequence.current;
        const startedAt = workspaceTransitionStartedAt.current;
        const remaining = startedAt ? Math.max(0, 900 - (performance.now() - startedAt)) : 0;
        if (workspaceRevealTimer.current !== null)
            window.clearTimeout(workspaceRevealTimer.current);
        workspaceRevealTimer.current = window.setTimeout(() => {
            if (sequence !== workspaceTransitionSequence.current)
                return;
            setActiveWorkspaceFrame(frameIndex);
            setWorkspaceFrameReady(true);
            workspaceTransitionStartedAt.current = 0;
            workspaceRevealTimer.current = null;
        }, remaining);
    }
    function navigateWorkspace(path: string) {
        setWorkspaceAccountMenuOpen(false);
        setWorkspacePath(path);
        desiredWorkspacePath.current = path;
        const appName = path.includes("/role-play-ai") ? "role-play-ai" : "ai-assistant";
        const routeToApp = (frameIndex: number) => {
            workspaceFrameRefs.current[frameIndex]?.contentWindow?.postMessage({ type: "avibi-workspace-navigate", path }, window.location.origin);
        };
        const currentFramePath = workspaceFramePaths[activeWorkspaceFrame];
        const currentApp = currentFramePath.includes("/role-play-ai") ? "role-play-ai" : currentFramePath.includes("/ai-assistant") ? "ai-assistant" : "";
        if (currentApp !== appName)
            beginWorkspaceTransition();
        if (currentApp === appName && loadedWorkspaceFrames.current.has(currentFramePath)) {
            pendingWorkspaceFrame.current = null;
            routeToApp(activeWorkspaceFrame);
            if (workspaceTransitionStartedAt.current)
                revealWorkspaceFrame(activeWorkspaceFrame);
            return;
        }
        const cachedFrame = workspaceFramePaths.findIndex((current) => (appName === "role-play-ai" ? current.includes("/role-play-ai") : current.includes("/ai-assistant")) &&
            loadedWorkspaceFrames.current.has(current));
        if (cachedFrame >= 0) {
            pendingWorkspaceFrame.current = null;
            routeToApp(cachedFrame);
            revealWorkspaceFrame(cachedFrame);
            return;
        }
        const nextSlot = workspaceFramePaths.findIndex((current) => current === "about:blank");
        const slot = nextSlot >= 0 ? nextSlot : 1 - activeWorkspaceFrame;
        pendingWorkspaceFrame.current = slot;
        const initialPath = appName === "role-play-ai" ? "/role-play-ai?workspace=1&view=characters" : "/ai-assistant?workspace=1";
        setWorkspaceFramePaths((current) => current.map((value, index) => index === slot ? initialPath : value));
    }
    function openWorkspaceAccount(panel: "profile" | "security") {
        setWorkspaceAccountMenuOpen(false);
        setWorkspaceProfileName(account?.display_name || "");
        setWorkspaceProfileBio(account?.bio || "");
        setWorkspaceCurrentPassword("");
        setWorkspaceNewPassword("");
        setWorkspaceShowPasswords(false);
        setWorkspaceAccountMessage("");
        setWorkspaceAccountError("");
        setWorkspaceAccountPanel(panel);
    }
    async function saveWorkspaceProfile() {
        if (!workspaceProfileName.trim())
            return;
        setWorkspaceAccountBusy(true);
        setWorkspaceAccountError("");
        try {
            const updated = await request<Account>("/v1/auth/me", "PATCH", {
                display_name: workspaceProfileName.trim(),
                bio: workspaceProfileBio.trim(),
            });
            setAccount(updated);
            localStorage.setItem("avibi_account_refresh", String(Date.now()));
            setWorkspaceAccountMessage("Đã lưu hồ sơ");
        }
        catch (reason) {
            setWorkspaceAccountError(String(reason));
        }
        finally {
            setWorkspaceAccountBusy(false);
        }
    }
    async function uploadWorkspaceAvatar(file: File) {
        setWorkspaceAccountBusy(true);
        setWorkspaceAccountError("");
        try {
            const form = new FormData();
            form.append("file", file);
            const response = await fetch("/v1/auth/me/avatar", { method: "POST", headers: headers(), body: form });
            if (!response.ok)
                throw new Error(String(response.status));
            const updated = await request<Account>("/v1/auth/me");
            setAccount(updated);
            localStorage.setItem("avibi_account_refresh", String(Date.now()));
            setWorkspaceAccountMessage("Đã cập nhật ảnh đại diện");
        }
        catch (reason) {
            setWorkspaceAccountError(String(reason));
        }
        finally {
            setWorkspaceAccountBusy(false);
        }
    }
    async function saveWorkspacePassword() {
        if (!workspaceCurrentPassword || workspaceNewPassword.length < 6)
            return;
        setWorkspaceAccountBusy(true);
        setWorkspaceAccountError("");
        try {
            await request<Account>("/v1/auth/me", "PATCH", {
                current_password: workspaceCurrentPassword,
                new_password: workspaceNewPassword,
            });
            setWorkspaceCurrentPassword("");
            setWorkspaceNewPassword("");
            setWorkspaceAccountMessage("Đã đổi mật khẩu");
        }
        catch (reason) {
            setWorkspaceAccountError(String(reason));
        }
        finally {
            setWorkspaceAccountBusy(false);
        }
    }
    useEffect(() => {
        if (!landingOnly)
            return;
        let historyTimer: number | undefined;
        const historySources = new Set<string>();
        const onFrameReady = (event: MessageEvent) => {
            if (event.origin !== window.location.origin)
                return;
            if (event.data?.type === "avibi-workspace-history-updated") {
                const sourceIndex = workspaceFrameRefs.current.findIndex(frame => frame?.contentWindow === event.source);
                if (sourceIndex < 0) return;
                historySources.add(workspaceFramePaths[sourceIndex].includes("/role-play-ai") ? "roleplay" : "assistant");
                if (historyTimer !== undefined) return;
                historyTimer = window.setTimeout(() => {
                    historyTimer = undefined;
                    if (historySources.has("assistant")) void loadChats().catch(() => {});
                    if (historySources.has("roleplay")) {
                        void request<WorkspaceRoom[]>("/v1/rooms").then(setRolePlayRooms).catch(() => {});
                        void loadWorkspaceCharacters();
                    }
                    historySources.clear();
                }, 250);
                return;
            }
            if (event.data?.type === "avibi-workspace-location") {
                const frameIndex = workspaceFrameRefs.current.findIndex((frame) => frame?.contentWindow === event.source);
                const path = event.data.path;
                if (frameIndex === activeWorkspaceFrame && typeof path === "string" &&
                    (path.startsWith("/ai-assistant?workspace=1") || path.startsWith("/role-play-ai?workspace=1")) &&
                    path.includes(desiredWorkspacePath.current.includes("/role-play-ai") ? "/role-play-ai" : "/ai-assistant"))
                    setWorkspacePath(path);
                return;
            }
            if (event.data?.type !== "avibi-workspace-ready")
                return;
            const frameIndex = workspaceFrameRefs.current.findIndex((frame) => frame?.contentWindow === event.source);
            if (frameIndex < 0)
                return;
            loadedWorkspaceFrames.current.add(workspaceFramePaths[frameIndex]);
            if (pendingWorkspaceFrame.current === frameIndex) {
                pendingWorkspaceFrame.current = null;
                revealWorkspaceFrame(frameIndex);
                const targetPath = desiredWorkspacePath.current;
                if (targetPath !== workspaceFramePaths[frameIndex]) {
                    window.setTimeout(() => workspaceFrameRefs.current[frameIndex]?.contentWindow?.postMessage({ type: "avibi-workspace-navigate", path: targetPath }, window.location.origin), 0);
                }
            }
        };
        window.addEventListener("message", onFrameReady);
        return () => {
            window.removeEventListener("message", onFrameReady);
            if (historyTimer !== undefined) window.clearTimeout(historyTimer);
        };
    }, [landingOnly, workspaceFramePaths, activeWorkspaceFrame]);
    function cancelAssistantStream() {
        assistantStreamSequence.current += 1;
        assistantStreams.current.forEach((controller) => controller.abort());
        assistantStreams.current.clear();
        assistantStreamRef.current?.abort();
        assistantStreamRef.current = null;
        setBusy(false);
    }
    useEffect(() => () => {
        assistantStreamSequence.current += 1;
        assistantStreams.current.forEach((controller) => controller.abort());
        assistantStreams.current.clear();
        assistantStreamRef.current?.abort();
    }, []);
    /* vùng scroll của chat */
    const conversationRef = useRef<HTMLElement>(null);
    useEffect(() => {
        if (!account)
            return;
        let cancelled = false;
        setAvailableModels([]);
        setSelectedModel("");
        request<AssistantModel[]>(`/v1/assistant/models?mode=${encodeURIComponent(mode)}`)
            .then((items) => {
            if (!cancelled) setAvailableModels(items);
        })
            .catch(() => {
            if (!cancelled) setAvailableModels([]);
        });
        return () => { cancelled = true; };
    }, [account, mode]);
    useEffect(() => {
        if (!account || !landingOnly)
            return;
        request<WorkspaceRoom[]>("/v1/rooms").then(setRolePlayRooms).catch(() => setRolePlayRooms([]));
        void loadWorkspaceCharacters();
    }, [account?.id, landingOnly]);
    useEffect(() => {
        if (!landingOnly)
            return;
        document.documentElement.dataset.app = workspacePath.includes("/role-play-ai") ? "roleplay" : "assistant";
    }, [landingOnly, workspacePath]);
    useEffect(() => {
        if (account && landingOnly && window.location.pathname === "/") {
            window.history.replaceState(window.history.state, "", "/avibi-platform");
        }
    }, [account?.id, landingOnly]);
    async function loadMemoryAndReminders(roomId = chat?.id) {
        const sequence = ++memoryLoadSequence.current;
        const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : "";
        const state = await request<{
            enabled: boolean;
            memories: SavedMemory[];
            reminders: AssistantReminder[];
        }>(`/v1/assistant/memory${query}`);
        if (sequence !== memoryLoadSequence.current)
            return;
        setMemoryEnabled(Boolean(state?.enabled));
        setReminders(Array.isArray(state?.reminders) ? state.reminders : []);
        if (activeChatIdRef.current === (roomId || null))
            setSavedMemories(Array.isArray(state?.memories) ? state.memories : []);
    }
    useEffect(() => {
        if (!account)
            return;
        void loadMemoryAndReminders(chat?.id).catch(() => { });
    }, [account?.id, chat?.id]);
    useEffect(() => {
        if (!account || !notificationsEnabled)
            return;
        if (window.location.search.includes("workspace=1"))
            return;
        const pollDue = () => {
            void request<AssistantReminder[]>("/v1/assistant/reminders/due").then((due) => {
                if (!due.length)
                    return;
                setReminders((current) => current.map((item) => due.some((ready) => ready.id === item.id) ? { ...item, last_notified_at: new Date().toISOString() } : item));
                const titles = due.map((item) => item.title).join(" · ");
                setReminderToast(titles);
                if (typeof Notification !== "undefined" && Notification.permission === "granted")
                    new Notification(tr("Đến giờ rồi"), { body: titles, tag: "avibi-assistant-reminders" });
            }).catch(() => { });
        };
        pollDue();
        const timer = window.setInterval(pollDue, 15000);
        return () => window.clearInterval(timer);
    }, [account?.id, notificationsEnabled, language]);
    useEffect(() => {
        const syncNotificationPreference = (event: StorageEvent) => {
            if (event.key === "assistant_client_notifications")
                setNotificationsEnabled(event.newValue !== "false");
        };
        window.addEventListener("storage", syncNotificationPreference);
        return () => window.removeEventListener("storage", syncNotificationPreference);
    }, []);
    useEffect(() => {
        const syncTheme = (event: StorageEvent) => {
            if (event.key !== "preferred_theme" || (event.newValue !== "light" && event.newValue !== "dark"))
                return;
            document.documentElement.dataset.theme = event.newValue;
            setLoginTheme(event.newValue);
            setAccount((current) => current && current.theme !== event.newValue
                ? { ...current, theme: event.newValue as Account["theme"] }
                : current);
        };
        window.addEventListener("storage", syncTheme);
        return () => window.removeEventListener("storage", syncTheme);
    }, []);
    useEffect(() => {
        const syncAccount = (event: StorageEvent) => {
            if (event.key === "ui_language" && event.newValue && UI_LANGUAGES.some((item) => item.code === event.newValue)) {
                setLanguage(event.newValue);
                document.documentElement.lang = event.newValue;
                setAccount((current) => current ? { ...current, language: event.newValue! } : current);
            }
            if (event.key === "avibi_account_refresh" && localStorage.getItem("auth_token")) {
                void request<Account>("/v1/auth/me").then(setAccount).catch(() => { });
            }
        };
        window.addEventListener("storage", syncAccount);
        return () => window.removeEventListener("storage", syncAccount);
    }, []);
    const [languageAttempt, setLanguageAttempt] = useState(0);
    const [appliedLanguage, setAppliedLanguage] = useState<UiLanguage | null>(null);
    useLayoutEffect(() => {
        if (appliedLanguage !== language) return;
        setRuntimeTranslations(translations);
        const root = document.getElementById("root");
        if (root) localizeInterface(root, language);
    });
    const tr = (value: string) => language === "vi"
        ? value
        : translations[value] || EN[value] || value;
    useEffect(() => {
        const preferred = (localStorage.getItem("preferred_theme") as Account["theme"] | null) ||
            "light";
        document.documentElement.dataset.theme = preferred;
        setLoginTheme(preferred);
        const token = localStorage.getItem("auth_token");
        if (!token) {
            setReady(true);
            return;
        }
        request<Account>("/v1/auth/me")
            .then((value) => {
            setAccount(value);
            const preferredLanguage = restoredLanguage(value.language);
            setLanguage(preferredLanguage);
            rememberLanguage(preferredLanguage);
            document.documentElement.dataset.theme = value.theme;
            localStorage.setItem("preferred_theme", value.theme);
            void loadChats().catch(() => setHistoryError(true));
        })
            .catch((reason) => {
            if (reason instanceof Error && Number(reason.message) === 401)
                localStorage.removeItem("auth_token");
            else
                setError("Không kiểm tra được phiên đăng nhập. Hãy tải lại trang để thử lại.");
        })
            .finally(() => setReady(true));
    }, []);
    useEffect(() => {
        if (landingOnly || !ready || window.parent === window)
            return;
        document.documentElement.dataset.workspaceReady = "true";
        window.parent.postMessage({ type: "avibi-workspace-ready" }, window.location.origin);
    }, [account?.id, ready, landingOnly]);
    useEffect(() => {
        if (landingOnly || !account || window.parent === window)
            return;
        window.parent.postMessage({ type: "avibi-workspace-history-updated" }, window.location.origin);
    }, [account?.id, chats, landingOnly]);
    useEffect(() => {
        if (landingOnly || !account || window.parent === window || (!chat && mode !== "assistant_general"))
            return;
        const path = chat
            ? `/ai-assistant?workspace=1&mode=${chat.mode}&chat=${chat.id}`
            : "/ai-assistant?workspace=1";
        window.parent.postMessage({ type: "avibi-workspace-location", path }, window.location.origin);
    }, [landingOnly, account?.id, chat?.id, mode]);
    useLayoutEffect(() => {
        let active = true;
        const controls = {
            retry: () => setLanguageAttempt((value) => value + 1),
            cancel: () => { void changeLanguage("vi").catch(() => {}); },
        };
        setUiLanguageGate({ language, busy: true, ...controls });
        setAppliedLanguage(null);
        const load = async () => {
            const values = await loadCompleteUiTranslations(language);
            if (!active) return;
            setTranslations(values);
            setAppliedLanguage(language);
            await afterUiLanguagePaint();
            if (active) setUiLanguageGate({ language, busy: false, ...controls });
        };
        void load().catch((error: unknown) => {
            if (active) setUiLanguageGate({
                language, busy: false,
                error: uiLanguageErrorMessage(error, language),
                ...controls,
            });
        });
        return () => { active = false; };
    }, [language, languageAttempt]);
    useEffect(() => {
        const element = conversationRef.current;
        if (!element)
            return;
        const frame = requestAnimationFrame(() => {
            element.scrollTo({
                top: element.scrollHeight,
                behavior: "smooth",
            });
        });
        return () => cancelAnimationFrame(frame);
    }, [messages, busy, chat?.id]);
    const visibleChatCount = (nextMode: Mode) => nextMode === "assistant_general"
        ? chats.filter((item) => item.mode === nextMode).length
        : Number(chats.some((item) => item.mode === nextMode));
    async function loadChats() {
        const rooms = await request<Chat[]>("/v1/assistant/chats");
        setChats(rooms);
        setChat((current) => current ? rooms.find((item) => item.id === current.id) || current : null);
        setChatsLoaded(true);
        setHistoryError(false);
    }
    async function openChat(item: Chat) {
        const sequence = ++taskOpenSequence.current;
        cancelAssistantStream();
        activeChatIdRef.current = item.id;
        setChat(item);
        setMode(item.mode);
        setMessages([]);
        setRoomFiles([]);
        setBusy(true);
        try {
            const [history, files] = await Promise.all([
                request<ChatMessage[]>(`/v1/assistant/chats/${item.id}/messages`),
                request<UploadedFile[]>(`/v1/assistant/chats/${item.id}/files`),
            ]);
            if (activeChatIdRef.current !== item.id || sequence !== taskOpenSequence.current)
                return;
            setMessages(history);
            setRoomFiles(files);
            setSidebarOpen(false);
            void loadMemoryAndReminders(item.id).catch(() => { });
        }
        finally {
            if (activeChatIdRef.current === item.id && sequence === taskOpenSequence.current)
                setBusy(false);
        }
    }
    function newChat(nextMode: Mode = "assistant_general") {
        taskOpenSequence.current += 1;
        cancelAssistantStream();
        activeChatIdRef.current = null;
        setChat(null);
        setSavedMemories([]);
        setMessages([]);
        setRoomFiles([]);
        setMode(nextMode);
        setText("");
        setFile(null);
        setSidebarOpen(false);
    }
    async function openTaskRoom(nextMode: Mode) {
        const sequence = ++taskOpenSequence.current;
        cancelAssistantStream();
        try {
            const existing = chats.find((item) => item.mode === nextMode);
            if (sequence !== taskOpenSequence.current)
                return;
            setSessionHistoryOpen(window.matchMedia("(min-width: 1051px)").matches);
            if (existing) {
                await openChat(existing);
            }
            else {
                await createTaskSession(nextMode);
            }
        }
        catch (reason) {
            if (sequence === taskOpenSequence.current)
                setError(String(reason));
        }
    }
    async function createTaskSession(nextMode: Mode = mode) {
        const sequence = ++taskOpenSequence.current;
        cancelAssistantStream();
        setError("");
        try {
            if (nextMode !== "assistant_general") {
                const existing = chats.find((item) => item.mode === nextMode);
                if (existing) {
                    await openChat(existing);
                    return;
                }
            }
            const created = await request<Chat>("/v1/assistant/chats", "POST", { mode: nextMode });
            if (sequence !== taskOpenSequence.current)
                return;
            setChats((current) => current.some((item) => item.id === created.id) ? current : [created, ...current]);
            setText("");
            setFile(null);
            await openChat(created);
        }
        catch (reason) {
            if (sequence === taskOpenSequence.current)
                setError(String(reason));
        }
    }
    useEffect(() => {
        if (!account || !chatsLoaded || !window.location.search.includes("workspace=1"))
            return;
        const params = new URLSearchParams(window.location.search);
        const chatId = params.get("chat");
        if (chatId && chatId !== workspaceInitialChatRef.current) {
            const item = chats.find((candidate) => candidate.id === chatId);
            if (item) {
                workspaceInitialChatRef.current = chatId;
                void openChat(item);
            }
            return;
        }
        const requested = params.get("mode");
        if (requested && !workspaceInitialChatRef.current) {
            const item = MODES.find((candidate) => candidate.id === requested);
            if (item) {
                workspaceInitialChatRef.current = `task:${requested}`;
                void openTaskRoom(item.id);
            }
        }
    }, [account, chats, chatsLoaded]);
    useEffect(() => {
        if (landingOnly || window.parent === window)
            return;
        const onWorkspaceNavigation = (event: MessageEvent) => {
            if (event.origin !== window.location.origin || event.data?.type !== "avibi-workspace-navigate")
                return;
            const params = new URL(event.data.path, window.location.origin).searchParams;
            if (params.get("panel") === "memory") {
                setMemoryPanelOpen(true);
                return;
            }
            setMemoryPanelOpen(false);
            const chatId = params.get("chat");
            if (chatId) {
                const item = chats.find((candidate) => candidate.id === chatId);
                if (item)
                    void openChat(item);
                return;
            }
            const requested = params.get("mode");
            if (requested === "assistant_general") {
                workspaceInitialChatRef.current = "task:assistant_general";
                void openTaskRoom("assistant_general");
            }
            else if (requested && MODES.some((item) => item.id === requested)) {
                workspaceInitialChatRef.current = `task:${requested}`;
                void openTaskRoom(requested as Mode);
            }
            else {
                workspaceInitialChatRef.current = "";
                newChat("assistant_general");
            }
        };
        window.addEventListener("message", onWorkspaceNavigation);
        return () => window.removeEventListener("message", onWorkspaceNavigation);
    }, [landingOnly, chats]);
    async function removeRoomFile(item: UploadedFile) {
        if (!chat)
            return;
        await request(`/v1/assistant/chats/${chat.id}/files/${item.id}`, "DELETE");
        setRoomFiles((current) => current.filter((value) => value.id !== item.id));
    }
    async function removeChat(item: Chat) {
        await request(`/v1/assistant/chats/${item.id}`, "DELETE");
        const remaining = chats.filter((value) => value.id !== item.id);
        setChats(remaining);
        if (chat?.id === item.id) {
            const next = remaining.find((value) => value.mode === item.mode);
            if (next)
                await openChat(next);
            else
                newChat(item.mode);
        }
    }
    async function removeWorkspaceConversation(id: string, kind: "assistant" | "roleplay", label: string) {
        if (!window.confirm(`${tr("Xóa cuộc trò chuyện")} “${label}”?`))
            return;
        try {
            const selected = rolePlayRooms.find((item) => item.id === id);
            const targets = kind === "roleplay" && selected?.character_ids?.length === 1
                ? rolePlayRooms.filter((item) => item.character_ids?.length === 1 &&
                    item.character_ids[0] === selected.character_ids![0])
                : [];
            const deletedIds = targets.length ? targets.map((item) => item.id) : [id];
            for (const targetId of deletedIds) {
                try {
                    await request(kind === "assistant" ? `/v1/assistant/chats/${targetId}` : `/v1/rooms/${targetId}`, "DELETE");
                } catch (error) {
                    // Another frame/tab may already have deleted the room.
                    if (!(error instanceof Error) || (error as Error & {status?: number}).status !== 404)
                        throw error;
                }
            }
            if (kind === "assistant")
                setChats((current) => current.filter((item) => item.id !== id));
            else
                setRolePlayRooms((current) => current.filter((item) => !deletedIds.includes(item.id)));
            if (deletedIds.some((targetId) => workspacePath.includes(targetId)))
                navigateWorkspace(kind === "assistant" ? "/ai-assistant?workspace=1" : "/role-play-ai?workspace=1&view=characters");
        }
        catch (reason) {
            window.alert(String(reason));
        }
    }
    async function changeLanguage(next: UiLanguage) {
        next = supportedUiLanguage(next);
        setLanguageAttempt((value) => value + 1);
        setLanguage(next);
        rememberLanguage(next);
        if (account)
            setAccount(await request<Account>("/v1/auth/me", "PATCH", { language: next }));
    }
    async function submitAuth() {
        setError("");
        try {
            const response = await fetch(`/v1/auth/${authMode}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password, display_name: displayName }),
            });
            if (!response.ok) {
                const result = await response.json().catch(() => null);
                const detail = typeof result?.detail === "string" ? result.detail : "";
                throw new Error(detail ? `${response.status}: ${detail}` : String(response.status));
            }
            const value = await response.json() as Account & {
                token: string;
            };
            localStorage.setItem("auth_token", value.token);
            setAccount(value);
            const theme = (localStorage.getItem("preferred_theme") as Account["theme"] | null) ||
                value.theme;
            const updated = await request<Account>("/v1/auth/me", "PATCH", { language, theme }).catch(() => value);
            setAccount(updated);
            document.documentElement.dataset.theme = theme;
            localStorage.setItem("preferred_theme", theme);
            await loadChats().catch(() => setHistoryError(true));
        }
        catch (reason) {
            setError(String(reason));
        }
    }
    async function toggleTheme() {
        const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = theme;
        localStorage.setItem("preferred_theme", theme);
        setLoginTheme(theme);
        if (account)
            setAccount(await request<Account>("/v1/auth/me", "PATCH", { theme }));
    }
    async function logout() {
        await request("/v1/auth/logout", "POST", {}).catch(() => { });
        localStorage.removeItem("auth_token");
        window.location.assign("/");
    }
    async function toggleMemory(enabled: boolean) {
        const result = await request<{
            enabled: boolean;
        }>("/v1/assistant/memory", "PATCH", { enabled });
        setMemoryEnabled(result.enabled);
        if (!enabled)
            setSavedMemories([]);
    }
    async function saveMemory() {
        const content = memoryDraft.trim();
        if (!content)
            return;
        if (!chat)
            throw new Error("Mở một cuộc hội thoại trước khi lưu ghi nhớ.");
        await request<SavedMemory>("/v1/assistant/memory/items", "POST", { content, room_id: chat.id });
        setMemoryDraft("");
        await loadMemoryAndReminders(chat.id);
    }
    async function removeMemory(item: SavedMemory) {
        await request(`/v1/assistant/memory/items/${item.id}`, "DELETE");
        setSavedMemories((current) => current.filter((value) => value.id !== item.id));
    }
    async function updateMemory(item: SavedMemory) {
        const updated = await request<SavedMemory>(`/v1/assistant/memory/items/${item.id}`, "PATCH", { content: editingMemoryDraft });
        setSavedMemories((current) => current.map((value) => value.id === item.id ? updated : value));
        setEditingMemoryId("");
        setEditingMemoryDraft("");
    }
    async function createReminder() {
        if (!reminderDraft.trim() || !reminderTime)
            return;
        await request("/v1/assistant/reminders", "POST", { title: reminderDraft.trim(), due_at: new Date(reminderTime).toISOString() });
        setReminderDraft("");
        setReminderTime("");
        await loadMemoryAndReminders();
    }
    async function updateReminder(item: AssistantReminder, changes: Partial<AssistantReminder>) {
        const updated = await request<AssistantReminder>(`/v1/assistant/reminders/${item.id}`, "PATCH", changes);
        setReminders((current) => current.map((value) => value.id === item.id ? updated : value));
    }
    async function removeReminder(item: AssistantReminder) {
        await request(`/v1/assistant/reminders/${item.id}`, "DELETE");
        setReminders((current) => current.filter((value) => value.id !== item.id));
    }
    async function toggleClientNotifications(enabled: boolean) {
        if (enabled && typeof Notification !== "undefined" && Notification.permission === "default")
            await Notification.requestPermission().catch(() => "denied");
        localStorage.setItem("assistant_client_notifications", String(enabled));
        setNotificationsEnabled(enabled);
        if (!enabled)
            setReminderToast("");
    }
    async function send(messageOverride = "", attachmentOverride?: File | null) {
        const directMessage = messageOverride.trim();
        const pendingAttachment = attachmentOverride ?? file;
        if ((!directMessage && !text.trim() && !pendingAttachment) || busy)
            return;
        const sentAt = performance.now();
        let firstChunkMs: number | undefined;
        const streamSequence = ++assistantStreamSequence.current;
        const controller = new AbortController();
        assistantStreamRef.current = controller;
        assistantStreams.current.add(controller);
        setBusy(true);
        setError("");
        let activeStreamId = "";
        let streamCompleted = false;
        let sentChatId = chat?.id || "";
        try {
            let active = chat;
            if (!active) {
                active = await request<Chat>("/v1/assistant/chats", "POST", { mode });
                if (controller.signal.aborted || streamSequence !== assistantStreamSequence.current)
                    return;
                const [history, files] = active.is_new ? [[], []] : await Promise.all([
                    request<ChatMessage[]>(`/v1/assistant/chats/${active.id}/messages`),
                    request<UploadedFile[]>(`/v1/assistant/chats/${active.id}/files`),
                ]);
                if (controller.signal.aborted || streamSequence !== assistantStreamSequence.current)
                    return;
                setMessages(history);
                setRoomFiles(files);
                setChat(active);
                activeChatIdRef.current = active.id;
                sentChatId = active.id;
                setChats((current) => current.some((item) => item.id === active!.id) ? current : [active!, ...current]);
            }
            const attached = attachmentOverride !== undefined
                ? attachmentOverride
                : directMessage
                    ? null
                    : file;
            const attachmentIds: string[] = [];
            if (attached) {
                const form = new FormData();
                form.append("file", attached);
                const upload = await fetch(`/v1/assistant/chats/${active.id}/files`, {
                    method: "POST",
                    headers: headers(),
                    body: form,
                    signal: controller.signal,
                });
                if (!upload.ok) {
                    const failure = (await upload.json().catch(() => ({}))) as {
                        detail?: string;
                    };
                    throw new Error(`${upload.status}: ${failure.detail || "Upload failed"}`);
                }
                const uploaded = (await upload.json()) as UploadedFile;
                attachmentIds.push(uploaded.id);
                setRoomFiles((current) => [...current, uploaded]);
                setFile(null);
            }
            const message = directMessage ||
                text.trim() ||
                (attached ? "Hãy phân tích nội dung trong tệp tôi vừa gửi." : "");
            const outgoing: ChatMessage = {
                id: crypto.randomUUID(),
                role: "user",
                text: message,
                ...(attached && attachmentIds.length
                    ? {
                        sources: [
                            {
                                index: 1,
                                document_id: attachmentIds[0],
                                filename: attached.name,
                            },
                        ],
                    }
                    : {}),
            };
            setMessages((current) => [
                ...current.map((item) => ({ ...item, suggestions: undefined })),
                outgoing,
            ]);
            if (!directMessage)
                setText("");
            const response = await fetch(`/v1/assistant/chats/${active.id}/messages/stream`, {
                method: "POST",
                headers: {
                    ...headers(),
                    "Content-Type": "application/json",
                    Accept: "text/event-stream",
                },
                body: JSON.stringify({
                    message,
                    attachment_ids: attachmentIds,
                    model_id: availableModels.some((item) => item.id === selectedModel) ? selectedModel : "",
                }),
                signal: controller.signal,
            });
            if (!response.ok || !response.body)
                throw new Error(await response.text());
            const streamId = (activeStreamId = "stream-" + crypto.randomUUID());
            const reader = response.body.getReader(), decoder = new TextDecoder();
            let buffer = "", streamed = false, answerCompleted = false;
            let suggestionReceipt: { messageId: string; options: string[]; milliseconds: number } | undefined;
            const handleEvent = (block: string) => {
                if (controller.signal.aborted || activeChatIdRef.current !== active.id)
                    return;
                let event = "", raw = "";
                for (const line of block.split("\n")) {
                    if (line.startsWith("event:"))
                        event = line.slice(6).trim();
                    if (line.startsWith("data:"))
                        raw += line.slice(5).trim();
                }
                if (!raw)
                    return;
                const payload = JSON.parse(raw) as ChatMessage & {
                    message?: string;
                    text?: string;
                };
                if (event === "suggestions") {
                    const suggestionPayload = payload as unknown as { message_id: string; suggestions: string[] };
                    suggestionReceipt = { messageId: suggestionPayload.message_id, options: suggestionPayload.suggestions, milliseconds: performance.now() - sentAt };
                    setMessages((current) => current.map((item) => item.id === suggestionReceipt!.messageId ||
                        (streamSequence === assistantStreamSequence.current && !answerCompleted && item.id === streamId)
                        ? { ...item, suggestions: suggestionReceipt!.options } : item));
                    return;
                }
                if (event === "done" && answerCompleted) {
                    streamCompleted = true;
                    if (suggestionReceipt)
                        reportFirstChunk("", headers(), suggestionReceipt.messageId, undefined, suggestionReceipt.milliseconds);
                    return;
                }
                if (streamSequence !== assistantStreamSequence.current) return;
                if (event === "answer_done") {
                    answerCompleted = true;
                    streamCompleted = true;
                    payload.suggestions = suggestionReceipt?.options || [];
                    setMessages((current) => current.some((item) => item.id === streamId)
                        ? current.map((item) => item.id === streamId ? payload : item)
                        : [...current, payload]);
                    reportFirstChunk("", headers(), payload.id, firstChunkMs);
                    setBusy(false);
                    void loadChats().catch(() => {});
                    return;
                }
                if (event === "delta" && payload.text) {
                    firstChunkMs ??= performance.now() - sentAt;
                    streamed = true;
                    setMessages((current) => {
                        const found = current.some((item) => item.id === streamId);
                        if (!found)
                            return [
                                ...current,
                                { id: streamId, role: "assistant", text: payload.text!, suggestions: suggestionReceipt?.options },
                            ];
                        return current.map((item) => item.id === streamId
                            ? { ...item, text: item.text + payload.text }
                            : item);
                    });
                }
                if ((event === "done" || event === "partial") && payload.id)
                    reportFirstChunk("", headers(), payload.id, firstChunkMs, event === "done" && payload.suggestions?.length ? performance.now() - sentAt : undefined);
                if (event === "done") {
                    streamCompleted = true;
                    setMessages((current) => current.some((item) => item.id === streamId)
                        ? current.map((item) => (item.id === streamId ? payload : item))
                        : [...current, payload]);
                }
                if (event === "partial") {
                    streamCompleted = true;
                    setMessages((current) => [
                        ...current.filter((item) => item.id !== streamId),
                        { ...payload, interrupted: true },
                    ]);
                }
                if (event === "error")
                    throw new Error(payload.message || "Assistant stream failed");
            };
            while (true) {
                const { value, done } = await reader.read();
                buffer += decoder
                    .decode(value || new Uint8Array(), { stream: !done })
                    .replace(/\r\n/g, "\n");
                let boundary: number;
                while ((boundary = buffer.indexOf("\n\n")) >= 0) {
                    const block = buffer.slice(0, boundary);
                    buffer = buffer.slice(boundary + 2);
                    handleEvent(block);
                }
                if (done)
                    break;
            }
            if (buffer.trim())
                handleEvent(buffer);
            if (!streamCompleted)
                throw new Error("Phản hồi bị gián đoạn trước khi hoàn tất.");
            void loadChats().catch(() => { });
            if (!streamed)
                setError("");
        }
        catch (reason) {
            const isCurrent = streamSequence === assistantStreamSequence.current && activeChatIdRef.current === sentChatId;
            if (isCurrent && !(reason instanceof DOMException && reason.name === "AbortError"))
                setError(String(reason));
            if (isCurrent && activeStreamId)
                setMessages((current) => current.map((item) => item.id === activeStreamId ? { ...item, interrupted: true } : item));
        }
        finally {
            assistantStreams.current.delete(controller);
            if (streamSequence === assistantStreamSequence.current) {
                assistantStreamRef.current = null;
                setBusy(false);
                void loadChats().catch(() => { });
            }
        }
    }
    async function retryPrevious(previous: ChatMessage, storedFile: UploadedFile) {
        if (!chat)
            return;
        try {
            const response = await fetch(`/v1/assistant/chats/${chat.id}/files/${storedFile.id}/content`, { headers: headers() });
            if (!response.ok)
                throw new Error("Unable to load the original attachment");
            const original = new File([await response.blob()], storedFile.filename);
            await send(previous.text, original);
        }
        catch (reason) {
            setError(String(reason));
        }
    }
    if (!ready)
        return (<div className="assistantGate">

        <RolePlayLoadingCat />

        <b>{tr("Đang tải…")}</b>

      </div>);
    if (!account)
        return (<div className={`assistantGate loginScene loginScene--${loginTheme}`} onPointerMove={(event) => {
                if (!lampOn || !loginCard.current || !loginLampButton.current)
                    return;
                const cardRect = loginCard.current.getBoundingClientRect();
                const lampRect = loginLampButton.current.getBoundingClientRect();
                const startX = lampRect.left + lampRect.width / 2 - cardRect.left;
                const startY = lampRect.top + lampRect.height / 2 - cardRect.top;
                const endX = event.clientX - cardRect.left;
                const endY = event.clientY - cardRect.top;
                const length = Math.hypot(endX - startX, endY - startY) || 1;
                const sideX = -(endY - startY) / length * 46;
                const sideY = (endX - startX) / length * 46;
                loginBeamPath.current?.setAttribute("d", `M ${startX} ${startY} L ${endX + sideX} ${endY + sideY} Q ${endX + (endX - startX) / length * 20} ${endY + (endY - startY) / length * 20} ${endX - sideX} ${endY - sideY} Z`);
                loginBeamSpot.current?.setAttribute("cx", String(endX));
                loginBeamSpot.current?.setAttribute("cy", String(endY));
                loginBeamSpot.current?.setAttribute("r", "48");
                const field = loginPasswordInput.current?.getBoundingClientRect();
                if (field && loginPasswordReveal.current) {
                    loginPasswordReveal.current.style.setProperty("--reveal-x", `${event.clientX - field.left}px`);
                    loginPasswordReveal.current.style.setProperty("--reveal-y", `${event.clientY - field.top}px`);
                }
                const shone = (element: Element) => {
                    const rect = element.getBoundingClientRect();
                    const nearestX = Math.max(rect.left, Math.min(event.clientX, rect.right));
                    const nearestY = Math.max(rect.top, Math.min(event.clientY, rect.bottom));
                    return Math.hypot(event.clientX - nearestX, event.clientY - nearestY) < 35;
                };
                if (loginOwl.current)
                    loginOwl.current.classList.toggle("owlShone", shone(loginOwl.current));
                loginCard.current.querySelectorAll(".loginSparrow").forEach((bird) => bird.classList.toggle("sparrowShone", shone(bird)));
            }} onPointerLeave={() => {
                loginBeamPath.current?.setAttribute("d", "");
                loginBeamSpot.current?.setAttribute("r", "0");
                loginOwl.current?.classList.remove("owlShone");
                loginCard.current?.querySelectorAll(".loginSparrow").forEach((bird) => bird.classList.remove("sparrowShone"));
                loginPasswordReveal.current?.style.setProperty("--reveal-x", "-100px");
            }}>

        <div className="loginSceneDecor" aria-hidden="true">{Array.from({ length: 7 }, (_, index) => <span key={index}/>)}</div>
        <div className="loginSky" aria-hidden="true"><span className="loginSkyOrb"/></div>

        <button className="btn ghost gateTheme" onClick={toggleTheme} type="button">

          <Icon n={loginTheme === "dark" ? "sun" : "moon"}/>

          {loginTheme === "dark"
                ? tr("Sáng")
                : tr("Tối")}

        </button>

        <section ref={loginCard} className={`assistantLogin loginCard${lampOn ? " loginCard--lit" : ""}`}>

          <svg className="loginLampBeam" aria-hidden="true"><path ref={loginBeamPath} className="loginBeamShape"/><circle ref={loginBeamSpot} className="loginBeamSpot" r="0"/></svg>

          {loginTheme === "dark" ? (<button ref={loginOwl} type="button" className={`loginOwl${owlAway ? " loginOwl--away" : ""}`} onClick={() => setOwlAway(true)} aria-label={tr("Chạm để cú mèo bay đi")} tabIndex={owlAway ? -1 : 0}>

              <svg viewBox="0 0 140 144" aria-hidden="true">

                <defs><linearGradient id="loginOwlBody" x2="0" y2="1"><stop stopColor="#bd8d66"/><stop offset="1" stopColor="#76523f"/></linearGradient><radialGradient id="loginOwlIris"><stop stopColor="#ffd76b"/><stop offset=".75" stopColor="#e9a93b"/><stop offset="1" stopColor="#a96527"/></radialGradient></defs>

                <g className="owlWings"><path className="owlWing owlWing--left" d="M30 73Q7 75 11 116q4 17 22 12l16-37Z"/><path className="owlWing owlWing--right" d="M110 73q23 2 19 43-4 17-22 12L91 91Z"/></g>

                <path className="owlBody" d="M27 64Q18 27 43 24L48 7l22 17L92 7l5 17q25 3 16 40 17 27 6 57-9 22-49 22s-40-2-49-22Q10 91 27 64Z"/>

                <path className="owlTuft" d="M23 44 32 9l17 23M117 44l-9-35-17 23"/>

                <path className="owlBelly" d="M41 85q29 19 58 0l5 35q-9 15-34 16-25-1-34-16Z"/>

                <g className="owlFeathers"><path d="m51 99 5 5 5-5m15 0 5 5 5-5m-45 14 5 5 5-5m15 0 5 5 5-5m15 0 5 5 5-5"/></g>

                <g className="owlHead"><path className="owlMask" d="M27 46Q37 24 69 44q33-20 44 2-4 40-44 43-39-3-42-43Z"/><path className="owlBrow" d="M27 43Q45 26 69 46q24-20 44-3"/><circle className="owlEyeRing" cx="48" cy="58" r="19"/><circle className="owlEyeRing" cx="92" cy="58" r="19"/><circle className="owlIris" cx="48" cy="59" r="13"/><circle className="owlIris" cx="92" cy="59" r="13"/><circle className="owlPupil" cx="48" cy="59" r="8"/><circle className="owlPupil" cx="92" cy="59" r="8"/><circle className="owlGlint" cx="44" cy="54" r="3.4"/><circle className="owlGlint" cx="88" cy="54" r="3.4"/><path className="owlLid" d="M34 59q14-12 28 0m16 0q14-12 28 0"/><path className="owlBeak" d="M63 73q7-7 14 0l-7 16Z"/></g>

                <path className="owlFeet" d="M49 133v8m-6-3 6 3 6-3m36-5v8m-6-3 6 3 6-3"/>

              </svg>

            </button>) : (<div className="loginSparrows" aria-hidden="true">{[0, 1, 2, 3].map((bird) => (<svg key={bird} className={`loginSparrow loginSparrow--${bird + 1}`} viewBox="0 0 100 85">

                <path className="sparrowTail" d="M30 54 4 62l-3 9 31-7 18-8Z"/><path className="sparrowBody" d="M23 48Q34 29 62 36q21 7 17 25-6 15-29 14-23-1-27-27Z"/>

                <path className="sparrowWing" d="M42 48Q25 27 30 3q24 6 33 36l-2 14Z"/><path className="sparrowWingLight" d="M47 44Q36 24 38 15q14 9 18 27"/>

                <path className="sparrowCap" d="M65 35q6-20 23-10 12 7 8 21l-10 8-20-3Z"/><path className="sparrowCheek" d="M63 46q10-7 21-1l-1 14q-15 5-22-5Z"/>

                <circle className="sparrowEyeRing" cx="79" cy="40" r="6"/><circle className="sparrowEye" cx="80" cy="40" r="3"/><circle className="sparrowGlint" cx="78" cy="38" r="1.2"/>

                <path className="sparrowBeak" d="m94 45 6 5-8 3Z"/><path className="sparrowFoot" d="m47 73-2 9m10-9 3 9"/>

              </svg>))}</div>)}

          <div className="row loginHead">

            <span className="logo">AI</span>

            <div>

              <h1>Avibi Platform</h1>

              <p className="muted">

                {tr(authMode === "login"
                ? "Đăng nhập để bắt đầu."
                : "Tạo tài khoản dùng chung với AI Role Play.")}

              </p>

            </div>

          </div>

          <label className="field">

            <span>Language</span>

            <select className="input" value={language} onChange={(event) => changeLanguage(event.target.value)}>

              {UI_LANGUAGES.map((item) => (<option key={item.code} value={item.code}>

                  {item.label}

                </option>))}

            </select>

          </label>

          {authMode === "register" && (<label className="field">

              <span>{tr("Tên hiển thị")}</span>

              <input className="input" autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)}/>

            </label>)}

          <label className="field">

            <span>{tr("Tên đăng nhập")}</span>

            <input className="input" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)}/>

          </label>

          <div className="field">

          <span>{tr("Mật khẩu")}</span>

          <div className="loginPasswordField">

            <input ref={loginPasswordInput} className="input" type="password" placeholder="••••••" autoComplete={authMode === "login" ? "current-password" : "new-password"} aria-label={tr("Mật khẩu")} value={password} onChange={(event) => setPassword(event.target.value)} onKeyDown={(event) => event.key === "Enter" && submitAuth()}/>

            <span ref={loginPasswordReveal} className="loginPasswordReveal" aria-hidden="true">{password}</span>

            <button ref={loginLampButton} className="loginLamp" type="button" onClick={() => { setLampOn((value) => !value); loginBeamPath.current?.setAttribute("d", ""); loginBeamSpot.current?.setAttribute("r", "0"); loginPasswordReveal.current?.style.setProperty("--reveal-x", "-100px"); loginOwl.current?.classList.remove("owlShone"); loginCard.current?.querySelectorAll(".loginSparrow").forEach((bird) => bird.classList.remove("sparrowShone")); }} aria-label={tr(lampOn ? "Tắt đèn và ẩn mật khẩu" : "Bật đèn để soi mật khẩu")} aria-pressed={lampOn} title={tr(lampOn ? "Tắt đèn" : "Bật đèn rồi đưa đến mật khẩu")}>

              <svg viewBox="0 0 32 32" aria-hidden="true"><path d="m6 5 7 7-3 3-7-7 3-3Zm8 8 12 12-4 4-12-12 4-4Zm12 10 3-3M5 2 2 5m12 3 3-3"/></svg>

            </button>

          </div>

          </div>

          {error && (<div className="err" role="alert">{tr(errorSource(error))}</div>)}

          <button className="btn pri loginSubmit" onClick={submitAuth}>

            {tr(authMode === "login" ? "Đăng nhập" : "Tạo tài khoản")}

          </button>

          <button className="linkbtn loginSwitch" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>

            {tr(authMode === "login"
                ? "Chưa có tài khoản? Đăng ký"
                : "Đã có tài khoản? Đăng nhập")}

          </button>

        </section>

      </div>);
    const inAssistant = !workspacePath.includes("/role-play-ai");
    const inCreate = !inAssistant && workspacePath.includes("view=create");
    const inChatBot = !inAssistant && !inCreate;
    const assistantSpaceActive = inAssistant && !/[?&](?:mode|chat|panel)=/.test(workspacePath);
    const chatBotSpaceActive = inChatBot && !/[?&](?:room)=/.test(workspacePath) &&
        !workspacePath.includes("view=chat");
    const visibleRolePlayRooms = [...rolePlayRooms]
        .sort((left, right) => (right.created_at || "").localeCompare(left.created_at || ""))
        .filter((item, index, ordered) => item.character_ids?.length !== 1 ||
            ordered.findIndex((candidate) => candidate.character_ids?.length === 1 &&
                candidate.character_ids[0] === item.character_ids![0]) === index);
    if (landingOnly)
        return (<div className={`platformWorkspace${workspaceCollapsed ? " platformWorkspaceCollapsed" : ""}`}>

        <aside className="platformWorkspaceSidebar">

          <a className="platformWorkspaceBrand" href="/" title="Avibi Platform"><span className="logo">AI</span><b>Avibi Platform</b></a>

          <section className="platformWorkspaceGroup">

            <small>{tr("Không gian")}</small>

            <button className={assistantSpaceActive ? "active" : ""} onClick={() => navigateWorkspace("/ai-assistant?workspace=1")} title={tr("Trợ lý AI")}><span className="platformWorkspaceNavIcon" aria-hidden="true"><span className="wsDot as"/></span><span className="platformWorkspaceNavLabel">{tr("Trợ lý AI")}</span></button>

            <button className={chatBotSpaceActive ? "active" : ""} onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=characters")} title={tr("Chat Bot AI")}><span className="platformWorkspaceNavIcon" aria-hidden="true"><span className="wsDot rp"/></span><span className="platformWorkspaceNavLabel">{tr("Chat Bot AI")}</span></button>

            <button className={inCreate ? "active" : ""} onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=create&createMode=custom")} title={tr("Sáng tạo nhân vật")}><span className="platformWorkspaceNavIcon" aria-hidden="true"><span className="wsDot warn"/></span><span className="platformWorkspaceNavLabel">{tr("Sáng tạo nhân vật")}</span></button>

          </section>

          <section className="platformWorkspaceGroup platformWorkspaceRecent">

            <div className="platformWorkspaceRecentHead">

              <small>{tr(inAssistant ? "Kênh AI" : "Gần đây")}</small>

              {!inAssistant && <button className="platformWorkspaceNewRoom" onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=characters&wizard=1")} title={tr("Tạo phòng chat")}><Icon n="plus-small"/>{tr("Phòng chat")}</button>}

            </div>

            {historyError && <button onClick={() => void loadChats().catch(() => setHistoryError(true))}>{tr("Không tải được lịch sử. Thử lại")}</button>}

            {(inAssistant
                ? MODES.map((item) => ({ id: item.id, kind: "channel" as const, label: tr(item.title), sub: tr(item.copy), date: "", path: `/ai-assistant?workspace=1&mode=${item.id}`, avatar: <ModeAvatar mode={item.id} size={26}/> }))
                : visibleRolePlayRooms.map((item) => {
                    const members = (item.character_ids || []).map((id) => workspaceCharacters.find((value) => value.id === id)).filter((value): value is WorkspaceCharacter => Boolean(value));
                    return { id: item.id, kind: "roleplay" as const, label: item.name, sub: members.map((value) => value.name).join(", "), date: item.created_at || "", path: `/role-play-ai?workspace=1&view=chat&room=${item.id}`, avatar: (<span className={`platformRecentAvatars${members.length > 1 ? " group" : ""}`} aria-hidden="true">

                      {members.length ? members.slice(0, 2).map((value) => value.avatar_url ? <img key={value.id} src={value.avatar_url} alt=""/> : <span key={value.id}>{value.name[0]?.toUpperCase()}</span>) : <span><Icon n="comments"/></span>}

                      {members.length > 2 && <i>+{members.length - 2}</i>}

                    </span>) };
                })).sort((left, right) => right.date.localeCompare(left.date)).map((item) => (<div className={`platformWorkspaceRecentRow${workspacePath.includes(item.id) ? " active" : ""}`} key={`${item.kind}:${item.id}`}>

                <button title={item.label} onClick={() => navigateWorkspace(item.path)}>

                  {item.avatar}

                  <span className="platformRecentText"><span>{item.label}</span>{item.sub && <small>{item.sub}</small>}</span>

                </button>

                {item.kind !== "channel" && <button className="platformWorkspaceRecentDelete" title={tr("Xóa cuộc trò chuyện")} aria-label={`${tr("Xóa cuộc trò chuyện")}: ${item.label}`} onClick={() => void removeWorkspaceConversation(item.id, item.kind, item.label)}><Icon n="cross-small"/></button>}

              </div>))}

          </section>

          {inAssistant && <button className="platformWorkspaceMemory" onClick={() => navigateWorkspace("/ai-assistant?workspace=1&panel=memory")} title={tr("Ghi nhớ & nhắc nhở")}><span className="platformWorkspaceNavIcon" aria-hidden="true"><Icon n="bookmark"/></span><span className="platformWorkspaceNavLabel">{tr("Ghi nhớ & nhắc nhở")}</span></button>}

          <section className="platformWorkspaceAccount" aria-label={tr("Tài khoản")}>

            <button className="platformWorkspaceIdentity" onClick={() => setWorkspaceAccountMenuOpen((open) => !open)} aria-expanded={workspaceAccountMenuOpen} aria-haspopup="dialog" title={tr("Cài đặt tài khoản")}>

              {account.avatar_url
                ? <img src={account.avatar_url} alt=""/>
                : <span>{account.display_name?.[0]?.toUpperCase() || "AI"}</span>}

              <span className="platformWorkspaceIdentityText"><b data-no-translate="true" translate="no">{account.display_name}</b><small>{account.username ? `@${account.username}` : tr("Tài khoản")}</small></span>

            </button>

            <button className="platformWorkspaceCollapse" onClick={() => { const next = !workspaceCollapsed; setWorkspaceCollapsed(next); localStorage.setItem("avibi_workspace_collapsed", String(next)); setWorkspaceAccountMenuOpen(false); }} aria-label={tr(workspaceCollapsed ? "Mở rộng thanh công cụ" : "Thu gọn thanh công cụ")} title={tr(workspaceCollapsed ? "Mở rộng thanh công cụ" : "Thu gọn thanh công cụ")}><Icon n={workspaceCollapsed ? "angle-small-right" : "angle-small-left"}/></button>

          </section>

        </aside>

        {workspaceCollapsed && <button className="platformWorkspaceRestore" onClick={() => { setWorkspaceCollapsed(false); localStorage.setItem("avibi_workspace_collapsed", "false"); }} aria-label={tr("Mở rộng thanh công cụ")} title={tr("Mở rộng thanh công cụ")}><Icon n="angle-small-right"/></button>}

        {workspaceAccountMenuOpen && <>

          <button className="platformWorkspaceMenuScrim" onClick={() => setWorkspaceAccountMenuOpen(false)} aria-label={tr("Đóng")} tabIndex={-1}/>

          <section className="platformWorkspaceAccountMenu" role="dialog" aria-label={tr("Cài đặt tài khoản")}>

            <div className="platformWorkspaceAccountMenuHead"><b data-no-translate="true" translate="no">{account.display_name}</b><small data-no-translate="true" translate="no">@{account.username || account.id}</small></div>

            <button onClick={() => openWorkspaceAccount("profile")}><span aria-hidden="true"><Icon n="user"/></span>{tr("Hồ sơ")}</button>

            <button onClick={() => openWorkspaceAccount("security")}><span aria-hidden="true"><Icon n="lock"/></span>{tr("Đổi mật khẩu")}</button>

            <div className="platformWorkspaceAccountMenuDivider"/>

            <button onClick={() => void toggleTheme()}><span aria-hidden="true"><Icon n={account.theme === "dark" ? "moon" : "sun"}/></span>{tr("Giao diện")}: {account.theme === "dark" ? tr("Tối") : tr("Sáng")}</button>

            <label className="platformWorkspaceAccountMenuLanguage"><span aria-hidden="true"><Icon n="globe"/></span><span>{tr("Ngôn ngữ")}</span><select value={language} onChange={(event) => void changeLanguage(event.target.value)} aria-label={tr("Ngôn ngữ")}>{UI_LANGUAGES.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>

            <div className="platformWorkspaceAccountMenuDivider"/>

            <button onClick={() => void logout()}><span aria-hidden="true"><Icon n="sign-out-alt"/></span>{tr("Đăng xuất")}</button>

          </section>

        </>}

        <section className="platformWorkspaceContent">

          {workspaceFramePaths.map((framePath, frameIndex) => framePath !== "about:blank" && (<iframe key={frameIndex} ref={(node) => { workspaceFrameRefs.current[frameIndex] = node; }} title={framePath.includes("role-play-ai") ? "Chat Bot AI" : "Trợ lý AI"} allow="autoplay" src={framePath} className={activeWorkspaceFrame === frameIndex ? "active" : "inactive"} aria-hidden={activeWorkspaceFrame !== frameIndex} onLoad={(event) => {
                    try {
                        const doc = event.currentTarget.contentDocument;
                        if (doc?.documentElement.dataset.workspaceReady === "true" && pendingWorkspaceFrame.current === frameIndex) {
                            loadedWorkspaceFrames.current.add(framePath);
                            pendingWorkspaceFrame.current = null;
                            revealWorkspaceFrame(frameIndex);
                        }
                        if (!doc || doc.getElementById("avibi-workspace-frame-style"))
                            return;
                        const style = doc.createElement("style");
                        style.id = "avibi-workspace-frame-style";
                        doc.documentElement.dataset.embeddedWorkspace = "true";
                        style.textContent = `.shell>aside,.assistantApp>aside{display:none!important}.shell{min-height:100vh}.shell>main{max-width:none;width:100%;margin:0;padding:26px 36px}.assistantApp{grid-template-columns:minmax(0,1fr)!important;width:100%;height:100vh}.assistantApp>main{min-width:0}`;
                        doc.head.appendChild(style);
                    }
                    catch { }
                }}/>))}

          {!workspaceFrameReady && <div className="platformWorkspaceLoading withCat" role={workspaceLoadError ? "alert" : "status"} aria-live="polite">
            {workspaceLoadError ? <div className="workspaceLoadFailure">
              <b data-no-translate="true" translate="no">{"Could not open workspace. Please retry."}</b>
              <button type="button" onClick={() => window.location.reload()}>{tr("Thử lại")}</button>
            </div> : <><RolePlayLoadingCat key={workspaceLoadingSession}/><b>Chờ chút nhé, mình đang chuẩn bị đây!</b></>}
          </div>}

          {reminderToast && <button className="assistantReminderToast platformReminderToast" onClick={() => setReminderToast("")}><b>{tr("\u0110\u1ebfn gi\u1edd r\u1ed3i")}</b><span>{reminderToast}</span><i>x</i></button>}

        </section>

          {workspaceAccountPanel && <div className="scrim enter" onMouseDown={(event) => { if (event.target === event.currentTarget)
                setWorkspaceAccountPanel(null); }}>

            <section className="dialog platformWorkspaceAccountDialog" role="dialog" aria-modal="true" aria-label={tr("Tài khoản")}>

              <header><h3>{tr("Tài khoản")}</h3><button className="iconbtn" onClick={() => setWorkspaceAccountPanel(null)} aria-label={tr("Đóng")}><Icon n="cross-small" size={18}/></button></header>

              <div className="tabs platformWorkspaceAccountTabs" role="tablist">

                <button role="tab" aria-selected={workspaceAccountPanel === "profile"} onClick={() => { setWorkspaceAccountPanel("profile"); setWorkspaceAccountMessage(""); setWorkspaceAccountError(""); }}>{tr("Hồ sơ")}</button>

                <button role="tab" aria-selected={workspaceAccountPanel === "security"} onClick={() => { setWorkspaceAccountPanel("security"); setWorkspaceAccountMessage(""); setWorkspaceAccountError(""); }}>{tr("Mật khẩu")}</button>

              </div>

              <div className="body">

                {workspaceAccountError && <p className="err" role="alert">{tr(errorSource(workspaceAccountError))}</p>}

                {workspaceAccountMessage && <p className="note-info" role="status">{tr(workspaceAccountMessage)}</p>}

                {workspaceAccountPanel === "profile" ? <>

                  <div className="platformWorkspaceAvatarPicker">

                    {account.avatar_url ? <img src={account.avatar_url} alt=""/> : <span>{account.display_name?.[0]?.toUpperCase() || "AI"}</span>}

                    <div className="stack" style={{ gap: 4 }}>

                      <label className={`btn sm${workspaceAccountBusy ? " disabled" : ""}`}><Icon n="upload"/>{tr("Thay ảnh đại diện")}<input className="sr" type="file" accept="image/png,image/jpeg,image/webp,image/gif" disabled={workspaceAccountBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file)
                    void uploadWorkspaceAvatar(file); event.target.value = ""; }}/></label>

                      <small className="faint">PNG, JPEG, WEBP · GIF</small>

                    </div>

                  </div>

                  <label className="field"><span>{tr("Tên đăng nhập")}</span><input className="input" value={account.username || ""} readOnly disabled/></label>

                  <label className="field"><span>{tr("Tên hiển thị")}</span><input className="input" maxLength={80} value={workspaceProfileName} onChange={(event) => setWorkspaceProfileName(event.target.value)}/></label>

                  <label className="field"><span>{tr("Giới thiệu")}</span><textarea className="input" maxLength={500} value={workspaceProfileBio} onChange={(event) => setWorkspaceProfileBio(event.target.value)}/></label>

                </> : <>

                  <label className="field"><span>{tr("Mật khẩu hiện tại")}</span><input className="input" type={workspaceShowPasswords ? "text" : "password"} value={workspaceCurrentPassword} onChange={(event) => setWorkspaceCurrentPassword(event.target.value)}/></label>

                  <label className="field"><span>{tr("Mật khẩu mới")}</span><input className="input" type={workspaceShowPasswords ? "text" : "password"} value={workspaceNewPassword} onChange={(event) => setWorkspaceNewPassword(event.target.value)}/></label>

                  <label className="check"><input type="checkbox" checked={workspaceShowPasswords} onChange={(event) => setWorkspaceShowPasswords(event.target.checked)}/>{tr("Hiện mật khẩu")}</label>

                </>}

              </div>

              <footer>

                <button className="btn" onClick={() => setWorkspaceAccountPanel(null)}>{tr("Đóng")}</button>

                {workspaceAccountPanel === "profile"
                    ? <button className="btn pri" disabled={workspaceAccountBusy || !workspaceProfileName.trim()} onClick={() => void saveWorkspaceProfile()}>{tr("Lưu hồ sơ")}</button>
                    : <button className="btn pri" disabled={workspaceAccountBusy || !workspaceCurrentPassword || workspaceNewPassword.length < 6} onClick={() => void saveWorkspacePassword()}>{tr("Đổi mật khẩu")}</button>}

              </footer>

            </section>

          </div>}

      </div>);
    const selectedMode = MODES.find((item) => item.id === mode)!;
    const activeReminders = reminders.filter((item) => item.status === "active").sort((left, right) => left.due_at.localeCompare(right.due_at));
    const composer = (home: boolean) => (<footer className={`assistantComposer asComposer${home ? " home" : ""}`}>

      {file && (<div className="assistantFile"><Icon n="clip"/> {file.name}<button className="iconbtn" onClick={() => setFile(null)} aria-label={tr("Hủy")}><Icon n="cross-small"/></button></div>)}

      <AutoGrowTextarea value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send();
            }
        }} placeholder={mode === "assistant_tarot" ? tr("Gửi Bát Tự, lá số minh họa hoặc đặt câu hỏi để chiêm nghiệm…") : home ? tr("Hỏi mình bất cứ điều gì…") : `${tr("Nhắn cho")} ${tr(selectedMode.title)}…`}/>

      <div className="asComposerBar">

        <input ref={fileInput} type="file" accept=".txt,.md,.pdf,.docx,.pptx,.csv,.xlsx,.jpg,.jpeg,.png,.webp,.gif" onChange={(event) => setFile(event.target.files?.[0] || null)}/>

        <button className="btn sm asGhost" onClick={() => fileInput.current?.click()}><Icon n="clip"/>{tr("Đính kèm")}</button>

        <EmojiPicker onSelect={(emoji) => setText((current) => current + emoji)} disabled={busy}/>

        {roomFiles.length > 0 && (<details className="asKnowledge">

            <summary className="btn sm asGhost"><Icon n="book-alt"/>{tr("Tài liệu của phòng")} ({roomFiles.length})</summary>

            <div className="asKnowledgeMenu">

              {roomFiles.map((item) => (<span key={item.id}>{item.filename}<button className="iconbtn" title={tr("Xóa nguồn")} onClick={() => removeRoomFile(item)}><Icon n="cross-small"/></button></span>))}

              <small>{tr("Trợ lý dùng các tài liệu này để trả lời trong phòng.")}</small>

            </div>

          </details>)}

        {home && availableModels.length > 0 && (<select className="asInlineModel" value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} aria-label={tr("Model")}>

            <option value="">{tr("Model của trợ lý")}</option>
              {availableModels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}

          </select>)}

        <span className="asHint">{tr("Enter để gửi · Shift+Enter xuống dòng")}</span>

        <button className="assistantSend asSend" onClick={() => send()} disabled={busy || (!text.trim() && !file)} aria-label={tr("Gửi")}><Icon n="arrow-small-up"/></button>

      </div>

      {error && <div className="assistantError">{tr(errorSource(error))}</div>}

    </footer>);
    return (<div className="assistantApp">

      <aside className={sidebarOpen ? "open" : ""}>

        <a className="assistantSideHead" href="/">

          <div className="assistantLogo">AI</div>

          <b>Avibi Platform</b>

        </a>

        <nav className="platformPrimaryNav assistantPlatformNav">

          <a className="platformSectionLink active" href="/ai-assistant">✦　Trợ lý</a>

          <a className="platformSectionLink" href="/role-play-ai">◉　Nhân vật</a>

        </nav>

        <button className="assistantHomeButton" onClick={() => newChat()}>

          ⌂ {tr("Trang chủ")}

        </button>

        <button className="newAssistantChat" onClick={() => void openTaskRoom("assistant_general")}>

          ＋ {tr("Trò chuyện với Trợ lý AI")}

        </button>

        <button className="assistantMemoryButton" onClick={() => { setMemoryPanelOpen(true); setSidebarOpen(false); }}>

          ◷ {tr("Ghi nhớ & nhắc nhở")}

        </button>

        <nav className="assistantShortcuts">

          <strong>{tr("Tác vụ")}</strong>

          {MODES.filter((item) => item.id !== "assistant_general").map((item) => (<button className={mode === item.id && Boolean(chat) ? "active" : ""} onClick={() => openTaskRoom(item.id)} key={item.id}>

                <i>{item.icon}</i>

                <span>

                  <b>{tr(item.title)}</b>

                  <small>{tr(item.copy)}</small>

                </span>

              </button>))}

        </nav>

        <div className="assistantSideBottom">

          <a href="/role-play-ai">AI Role Play →</a>

          <button onClick={logout}>{tr("Đăng xuất")}</button>

        </div>

      </aside>

      <main>

        {reminderToast && <button className="assistantReminderToast" onClick={() => setReminderToast("")}><b>{tr("Đến giờ rồi")}</b><span>{reminderToast}</span><i>×</i></button>}

        {!window.location.search.includes("workspace=1") && <header>

          <button className="assistantMobileMenu" onClick={() => setSidebarOpen((value) => !value)}>

            ☰

          </button>

          <span className="assistantHeaderSpacer"/>

          <div>

            <select value={language} onChange={(event) => changeLanguage(event.target.value)}>

              {UI_LANGUAGES.map((item) => (<option key={item.code} value={item.code}>

                  {item.label}

                </option>))}

            </select>

            <button onClick={toggleTheme}>

              {account.theme === "dark" ? `☀ ${tr("Sáng")}` : `☾ ${tr("Tối")}`}

            </button>

          </div>

        </header>}

        {memoryPanelOpen && <div className="assistantMemoryBackdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget)
            setMemoryPanelOpen(false); }}>

          <section className="assistantMemoryPanel" role="dialog" aria-modal="true" aria-label={tr("Ghi nhớ & nhắc nhở")}>

            <header><div><h2>{tr("Ghi nhớ & nhắc nhở")}</h2></div><button className="iconbtn" onClick={() => setMemoryPanelOpen(false)} aria-label={tr("Đóng")}><Icon n="cross-small"/></button></header>

            <div className="tabs asPanelTabs" role="tablist">

              <button role="tab" className={memoryPanelTab === "memory" ? "active" : ""} aria-selected={memoryPanelTab === "memory"} onClick={() => setMemoryPanelTab("memory")}>{tr("Ghi nhớ")}{savedMemories.length ? ` (${savedMemories.length})` : ""}</button>

              <button role="tab" className={memoryPanelTab === "reminders" ? "active" : ""} aria-selected={memoryPanelTab === "reminders"} onClick={() => setMemoryPanelTab("reminders")}>{tr("Nhắc nhở")}{activeReminders.length ? ` (${activeReminders.length})` : ""}</button>

            </div>

            {error && <div className="assistantError assistantMemoryError">{tr(errorSource(error))}</div>}

            <div className="assistantMemoryBody">

              {memoryPanelTab === "memory" ? <section className="assistantMemorySection">

                <label className="assistantMemoryConsent asSwitchRow"><span>{tr("Cho phép AI Assistant ghi nhớ điều bạn chủ động lưu")}</span><input type="checkbox" checked={memoryEnabled} onChange={(event) => void toggleMemory(event.target.checked).catch((reason) => setError(String(reason)))}/></label>

                {memoryEnabled && (!chat ? <p className="note-info"><Icon n="info"/><span>{tr("Ghi nhớ gắn với từng cuộc trò chuyện. Mở một cuộc trò chuyện để xem và thêm ghi nhớ.")}</span></p> : <>

                  <div className="assistantMemoryCreate"><textarea value={memoryDraft} onChange={(event) => setMemoryDraft(event.target.value)} maxLength={500} placeholder={tr("Thêm điều cần ghi nhớ")}/><div><small>{memoryDraft.length}/500</small><button className="btn primary sm" disabled={!memoryDraft.trim()} onClick={() => void saveMemory().catch((reason) => setError(String(reason)))}>{tr("Lưu trí nhớ")}</button></div></div>

                  {savedMemories.length ? savedMemories.map((item) => <article className="assistantMemoryItem" key={item.id}><span>{editingMemoryId === item.id ? <textarea value={editingMemoryDraft} maxLength={500} onChange={(event) => setEditingMemoryDraft(event.target.value)}/> : <p>{item.content}</p>}</span><div>{editingMemoryId === item.id ? <><button onClick={() => void updateMemory(item).catch((reason) => setError(String(reason)))}>{tr("Lưu")}</button><button onClick={() => setEditingMemoryId("")}>{tr("Hủy")}</button></> : <button onClick={() => { setEditingMemoryId(item.id); setEditingMemoryDraft(item.content); }}>{tr("Sửa")}</button>}<button onClick={() => void removeMemory(item).catch((reason) => setError(String(reason)))}>{tr("Xóa")}</button></div></article>) : <p className="assistantMemoryEmpty">{tr("Chưa có điều gì được lưu.")}</p>}

                </>)}

                {memoryEnabled && <button className="assistantMemoryDisable" onClick={() => void toggleMemory(false).catch((reason) => setError(String(reason)))}>{tr("Tắt và xóa mọi trí nhớ")}</button>}

              </section> : <section className="assistantMemorySection">

                <label className="assistantMemoryConsent asSwitchRow"><span>{tr("Thông báo trên client")}</span><input type="checkbox" checked={notificationsEnabled} onChange={(event) => void toggleClientNotifications(event.target.checked)}/></label><p className="assistantMemoryHint">{tr("Để ứng dụng mở để nhận nhắc. Có thể cấp quyền trình duyệt để hiện thông báo khi chuyển tab.")}</p>

                <div className="assistantReminderCreate"><input value={reminderDraft} onChange={(event) => setReminderDraft(event.target.value)} maxLength={200} placeholder={tr("Nhắc mình về…")}/><label>{tr("Ngày và giờ")}<input type="datetime-local" value={reminderTime} min={localDateTimeValue()} onChange={(event) => setReminderTime(event.target.value)}/></label><button className="btn primary sm" disabled={!reminderDraft.trim() || !reminderTime} onClick={() => void createReminder().catch((reason) => setError(String(reason)))}>{tr("Tạo nhắc nhở")}</button></div>

                {reminders.length ? reminders.map((item) => <article className="assistantMemoryItem" key={item.id}><span><b>{item.title}</b><p>{new Date(item.due_at).toLocaleString(language === "vi" ? "vi-VN" : language)}</p><small>{item.status === "done" ? tr("Hoàn tất") : item.status === "paused" ? tr("Tạm dừng") : item.last_notified_at ? tr("Đến giờ rồi") : ""}</small></span><div>{item.status !== "done" && <><button onClick={() => void updateReminder(item, { status: item.status === "active" ? "paused" : "active" }).catch((reason) => setError(String(reason)))}>{tr(item.status === "active" ? "Tạm dừng" : "Bật lại")}</button><button onClick={() => void updateReminder(item, { status: "done" }).catch((reason) => setError(String(reason)))}>{tr("Hoàn tất")}</button></>}<button onClick={() => void removeReminder(item).catch((reason) => setError(String(reason)))}>{tr("Xóa")}</button></div></article>) : <p className="assistantMemoryEmpty">{tr("Chưa có nhắc nhở.")}</p>}

              </section>}

            </div>

          </section>

        </div>}

        {chat && (<header className="asRoomHead">

            <button className="iconbtn" onClick={() => newChat("assistant_general")} title={tr("Về trang chủ Trợ lý AI")} aria-label={tr("Về trang chủ Trợ lý AI")}><Icon n="angle-small-left"/></button>

            <ModeAvatar mode={mode} size={36}/>

            <div className="asRoomTitle">

              <div><b>{tr(selectedMode.title)}</b></div>

              <small>{mode !== "assistant_general" ? tr(selectedMode.slogan) : tr("Trợ lý chung · hỏi bất cứ điều gì")}</small>

            </div>

            {availableModels.length > 0 && (<label className="asModelPick">

                <span>{tr("Model")}</span>

                <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>

                  <option value="">{tr("Model của trợ lý")}</option>
              {availableModels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}

                </select>

              </label>)}

            <button className={`btn sm${memoryPanelOpen ? " primary" : ""}`} onClick={() => { setMemoryPanelTab("memory"); setMemoryPanelOpen(true); }}><Icon n="bookmark"/>{tr("Ghi nhớ")}{savedMemories.length ? ` (${savedMemories.length})` : ""}</button>

          </header>)}

        {chat && mode === "assistant_tarot" && (<p className="tarotNotice asTarotBar"><Icon n="info"/>{tr("Nội dung chỉ để tham khảo và chiêm nghiệm. Không có lá số hay quẻ bài nào thay đổi được vận mệnh của bạn ngoài lựa chọn và sự cố gắng của chính bạn.")}</p>)}

        <section ref={conversationRef} className={`assistantConversation asConversation ${messages.length ? "hasMessages" : ""} ${chat ? "inRoom" : "isHome"}`}>

          {!chat ? (<div className="asHome">

              <section className="asHero">

                <div className="asHeroTitle"><ModeAvatar mode="assistant_general" size={52}/><div><span className="eyebrow">{tr("Trợ lý AI")}</span><h1>{tr("Chào")} {account.display_name.split(" ").pop()}, {tr("hôm nay mình giúp gì?")}</h1></div></div>

                {composer(true)}

                <div className="asStarters">{STARTERS.assistant_general.map((item) => <button key={item} disabled={busy} onClick={() => void send(tr(item))}>{tr(item)}</button>)}</div>

              </section>

              <section className="asSection">

                <div className="asSectionHead"><h2>{tr("Trợ lý cá nhân")}</h2><p>{tr("Bấm Chat để tiếp tục cuộc trò chuyện của từng tác vụ.")}</p></div>

                <div className="asSpecGrid">

                  {MODES.filter((item) => item.id !== "assistant_general").map((item) => {
                const count = visibleChatCount(item.id);
                return (<article className="asSpec" key={item.id}>

                        <div className="asSpecArt"><ModeIllustration mode={item.id}/><span className="asSpecAvatar"><ModeAvatar mode={item.id} size={44}/></span></div>

                        <div className="asSpecBody">

                          <b>{tr(item.title)}</b>

                          <p>{tr(item.copy)}</p>

                          <div className="asSpecFoot">

                            <span className="asSpecCount"><Icon n="comment-alt"/>{count} {tr("cuộc trò chuyện")}</span>

                            <button className="btn primary sm" onClick={() => void openTaskRoom(item.id)}><Icon n="comment-alt"/>{tr("Chat")}</button>

                          </div>

                        </div>

                      </article>);
            })}

                </div>

              </section>

              <div className="asTwoCol">

                <section className="asPanel">

                  <header><h3>{tr("Tiếp tục trò chuyện")}</h3><small>{MODES.reduce((total, item) => total + visibleChatCount(item.id), 0)} {tr("cuộc trò chuyện")}</small></header>

                  <div className="asList">

                    {MODES.filter((item) => chats.some((room) => room.mode === item.id)).map((item) => (<button className="asListItem" key={item.id} onClick={() => void openTaskRoom(item.id)}>
                        <ModeAvatar mode={item.id} size={34}/>
                        <span><b>{tr(item.title)}</b><small>{visibleChatCount(item.id)} {tr("cuộc trò chuyện")}</small></span>
                        <Icon n="angle-small-right"/>
                      </button>))}
                    {!chats.length && <p className="empty">{tr("Bạn chưa có cuộc trò chuyện nào.")}</p>}

                  </div>

                </section>

                <section className="asPanel">

                  <header><h3>{tr("Nhắc nhở sắp tới")}</h3><button className="btn ghost sm" onClick={() => { setMemoryPanelTab("reminders"); setMemoryPanelOpen(true); }}>{tr("Quản lý")}<Icon n="angle-small-right"/></button></header>

                  <div className="asList">

                    {activeReminders.length ? activeReminders.slice(0, 3).map((item) => (<div className="asListItem static" key={item.id}>

                        <span className="asReminderDot"><Icon n="bell"/></span>

                        <span><b>{item.title}</b><small>{new Date(item.due_at).toLocaleString(language === "vi" ? "vi-VN" : language, { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}</small></span>

                      </div>)) : <p className="empty">{tr("Không có nhắc nhở nào sắp tới.")}</p>}

                  </div>

                </section>

              </div>

            </div>) : (<div className="assistantMessages">

              {!messages.length && (<div className="asIntro">

                  <ModeAvatar mode={mode} size={72}/>

                  <h2>{mode !== "assistant_general" ? tr(selectedMode.title) : tr("Cuộc trò chuyện mới")}</h2>

                  <p>{mode !== "assistant_general" ? tr(selectedMode.greeting) : tr("Hỏi đáp, tóm tắt tài liệu, lên kế hoạch hoặc viết nội dung. Bạn có thể gửi kèm file.")}</p>

                  <div className="asStarters">{STARTERS[mode].map((item) => <button key={item} disabled={busy} onClick={() => void send(tr(item))}>{tr(item)}</button>)}</div>

                </div>)}

              {messages.map((item, index) => (<article className={`${item.role} asMsg`} key={item.id}>

                  {item.role === "assistant" && <span className="asMsgAvatar"><ModeAvatar mode={mode} size={30}/></span>}

                  <div className="asMsgBody">

                    <b>{item.role === "user" ? tr("Bạn") : tr(selectedMode.title)}</b>

                    {item.role === "assistant"
                      ? <AssistantMarkdown text={item.text} />
                      : <p data-no-translate="true" translate="no">{item.text}</p>}

                    {item.interrupted && (<div className="assistantInterrupted">

                        <span>{tr("Câu trả lời bị gián đoạn")}</span>

                        <button disabled={busy} onClick={() => {
                        const previous = messages.slice(0, index).reverse().find((message) => message.role === "user");
                        if (previous) {
                            const attachment = previous.sources?.[0];
                            const storedFile = attachment?.document_id ? roomFiles.find((file) => file.id === attachment.document_id) : undefined;
                            if (storedFile)
                                void retryPrevious(previous, storedFile);
                            else
                                void send(previous.text);
                        }
                    }}>

                          {tr("Thử lại")}

                        </button>

                      </div>)}

                    {Boolean(item.sources?.length) && (<div className="assistantSources">

                        {item.sources!.map((source) => (<span key={`${item.id}-${source.index}`}>[{source.index}] {source.filename}{source.location ? ` · ${source.location}` : ""}</span>))}

                      </div>)}

                    <div className="asMsgTools">

                      {item.role === "user"
                    ? <button className="btn sm asGhost" onClick={() => { setMemoryDraft(item.text.slice(0, 500)); setMemoryPanelTab("memory"); setMemoryPanelOpen(true); }}><Icon n="bookmark"/>{tr("Lưu vào trí nhớ")}</button>
                    : item.text && <button className="btn sm asGhost" onClick={() => { void navigator.clipboard?.writeText(item.text).then(() => { setCopiedId(item.id); window.setTimeout(() => setCopiedId(""), 1500); }).catch(() => { }); }}><Icon n={copiedId === item.id ? "check" : "copy-alt"}/>{tr(copiedId === item.id ? "Đã sao chép" : "Sao chép")}</button>}

                    </div>

                    {item.role === "assistant" && index === messages.length - 1 && Boolean(item.suggestions?.length) && (<div className="assistantSuggestions">

                        {item.suggestions!.map((suggestion, index) => (<button key={index} disabled={busy} onClick={() => send(suggestion)} data-no-translate="true" translate="no">{suggestion}</button>))}

                      </div>)}

                  </div>

                </article>))}

              {busy && !messages.some((item) => item.id.startsWith("stream-")) && (<article className="assistant asMsg">

                  <span className="asMsgAvatar"><ModeAvatar mode={mode} size={30}/></span>

                  <div className="asMsgBody"><b>{tr(selectedMode.title)}</b><p className="asThinking"><span className="asDots"><i /><i /><i /></span>{tr("Đang suy nghĩ…")}</p></div>

                </article>)}

            </div>)}

        </section>

        {chat && mode === "assistant_general" && <div className="assistantSessionNew"><button className="btn sm" disabled={busy} onClick={() => void createTaskSession()}><Icon n="plus-small"/>{tr("Hỏi chủ đề mới")}</button></div>}
        {chat && <div className="asFoot">{composer(false)}</div>}
        {(chat || mode !== "assistant_general") && <aside className={`assistantSessionHistory${sessionHistoryOpen ? " open" : ""}`} aria-label={tr("Lịch sử trò chuyện")}>
          <header><b><Icon n="time-past"/>{tr("Lịch sử trò chuyện")}</b><button className="iconbtn" onClick={() => setSessionHistoryOpen((value) => !value)} aria-label={tr("Đóng lịch sử")}><Icon n="cross-small"/></button></header>
          <div className="assistantSessionHistoryList">
            {chats.filter((item) => item.mode === mode).slice(0, mode === "assistant_general" ? undefined : 1).map((item) => <div className={`assistantSessionRow${chat?.id === item.id ? " active" : ""}`} key={item.id}>
              <button onClick={() => { if (window.matchMedia("(max-width: 1050px)").matches) setSessionHistoryOpen(false); void openChat(item); }} title={item.title}>{item.title}</button>
              <button className="assistantSessionDelete" onClick={() => void removeChat(item)} title={tr("Xóa cuộc trò chuyện")} aria-label={tr("Xóa cuộc trò chuyện")}><Icon n="cross-small"/></button>
            </div>)}
          </div>
        </aside>}
        {(chat || mode !== "assistant_general") && <button className="assistantSessionToggle" onClick={() => setSessionHistoryOpen(true)} aria-expanded={sessionHistoryOpen} aria-label={tr("Lịch sử trò chuyện")}><Icon n="time-past"/></button>}

      </main>

    </div>);
}
