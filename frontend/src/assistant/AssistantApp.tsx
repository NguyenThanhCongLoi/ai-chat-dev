import { useEffect, useRef, useState } from "react";
import {
  rememberLanguage,
  storedLanguage,
  UI_LANGUAGES,
  type UiLanguage,
} from "../i18n";
import "./assistant.css";

type Account = {
  id: string;
  username?: string;
  display_name: string;
  bio?: string;
  avatar_url?: string | null;
  theme: "light" | "dark";
  language: UiLanguage;
};
type Chat = { id: string; mode: Mode; title: string; created_at: string };
type WorkspaceRoom = { id: string; name: string; created_at?: string };
type ChatSource = {
  index: number;
  document_id: string;
  filename: string;
  location?: string;
  score?: number;
};
type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources?: ChatSource[];
  suggestions?: string[];
  interrupted?: boolean;
};
type UploadedFile = { id: string; filename: string; status: string };
type AssistantModel = { id: string; name: string; role: string };
type SavedMemory = { id: string; room_id: string; mode: Mode; content: string; created_at: string };
type AssistantReminder = { id: string; title: string; due_at: string; status: "active" | "paused" | "done"; last_notified_at?: string | null };
type Mode =
  | "assistant_general"
  | "assistant_psychology"
  | "assistant_health"
  | "assistant_homework"
  | "assistant_tarot";
type ModeItem = {
  id: Mode;
  icon: string;
  title: string;
  copy: string;
  slogan: string;
  greeting: string;
};
const MODES: ModeItem[] = [
  {
    id: "assistant_general",
    icon: "✦",
    title: "AI Assistant",
    copy: "Hỏi mình bất cứ điều gì",
    slogan: "Một câu hỏi mở ra thêm một khả năng.",
    greeting:
      "Chào bạn! Mang câu hỏi tới đây, mình mang sự tò mò — cùng bắt đầu nhé!",
  },
  {
    id: "assistant_psychology",
    icon: "◎",
    title: "Tâm lý",
    copy: "Lắng nghe và cùng bạn gỡ rối cảm xúc",
    slogan: "Gỡ rối trong lòng, tìm lại nhịp của riêng bạn.",
    greeting:
      "Chào bạn! Cứ đặt mớ suy nghĩ rối như tai nghe trong túi xuống đây, mình cùng bạn gỡ từng nút nhé.",
  },
  {
    id: "assistant_health",
    icon: "✚",
    title: "Sức khỏe",
    copy: "Thông tin sức khỏe thận trọng, dễ hiểu",
    slogan: "Hiểu cơ thể đúng hơn, chăm mình tốt hơn.",
    greeting:
      "Xin chào! Cơ thể vừa gửi thông báo gì thế? Kể mình nghe, chúng ta cùng đọc cho đúng và bớt hoang mang nhé.",
  },
  {
    id: "assistant_homework",
    icon: "✎",
    title: "Học tập",
    copy: "Giải thích từng bước từ tài liệu của bạn",
    slogan: "Bài khó đến đâu, hiểu đúng là đi tiếp được.",
    greeting:
      "Bài khó đã xuất hiện à? Tuyệt, cho mình xem thử — ta sẽ chia nhỏ nó đến khi đáp án hết đường trốn!",
  },
  {
    id: "assistant_tarot",
    icon: "✦",
    title: "Tarot & Tử vi",
    copy: "Gửi Bát Tự, lá số hoặc trải bài minh họa để chiêm nghiệm",
    slogan: "Đọc dấu hiệu để hiểu mình, không để số phận viết thay.",
    greeting:
      "Chào người khám phá! Gửi câu hỏi, lá số hoặc trải bài sang đây; mình cùng bạn đọc những biểu tượng bằng một cái đầu tỉnh táo và trái tim vui vẻ nhé.",
  },
];
const ROOM_TITLES: Record<Mode, string> = {
  assistant_general: "AI Assistant",
  assistant_psychology: "Tư vấn tâm lý",
  assistant_health: "Tư vấn sức khỏe",
  assistant_homework: "Hỗ trợ bài tập",
  assistant_tarot: "Tarot và chiêm nghiệm",
};
const UI_TEXTS = [
  "Nhân vật",
  "Nhân vật của tôi",
  "Tạo nhân vật",
  "Tạo bản sao",
  "Sáng tạo",
  "Tài khoản",
  "Thu gọn thanh công cụ",
  "Mở rộng thanh công cụ",
  "Cài đặt tài khoản",
  "Giao diện",
  "Hồ sơ",
  "Ngôn ngữ",
  "Đóng",
  "Thay ảnh đại diện",
  "Giới thiệu",
  "Lưu hồ sơ",
  "Mật khẩu hiện tại",
  "Mật khẩu mới",
  "Hiện mật khẩu",
  "Đổi mật khẩu",
  "Đã lưu hồ sơ",
  "Đã cập nhật ảnh đại diện",
  "Đã đổi mật khẩu",
  ...Object.values(ROOM_TITLES),
  "Đã xảy ra lỗi. Vui lòng thử lại.",
  "Phiên đăng nhập không hợp lệ.",
  "Dịch vụ AI tạm thời không khả dụng.",
  "Tệp tải lên quá lớn.",
  "Đang tải…",
  "Sáng",
  "Tối",
  "Đăng xuất",
  "Chọn không gian của bạn",
  "Bạn muốn bắt đầu với gì?",
  "Một tài khoản, hai không gian AI dành cho những nhu cầu khác nhau.",
  "Mở",
  "Hỏi đáp, tâm lý, sức khỏe, bài tập và Tarot",
  "Trò chuyện và nhập vai cùng các nhân vật AI",
  "Đăng nhập để bắt đầu.",
  "Tạo tài khoản dùng chung với AI Role Play.",
  "Tên hiển thị",
  "Tên đăng nhập",
  "Mật khẩu",
  "Đăng nhập",
  "Tạo tài khoản",
  "Chưa có tài khoản? Đăng ký",
  "Đã có tài khoản? Đăng nhập",
  "Trang chủ",
  "Cuộc trò chuyện mới",
  "Tác vụ",
  "Phòng chat chuyên biệt",
  "Mở phòng chat",
  "Bắt đầu cuộc trò chuyện",
  "Bạn có thể gửi câu hỏi hoặc đính kèm tệp để bắt đầu.",
  "Gần đây",
  "Xóa cuộc trò chuyện",
  "Bạn chưa có cuộc trò chuyện nào.",
  "Hỏi mình bất cứ điều gì…",
  "Gửi Bát Tự, lá số minh họa hoặc đặt câu hỏi để chiêm nghiệm…",
  "Gửi file",
  "Model",
  "Xóa nguồn",
  "Ghi nhớ & nhắc nhở",
  "Trí nhớ của bạn",
  "Cho phép AI Assistant ghi nhớ điều bạn chủ động lưu",
  "Tắt và xóa mọi trí nhớ",
  "Chưa có điều gì được lưu.",
  "Thêm điều cần ghi nhớ",
  "Chỉ dùng trong tác vụ",
  "Lưu trí nhớ",
  "Nhắc nhở",
  "Nhắc mình về…",
  "Ngày và giờ",
  "Tạo nhắc nhở",
  "Chưa có nhắc nhở.",
  "Tạm dừng",
  "Bật lại",
  "Hoàn tất",
  "Xóa",
  "Đến giờ rồi",
  "Nhắc nhở chỉ hiện khi bạn đang mở ứng dụng.",
  "Lưu",
  "Lưu vào trí nhớ",
  "Sửa",
  "Hủy",
  "Thông báo trên client",
  "Để ứng dụng mở để nhận nhắc. Có thể cấp quyền trình duyệt để hiện thông báo khi chuyển tab.",
  "Bạn",
  "Đang suy nghĩ…",
  "Câu trả lời bị gián đoạn",
  "Thử lại",
  "Nội dung chỉ để tham khảo và chiêm nghiệm. Không có lá số hay quẻ bài nào thay đổi được vận mệnh của bạn ngoài lựa chọn và sự cố gắng của chính bạn.",
  ...MODES.flatMap((item) => [
    item.title,
    item.copy,
    item.slogan,
    item.greeting,
  ]),
];
const EN: Record<string, string> = {
  "Tài khoản": "Account",
  "Thu gọn thanh công cụ": "Collapse sidebar",
  "Mở rộng thanh công cụ": "Expand sidebar",
  "Cài đặt tài khoản": "Account settings",
  "Giao diện": "Appearance",
  "Hồ sơ": "Profile",
  "Ngôn ngữ": "Language",
  "Đóng": "Close",
  "Thay ảnh đại diện": "Change avatar",
  "Giới thiệu": "Bio",
  "Lưu hồ sơ": "Save profile",
  "Mật khẩu hiện tại": "Current password",
  "Mật khẩu mới": "New password",
  "Hiện mật khẩu": "Show passwords",
  "Đổi mật khẩu": "Change password",
  "Đã lưu hồ sơ": "Profile saved",
  "Đã cập nhật ảnh đại diện": "Avatar updated",
  "Đã đổi mật khẩu": "Password changed",
  "\u004b\u0068\u00f4\u006e\u0067 \u0067\u0069\u0061\u006e": "Workspace",
  "\u0054\u00e1\u0063 \u0076\u1ee5 \u0074\u0072\u1ee3 \u006c\u00fd": "Assistant tasks",
  "\u004e\u0068\u00e2\u006e \u0076\u1ead\u0074": "Characters",
  "\u004e\u0068\u00e2\u006e \u0076\u1ead\u0074 \u0063\u1ee7\u0061 \u0074\u00f4\u0069": "My characters",
  "\u0043\u1ed9\u006e\u0067 \u0111\u1ed3\u006e\u0067": "Community",
  "\u0054\u1ea1\u006f \u006e\u0068\u00e2\u006e \u0076\u1ead\u0074": "Create character",
  "\u0054\u1ea1\u006f \u0062\u1ea3\u006e \u0073\u0061\u006f": "Create a copy",
  "\u0053\u00e1\u006e\u0067 \u0074\u1ea1\u006f": "Create freely",
  "Tư vấn tâm lý": "Wellbeing support",
  "Tư vấn sức khỏe": "Health guidance",
  "Hỗ trợ học tập": "Homework support",
  "Tarot và chiêm nghiệm": "Tarot and reflection",
  "Chào bạn! Mang câu hỏi tới đây, mình mang sự tò mò — cùng bắt đầu nhé!":
    "Hello! Bring the question, I'll bring the curiosity — let's begin!",
  "Chào bạn! Cứ đặt mớ suy nghĩ rối như tai nghe trong túi xuống đây, mình cùng bạn gỡ từng nút nhé.":
    "Hello! Drop those tangled thoughts here like earphones in a pocket, and we'll untie them one knot at a time.",
  "Xin chào! Cơ thể vừa gửi thông báo gì thế? Kể mình nghe, chúng ta cùng đọc cho đúng và bớt hoang mang nhé.":
    "Hello! What notification did your body just send? Tell me, and we'll read it carefully without the panic.",
  "Bài khó đã xuất hiện à? Tuyệt, cho mình xem thử — ta sẽ chia nhỏ nó đến khi đáp án hết đường trốn!":
    "A tough problem has appeared? Great, show me — we'll break it down until the answer has nowhere left to hide!",
  "Chào người khám phá! Gửi câu hỏi, lá số hoặc trải bài sang đây; mình cùng bạn đọc những biểu tượng bằng một cái đầu tỉnh táo và trái tim vui vẻ nhé.":
    "Hello, explorer! Send your question, chart, or spread; we'll read the symbols with a clear head and a cheerful heart.",
  "Một câu hỏi mở ra thêm một khả năng.":
    "One question can open a new possibility.",
  "Gỡ rối trong lòng, tìm lại nhịp của riêng bạn.":
    "Untangle your thoughts and find your own rhythm again.",
  "Hiểu cơ thể đúng hơn, chăm mình tốt hơn.":
    "Understand your body better, care for yourself better.",
  "Bài khó đến đâu, hiểu đúng là đi tiếp được.":
    "No problem is too hard once the path becomes clear.",
  "Đọc dấu hiệu để hiểu mình, không để số phận viết thay.":
    "Read the signs to understand yourself, never to let fate write your story.",
  "Đã xảy ra lỗi. Vui lòng thử lại.": "Something went wrong. Please try again.",
  "Phiên đăng nhập không hợp lệ.": "Your sign-in session is invalid.",
  "Dịch vụ AI tạm thời không khả dụng.":
    "The AI service is temporarily unavailable.",
  "Tệp tải lên quá lớn.": "The uploaded file is too large.",
  "Đang tải…": "Loading…",
  Sáng: "Light",
  Tối: "Dark",
  "Đăng xuất": "Sign out",
  "Chọn không gian của bạn": "Choose your space",
  "Bạn muốn bắt đầu với gì?": "What would you like to start with?",
  "Một tài khoản, hai không gian AI dành cho những nhu cầu khác nhau.":
    "One account, two AI spaces for different needs.",
  Mở: "Open",
  "Hỏi đáp, tâm lý, sức khỏe, bài tập và Tarot":
    "Questions, wellbeing, health, homework and Tarot",
  "Trò chuyện và nhập vai cùng các nhân vật AI":
    "Chat and role-play with AI characters",
  "Đăng nhập để bắt đầu.": "Sign in to get started.",
  "Tạo tài khoản dùng chung với AI Role Play.":
    "Create one account for both products.",
  "Tên hiển thị": "Display name",
  "Tên đăng nhập": "Username",
  "Mật khẩu": "Password",
  "Đăng nhập": "Sign in",
  "Tạo tài khoản": "Create account",
  "Chưa có tài khoản? Đăng ký": "No account yet? Sign up",
  "Đã có tài khoản? Đăng nhập": "Already have an account? Sign in",
  "Trang chủ": "Home",
  "Cuộc trò chuyện mới": "New chat",
  "Tác vụ": "Tools",
  "Phòng chat chuyên biệt": "Specialized chat rooms",
  "Mở phòng chat": "Open chat room",
  "Bắt đầu cuộc trò chuyện": "Start the conversation",
  "Bạn có thể gửi câu hỏi hoặc đính kèm tệp để bắt đầu.":
    "Send a question or attach a file to get started.",
  "Gần đây": "Recent",
  "Xóa cuộc trò chuyện": "Delete conversation",
  "Bạn chưa có cuộc trò chuyện nào.": "No conversations yet.",
  "Hỏi mình bất cứ điều gì…": "Ask me anything…",
  "Gửi Bát Tự, lá số minh họa hoặc đặt câu hỏi để chiêm nghiệm…":
    "Upload an illustrative chart or ask a reflective question…",
  "Gửi file": "Attach file",
  Model: "Model",
  "Xóa nguồn": "Remove source",
  "Ghi nhớ & nhắc nhở": "Memory & reminders",
  "Trí nhớ của bạn": "Your memories",
  "Cho phép AI Assistant ghi nhớ điều bạn chủ động lưu": "Allow AI Assistant to use details you explicitly save",
  "Tắt và xóa mọi trí nhớ": "Turn off and delete all memories",
  "Chưa có điều gì được lưu.": "Nothing saved yet.",
  "Thêm điều cần ghi nhớ": "Add a memory",
  "Chỉ dùng trong tác vụ": "Use only in this task",
  "Lưu trí nhớ": "Save memory",
  "Nhắc nhở": "Reminders",
  "Nhắc mình về…": "Remind me about…",
  "Ngày và giờ": "Date and time",
  "Tạo nhắc nhở": "Create reminder",
  "Chưa có nhắc nhở.": "No reminders yet.",
  "Tạm dừng": "Pause",
  "Bật lại": "Resume",
  "Hoàn tất": "Done",
  "Xóa": "Delete",
  "Đến giờ rồi": "It's time",
  "Nhắc nhở chỉ hiện khi bạn đang mở ứng dụng.": "Reminders appear while the app is open.",
  "Lưu": "Save",
  "Lưu vào trí nhớ": "Save to memory",
  "Sửa": "Edit",
  "Hủy": "Cancel",
  "Thông báo trên client": "Client notifications",
  "Để ứng dụng mở để nhận nhắc. Có thể cấp quyền trình duyệt để hiện thông báo khi chuyển tab.": "Keep the app open for reminders. Allow browser notifications to see them while using another tab.",
  Bạn: "You",
  "Đang suy nghĩ…": "Thinking…",
  "Câu trả lời bị gián đoạn": "The response was interrupted.",
  "Thử lại": "Try again",
  "Nội dung chỉ để tham khảo và chiêm nghiệm. Không có lá số hay quẻ bài nào thay đổi được vận mệnh của bạn ngoài lựa chọn và sự cố gắng của chính bạn.":
    "For reference and reflection only. No chart or card can change your destiny; your choices and effort shape your life.",
  "Tâm lý": "Wellbeing",
  "Sức khỏe": "Health",
  "Học tập": "Homework",
  "Tarot & Tử vi": "Tarot & Astrology",
  "Hỏi mình bất cứ điều gì": "Ask me anything",
  "Lắng nghe và cùng bạn gỡ rối cảm xúc": "Support for thoughts and emotions",
  "Thông tin sức khỏe thận trọng, dễ hiểu": "Careful, clear health information",
  "Giải thích từng bước từ tài liệu của bạn":
    "Step-by-step help with your materials",
  "Gửi Bát Tự, lá số hoặc trải bài minh họa để chiêm nghiệm":
    "Upload an illustrative chart or spread for reflection",
};
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
  });
  if (!response.ok) throw new Error(String(response.status));
  if (response.status === 204) return undefined as T;
  return response.json();
}
const cacheKey = (language: string) => `assistant_ui_v4:${language}`;
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

export default function AssistantApp({
  landingOnly = false,
}: {
  landingOnly?: boolean;
}) {
  const [account, setAccount] = useState<Account | null>(null),
    [ready, setReady] = useState(false),
    [authMode, setAuthMode] = useState<"login" | "register">("login"),
    [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [lampOn, setLampOn] = useState(false),
    [owlAway, setOwlAway] = useState(false),
    [loginTheme, setLoginTheme] = useState<"light" | "dark">(() =>
      localStorage.getItem("preferred_theme") === "dark" ? "dark" : "light"),
    [displayName, setDisplayName] = useState(""),
    [language, setLanguage] = useState<UiLanguage>(storedLanguage),
    [translations, setTranslations] = useState<Record<string, string>>({}),
    [languageBusy, setLanguageBusy] = useState(false),
    [error, setError] = useState("");
  const [mode, setMode] = useState<Mode>(() => {
    const requested = new URLSearchParams(window.location.search).get("mode");
    return MODES.some((item) => item.id === requested) ? requested as Mode : "assistant_general";
  }),
    [chats, setChats] = useState<Chat[]>([]),
    [chat, setChat] = useState<Chat | null>(null),
    [messages, setMessages] = useState<ChatMessage[]>([]),
    [roomFiles, setRoomFiles] = useState<UploadedFile[]>([]),
    [text, setText] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [availableModels, setAvailableModels] = useState<AssistantModel[]>([]),
    [selectedModel, setSelectedModel] = useState(""),
    [busy, setBusy] = useState(false),
    [sidebarOpen, setSidebarOpen] = useState(false);
  const [workspacePath, setWorkspacePath] = useState("/ai-assistant?workspace=1");
  const [workspaceFramePaths, setWorkspaceFramePaths] = useState([
    "/ai-assistant?workspace=1",
    "about:blank",
  ]);
  const [activeWorkspaceFrame, setActiveWorkspaceFrame] = useState(0);
  const [workspaceFrameReady, setWorkspaceFrameReady] = useState(false);
  const workspaceFrameRefs = useRef<Array<HTMLIFrameElement | null>>([]);
  const pendingWorkspaceFrame = useRef<number | null>(0);
  const loadedWorkspaceFrames = useRef(new Set<string>());
  const desiredWorkspacePath = useRef("/ai-assistant?workspace=1");
  const [rolePlayRooms, setRolePlayRooms] = useState<WorkspaceRoom[]>([]);
  const [historyError, setHistoryError] = useState(false);
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
    if (!workspaceAccountMenuOpen) return;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setWorkspaceAccountMenuOpen(false);
    };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [workspaceAccountMenuOpen]);
  const [memoryPanelOpen, setMemoryPanelOpen] = useState(() => new URLSearchParams(window.location.search).get("panel") === "memory"),
    [memoryEnabled, setMemoryEnabled] = useState(false),
    [savedMemories, setSavedMemories] = useState<SavedMemory[]>([]),
    [editingMemoryId, setEditingMemoryId] = useState(""),
    [editingMemoryDraft, setEditingMemoryDraft] = useState(""),
    [reminders, setReminders] = useState<AssistantReminder[]>([]),
    [memoryDraft, setMemoryDraft] = useState(""),
    [reminderDraft, setReminderDraft] = useState(""),
    [reminderTime, setReminderTime] = useState(""),
    [reminderToast, setReminderToast] = useState(""),
    [notificationsEnabled, setNotificationsEnabled] = useState(() => localStorage.getItem("assistant_client_notifications") !== "false");

  const fileInput = useRef<HTMLInputElement>(null);
  const loginPasswordInput = useRef<HTMLInputElement>(null);
  const loginCard = useRef<HTMLElement>(null);
  const loginLampButton = useRef<HTMLButtonElement>(null);
  const loginPasswordReveal = useRef<HTMLSpanElement>(null);
  const loginBeamPath = useRef<SVGPathElement>(null);
  const loginBeamSpot = useRef<SVGCircleElement>(null);
  const loginOwl = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!owlAway) return;
    const timer = window.setTimeout(() => setOwlAway(false), 10_000);
    return () => window.clearTimeout(timer);
  }, [owlAway]);
  const activeChatIdRef = useRef<string | null>(null);
  const workspaceInitialChatRef = useRef("");
  const assistantStreamRef = useRef<AbortController | null>(null);
  const assistantStreamSequence = useRef(0);
  const memoryLoadSequence = useRef(0);
  function navigateWorkspace(path: string) {
    setWorkspaceAccountMenuOpen(false);
    setWorkspacePath(path);
    desiredWorkspacePath.current = path;
    const appName = path.includes("/role-play-ai") ? "role-play-ai" : "ai-assistant";
    const routeToApp = (frameIndex: number) => {
      workspaceFrameRefs.current[frameIndex]?.contentWindow?.postMessage(
        { type: "avibi-workspace-navigate", path },
        window.location.origin,
      );
    };
    const currentFramePath = workspaceFramePaths[activeWorkspaceFrame];
    const currentApp = currentFramePath.includes("/role-play-ai") ? "role-play-ai" : currentFramePath.includes("/ai-assistant") ? "ai-assistant" : "";
    if (currentApp === appName && loadedWorkspaceFrames.current.has(currentFramePath)) {
      pendingWorkspaceFrame.current = null;
      routeToApp(activeWorkspaceFrame);
      return;
    }
    const cachedFrame = workspaceFramePaths.findIndex((current) =>
      (appName === "role-play-ai" ? current.includes("/role-play-ai") : current.includes("/ai-assistant")) &&
      loadedWorkspaceFrames.current.has(current),
    );
    if (cachedFrame >= 0) {
      pendingWorkspaceFrame.current = null;
      setActiveWorkspaceFrame(cachedFrame);
      setWorkspaceFrameReady(true);
      routeToApp(cachedFrame);
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
    if (!workspaceProfileName.trim()) return;
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
    } catch (reason) {
      setWorkspaceAccountError(String(reason));
    } finally {
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
      if (!response.ok) throw new Error(String(response.status));
      const updated = await request<Account>("/v1/auth/me");
      setAccount(updated);
      localStorage.setItem("avibi_account_refresh", String(Date.now()));
      setWorkspaceAccountMessage("Đã cập nhật ảnh đại diện");
    } catch (reason) {
      setWorkspaceAccountError(String(reason));
    } finally {
      setWorkspaceAccountBusy(false);
    }
  }
  async function saveWorkspacePassword() {
    if (!workspaceCurrentPassword || workspaceNewPassword.length < 6) return;
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
    } catch (reason) {
      setWorkspaceAccountError(String(reason));
    } finally {
      setWorkspaceAccountBusy(false);
    }
  }
  useEffect(() => {
    if (!landingOnly) return;
    const onFrameReady = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type === "avibi-workspace-history-updated") {
        void loadChats().catch(() => {});
        void request<WorkspaceRoom[]>("/v1/rooms").then(setRolePlayRooms).catch(() => {});
        return;
      }
      if (event.data?.type !== "avibi-workspace-ready") return;
      const frameIndex = workspaceFrameRefs.current.findIndex((frame) => frame?.contentWindow === event.source);
      if (frameIndex < 0) return;
      loadedWorkspaceFrames.current.add(workspaceFramePaths[frameIndex]);
      if (pendingWorkspaceFrame.current === frameIndex) {
        pendingWorkspaceFrame.current = null;
        setActiveWorkspaceFrame(frameIndex);
        setWorkspaceFrameReady(true);
        const targetPath = desiredWorkspacePath.current;
        if (targetPath !== workspaceFramePaths[frameIndex]) {
          window.setTimeout(() => workspaceFrameRefs.current[frameIndex]?.contentWindow?.postMessage(
            { type: "avibi-workspace-navigate", path: targetPath },
            window.location.origin,
          ), 0);
        }
      }
    };
    window.addEventListener("message", onFrameReady);
    return () => window.removeEventListener("message", onFrameReady);
  }, [landingOnly, workspaceFramePaths]);
  function cancelAssistantStream() {
    assistantStreamSequence.current += 1;
    assistantStreamRef.current?.abort();
    assistantStreamRef.current = null;
    setBusy(false);
  }
  useEffect(() => () => {
    assistantStreamSequence.current += 1;
    assistantStreamRef.current?.abort();
  }, []);

  /* vùng scroll của chat */
  const conversationRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!account) return;
    request<AssistantModel[]>(
      `/v1/assistant/models?mode=${encodeURIComponent(mode)}`,
    )
      .then((items) => {
        setAvailableModels(items);
        setSelectedModel((current) =>
          items.some((item) => item.id === current)
            ? current
            : items[0]?.id || "",
        );
      })
      .catch(() => {
        setAvailableModels([]);
        setSelectedModel("");
      });
  }, [account, mode]);
  useEffect(() => {
    if (!account || !landingOnly) return;
    request<WorkspaceRoom[]>("/v1/rooms").then(setRolePlayRooms).catch(() => setRolePlayRooms([]));
  }, [account?.id, landingOnly]);
  useEffect(() => {
    if (account && landingOnly && window.location.pathname === "/") {
      window.history.replaceState(window.history.state, "", "/avibi-platform");
    }
  }, [account?.id, landingOnly]);
  async function loadMemoryAndReminders(roomId = chat?.id) {
    const sequence=++memoryLoadSequence.current;
    const query=roomId?`?room_id=${encodeURIComponent(roomId)}`:"";
    const state = await request<{enabled:boolean; memories:SavedMemory[]; reminders:AssistantReminder[] }>(`/v1/assistant/memory${query}`);
    if(sequence!==memoryLoadSequence.current)return;
    setMemoryEnabled(state.enabled);setReminders(state.reminders);
    if(activeChatIdRef.current===(roomId||null))setSavedMemories(state.memories);
  }
  useEffect(() => {
    if (!account) return;
    void loadMemoryAndReminders(chat?.id).catch(() => {});
  }, [account?.id, chat?.id]);
  useEffect(() => {
    if (!account || !notificationsEnabled) return;
    if (window.location.search.includes("workspace=1")) return;
    const pollDue=()=>{
      void request<AssistantReminder[]>("/v1/assistant/reminders/due").then((due)=>{
        if(!due.length)return;
        setReminders((current)=>current.map((item)=>due.some((ready)=>ready.id===item.id)?{...item,last_notified_at:new Date().toISOString()}:item));
        const titles=due.map((item)=>item.title).join(" · ");setReminderToast(titles);
        if(typeof Notification!=="undefined"&&Notification.permission==="granted")new Notification(tr("Đến giờ rồi"),{body:titles,tag:"avibi-assistant-reminders"});
      }).catch(()=>{});
    };
    pollDue();
    const timer=window.setInterval(pollDue,15000);
    return ()=>window.clearInterval(timer);
  },[account?.id,notificationsEnabled,language]);
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
      if (event.key !== "preferred_theme" || (event.newValue !== "light" && event.newValue !== "dark")) return;
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
        void request<Account>("/v1/auth/me").then(setAccount).catch(() => {});
      }
    };
    window.addEventListener("storage", syncAccount);
    return () => window.removeEventListener("storage", syncAccount);
  }, []);
  const tr = (value: string) =>
    language === "vi"
      ? value
      : language === "en"
        ? EN[value] || value
        : translations[value] || EN[value] || value;
  useEffect(() => {
    const preferred =
      (localStorage.getItem("preferred_theme") as Account["theme"] | null) ||
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
        setLanguage(value.language);
        rememberLanguage(value.language);
        document.documentElement.dataset.theme = value.theme;
        localStorage.setItem("preferred_theme", value.theme);
        void loadChats().catch(() => setHistoryError(true));
      })
      .catch((reason) => {
        if (reason instanceof Error && Number(reason.message) === 401) localStorage.removeItem("auth_token");
        else setError("Không kiểm tra được phiên đăng nhập. Hãy tải lại trang để thử lại.");
      })
      .finally(() => setReady(true));
  }, []);
  useEffect(() => {
    if (landingOnly || !account || !ready || window.parent === window) return;
    window.parent.postMessage({ type: "avibi-workspace-ready" }, window.location.origin);
  }, [account?.id, ready, landingOnly]);
  useEffect(() => {
    if (landingOnly || !account || window.parent === window) return;
    window.parent.postMessage({ type: "avibi-workspace-history-updated" }, window.location.origin);
  }, [account?.id, chats, landingOnly]);
  useEffect(() => {
    let active = true;
    rememberLanguage(language);
    if (language === "vi" || language === "en") {
      setTranslations({});
      setLanguageBusy(false);
      return;
    }
    try {
      const cached = JSON.parse(
        localStorage.getItem(cacheKey(language)) || "{}",
      );
      setTranslations(cached);
      if (UI_TEXTS.every((item) => cached[item])) {
        setLanguageBusy(false);
        return;
      }
    } catch {}
    setLanguageBusy(true);
    request<{ translations: string[] }>("/v1/i18n/translate", "POST", {
      language,
      texts: UI_TEXTS,
    })
      .then((result) => {
        if (!active) return;
        const values = Object.fromEntries(
          UI_TEXTS.map((item, index) => [
            item,
            result.translations[index] || item,
          ]),
        );
        setTranslations(values);
        localStorage.setItem(
          cacheKey(language),
          JSON.stringify(
            Object.fromEntries(
              Object.entries(values).filter(
                ([source, translated]) => translated && translated !== source,
              ),
            ),
          ),
        );
      })
      .catch(() => {})
      .finally(() => active && setLanguageBusy(false));
    return () => {
      active = false;
    };
  }, [language]);
  useEffect(() => {
    const element = conversationRef.current;
    if (!element) return;

    const frame = requestAnimationFrame(() => {
      element.scrollTo({
        top: element.scrollHeight,
        behavior: "smooth",
      });
    });

    return () => cancelAnimationFrame(frame);
  }, [messages, busy, chat?.id]);

  const chatTitle = (item: Chat) => tr(ROOM_TITLES[item.mode] || item.title);
  async function loadChats() {
    setChats(await request<Chat[]>("/v1/assistant/chats"));
    setHistoryError(false);
  }
  async function openChat(item: Chat) {
    cancelAssistantStream();
    activeChatIdRef.current = item.id;
    setChat(item);
    setMode(item.mode);
    const [history, files] = await Promise.all([
      request<ChatMessage[]>(`/v1/assistant/chats/${item.id}/messages`),
      request<UploadedFile[]>(`/v1/assistant/chats/${item.id}/files`),
    ]);
    if (activeChatIdRef.current !== item.id) return;
    setMessages(history);
    setRoomFiles(files);
    setSidebarOpen(false);
    void loadMemoryAndReminders(item.id).catch(()=>{});
  }
  function newChat(nextMode: Mode = "assistant_general") {
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
    cancelAssistantStream();
    activeChatIdRef.current = null;
    const created = await request<Chat>("/v1/assistant/chats", "POST", {
      mode: nextMode,
    });
    setChats((current) => [created, ...current]);
    setChat(created);
    activeChatIdRef.current = created.id;
    setSavedMemories([]);
    setMode(nextMode);
    setMessages([]);
    setRoomFiles([]);
    setText("");
    setFile(null);
    setSidebarOpen(false);
    void loadMemoryAndReminders(created.id).catch(()=>{});
  }
  useEffect(() => {
    if (!account || !window.location.search.includes("workspace=1")) return;
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
    if (requested && requested !== "assistant_general" && !workspaceInitialChatRef.current) {
      const item = MODES.find((candidate) => candidate.id === requested);
      if (item) {
        workspaceInitialChatRef.current = `task:${requested}`;
        void openTaskRoom(item.id);
      }
    }
  }, [account, chats]);
  useEffect(() => {
    if (landingOnly || window.parent === window) return;
    const onWorkspaceNavigation = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.data?.type !== "avibi-workspace-navigate") return;
      const params = new URL(event.data.path, window.location.origin).searchParams;
      if (params.get("panel") === "memory") {
        setMemoryPanelOpen(true);
        return;
      }
      setMemoryPanelOpen(false);
      const chatId = params.get("chat");
      if (chatId) {
        const item = chats.find((candidate) => candidate.id === chatId);
        if (item) void openChat(item);
        return;
      }
      const requested = params.get("mode");
      if (requested === "assistant_general") {
        workspaceInitialChatRef.current = "";
        newChat("assistant_general");
      } else if (requested && MODES.some((item) => item.id === requested)) {
        workspaceInitialChatRef.current = requested === "assistant_general" ? "" : `task:${requested}`;
        void openTaskRoom(requested as Mode);
      } else {
        workspaceInitialChatRef.current = "";
        newChat("assistant_general");
      }
    };
    window.addEventListener("message", onWorkspaceNavigation);
    return () => window.removeEventListener("message", onWorkspaceNavigation);
  }, [landingOnly, chats]);
  async function removeRoomFile(item: UploadedFile) {
    if (!chat) return;
    await request(`/v1/assistant/chats/${chat.id}/files/${item.id}`, "DELETE");
    setRoomFiles((current) => current.filter((value) => value.id !== item.id));
  }
  async function removeChat(item: Chat) {
    await request(`/v1/assistant/chats/${item.id}`, "DELETE");
    setChats((current) => current.filter((value) => value.id !== item.id));
    if (chat?.id === item.id) newChat();
  }
  async function removeWorkspaceConversation(id: string, kind: "assistant" | "roleplay", label: string) {
    if (!window.confirm(`${tr("Xóa cuộc trò chuyện")} “${label}”?`)) return;
    try {
      await request(kind === "assistant" ? `/v1/assistant/chats/${id}` : `/v1/rooms/${id}`, "DELETE");
      if (kind === "assistant") setChats((current) => current.filter((item) => item.id !== id));
      else setRolePlayRooms((current) => current.filter((item) => item.id !== id));
      if (workspacePath.includes(id)) navigateWorkspace(kind === "assistant" ? "/ai-assistant?workspace=1" : "/role-play-ai?workspace=1&view=characters");
    } catch (reason) {
      window.alert(String(reason));
    }
  }
  async function changeLanguage(next: UiLanguage) {
    setLanguage(next);
    rememberLanguage(next);
    if (account)
      setAccount(
        await request<Account>("/v1/auth/me", "PATCH", { language: next }),
      );
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
      const value = await response.json() as Account & { token: string };
      localStorage.setItem("auth_token", value.token);
      setAccount(value);
      const theme =
        (localStorage.getItem("preferred_theme") as Account["theme"] | null) ||
        value.theme;
      const updated = await request<Account>("/v1/auth/me", "PATCH", { language, theme }).catch(() => value);
      setAccount(updated);
      document.documentElement.dataset.theme = theme;
      localStorage.setItem("preferred_theme", theme);
      await loadChats().catch(() => setHistoryError(true));
    } catch (reason) {
      setError(String(reason));
    }
  }
  async function toggleTheme() {
    const theme =
      document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("preferred_theme", theme);
    setLoginTheme(theme);
    if (account)
      setAccount(await request<Account>("/v1/auth/me", "PATCH", { theme }));
  }
  async function logout() {
    await request("/v1/auth/logout", "POST", {}).catch(() => {});
    localStorage.removeItem("auth_token");
    window.location.assign("/");
  }
  async function toggleMemory(enabled:boolean) {
    const result=await request<{enabled:boolean}>("/v1/assistant/memory","PATCH",{enabled});
    setMemoryEnabled(result.enabled);
    if(!enabled)setSavedMemories([]);
  }
  async function saveMemory() {
    const content=memoryDraft.trim();if(!content)return;
    if(!chat)throw new Error("Mở một cuộc hội thoại trước khi lưu ghi nhớ.");
    await request<SavedMemory>("/v1/assistant/memory/items","POST",{content,room_id:chat.id});
    setMemoryDraft("");await loadMemoryAndReminders(chat.id);
  }
  async function removeMemory(item:SavedMemory) {
    await request(`/v1/assistant/memory/items/${item.id}`,"DELETE");
    setSavedMemories((current)=>current.filter((value)=>value.id!==item.id));
  }
  async function updateMemory(item:SavedMemory) {
    const updated=await request<SavedMemory>(`/v1/assistant/memory/items/${item.id}`,"PATCH",{content:editingMemoryDraft});
    setSavedMemories((current)=>current.map((value)=>value.id===item.id?updated:value));setEditingMemoryId("");setEditingMemoryDraft("");
  }
  async function createReminder() {
    if(!reminderDraft.trim()||!reminderTime)return;
    await request("/v1/assistant/reminders","POST",{title:reminderDraft.trim(),due_at:new Date(reminderTime).toISOString()});
    setReminderDraft("");setReminderTime("");await loadMemoryAndReminders();
  }
  async function updateReminder(item:AssistantReminder,changes:Partial<AssistantReminder>) {
    const updated=await request<AssistantReminder>(`/v1/assistant/reminders/${item.id}`,"PATCH",changes);
    setReminders((current)=>current.map((value)=>value.id===item.id?updated:value));
  }
  async function removeReminder(item:AssistantReminder) {
    await request(`/v1/assistant/reminders/${item.id}`,"DELETE");setReminders((current)=>current.filter((value)=>value.id!==item.id));
  }
  async function toggleClientNotifications(enabled:boolean) {
    if(enabled&&typeof Notification!=="undefined"&&Notification.permission==="default")await Notification.requestPermission().catch(()=>"denied");
    localStorage.setItem("assistant_client_notifications",String(enabled));setNotificationsEnabled(enabled);
    if(!enabled)setReminderToast("");
  }
  async function send(messageOverride = "", attachmentOverride?: File | null) {
    const directMessage = messageOverride.trim();
    const pendingAttachment = attachmentOverride ?? file;
    if ((!directMessage && !text.trim() && !pendingAttachment) || busy) return;
    const streamSequence = ++assistantStreamSequence.current;
    const controller = new AbortController();
    assistantStreamRef.current = controller;
    setBusy(true);
    setError("");
    let activeStreamId = "";
    let streamCompleted = false;
    let sentChatId = chat?.id || "";
    try {
      let active = chat;
      if (!active) {
        active = await request<Chat>("/v1/assistant/chats", "POST", { mode });
        setChat(active);
        activeChatIdRef.current = active.id;
        sentChatId = active.id;
        setChats((current) => [active!, ...current]);
      }
      const attached =
        attachmentOverride !== undefined
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
          throw new Error(
            `${upload.status}: ${failure.detail || "Upload failed"}`,
          );
        }
        const uploaded = (await upload.json()) as UploadedFile;
        attachmentIds.push(uploaded.id);
        setRoomFiles((current) => [...current, uploaded]);
        setFile(null);
      }
      const message =
        directMessage ||
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
      if (!directMessage) setText("");
      const response = await fetch(
        `/v1/assistant/chats/${active.id}/messages/stream`,
        {
          method: "POST",
          headers: {
            ...headers(),
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            message,
            attachment_ids: attachmentIds,
            model_id: selectedModel,
          }),
          signal: controller.signal,
        },
      );
      if (!response.ok || !response.body)
        throw new Error(await response.text());
      const streamId = (activeStreamId = "stream-" + crypto.randomUUID());
      const reader = response.body.getReader(),
        decoder = new TextDecoder();
      let buffer = "",
        streamed = false;
      const handleEvent = (block: string) => {
        if (streamSequence !== assistantStreamSequence.current || activeChatIdRef.current !== active.id) return;
        let event = "",
          raw = "";
        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          if (line.startsWith("data:")) raw += line.slice(5).trim();
        }
        if (!raw) return;
        const payload = JSON.parse(raw) as ChatMessage & {
          message?: string;
          text?: string;
        };
        if (event === "delta" && payload.text) {
          streamed = true;
          setMessages((current) => {
            const found = current.some((item) => item.id === streamId);
            if (!found)
              return [
                ...current,
                { id: streamId, role: "assistant", text: payload.text! },
              ];
            return current.map((item) =>
              item.id === streamId
                ? { ...item, text: item.text + payload.text }
                : item,
            );
          });
        }
        if (event === "done") {
          streamCompleted = true;
          setMessages((current) =>
            current.some((item) => item.id === streamId)
              ? current.map((item) => (item.id === streamId ? payload : item))
              : [...current, payload],
          );
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
        if (done) break;
      }
      if (buffer.trim()) handleEvent(buffer);
      if (!streamCompleted)
        throw new Error("Phản hồi bị gián đoạn trước khi hoàn tất.");
      if (!streamed) setError("");
    } catch (reason) {
      const isCurrent = streamSequence === assistantStreamSequence.current && activeChatIdRef.current === sentChatId;
      if (isCurrent && !(reason instanceof DOMException && reason.name === "AbortError")) setError(String(reason));
      if (isCurrent && activeStreamId)
        setMessages((current) =>
          current.map((item) =>
            item.id === activeStreamId ? { ...item, interrupted: true } : item,
          ),
        );
    } finally {
      if (streamSequence === assistantStreamSequence.current) {
        assistantStreamRef.current = null;
        setBusy(false);
      }
    }
  }
  async function retryPrevious(
    previous: ChatMessage,
    storedFile: UploadedFile,
  ) {
    if (!chat) return;
    try {
      const response = await fetch(
        `/v1/assistant/chats/${chat.id}/files/${storedFile.id}/content`,
        { headers: headers() },
      );
      if (!response.ok)
        throw new Error("Unable to load the original attachment");
      const original = new File([await response.blob()], storedFile.filename);
      await send(previous.text, original);
    } catch (reason) {
      setError(String(reason));
    }
  }
  if (!ready || languageBusy)
    return (
      <div className="assistantGate">
        <span className="assistantSpinner" />
        <b>{tr("Đang tải…")}</b>
      </div>
    );
  if (!account)
    return (
      <div className={`assistantGate loginScene loginScene--${loginTheme}`} onPointerMove={(event) => {
        if (!lampOn || !loginCard.current || !loginLampButton.current) return;
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
        if (loginOwl.current) loginOwl.current.classList.toggle("owlShone", shone(loginOwl.current));
        loginCard.current.querySelectorAll(".loginSparrow").forEach((bird) => bird.classList.toggle("sparrowShone", shone(bird)));
      }} onPointerLeave={() => {
        loginBeamPath.current?.setAttribute("d", "");
        loginBeamSpot.current?.setAttribute("r", "0");
        loginOwl.current?.classList.remove("owlShone");
        loginCard.current?.querySelectorAll(".loginSparrow").forEach((bird) => bird.classList.remove("sparrowShone"));
        loginPasswordReveal.current?.style.setProperty("--reveal-x", "-100px");
      }}>
        <div className="loginSceneDecor" aria-hidden="true">{Array.from({ length: 7 }, (_, index) => <span key={index} />)}</div>
        <div className="loginSky" aria-hidden="true"><span className="loginSkyOrb" /></div>
        <button className="gateTheme" onClick={toggleTheme} type="button">
          ◐{" "}
          {loginTheme === "dark"
            ? tr("Sáng")
            : tr("Tối")}
        </button>
        <section ref={loginCard} className={`assistantLogin loginCard${lampOn ? " loginCard--lit" : ""}`}>
          <svg className="loginLampBeam" aria-hidden="true"><path ref={loginBeamPath} className="loginBeamShape"/><circle ref={loginBeamSpot} className="loginBeamSpot" r="0"/></svg>
          {loginTheme === "dark" ? (
            <button ref={loginOwl} type="button" className={`loginOwl${owlAway ? " loginOwl--away" : ""}`} onClick={() => setOwlAway(true)} aria-label={tr("Chạm để cú mèo bay đi")} tabIndex={owlAway ? -1 : 0}>
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
            </button>
          ) : (
            <div className="loginSparrows" aria-hidden="true">{[0, 1, 2, 3].map((bird) => (
              <svg key={bird} className={`loginSparrow loginSparrow--${bird + 1}`} viewBox="0 0 100 85">
                <path className="sparrowTail" d="M30 54 4 62l-3 9 31-7 18-8Z"/><path className="sparrowBody" d="M23 48Q34 29 62 36q21 7 17 25-6 15-29 14-23-1-27-27Z"/>
                <path className="sparrowWing" d="M42 48Q25 27 30 3q24 6 33 36l-2 14Z"/><path className="sparrowWingLight" d="M47 44Q36 24 38 15q14 9 18 27"/>
                <path className="sparrowCap" d="M65 35q6-20 23-10 12 7 8 21l-10 8-20-3Z"/><path className="sparrowCheek" d="M63 46q10-7 21-1l-1 14q-15 5-22-5Z"/>
                <circle className="sparrowEyeRing" cx="79" cy="40" r="6"/><circle className="sparrowEye" cx="80" cy="40" r="3"/><circle className="sparrowGlint" cx="78" cy="38" r="1.2"/>
                <path className="sparrowBeak" d="m94 45 6 5-8 3Z"/><path className="sparrowFoot" d="m47 73-2 9m10-9 3 9"/>
              </svg>
            ))}</div>
          )}
          <div className="assistantLogo">AI</div>
          <h1>Avibi Platform</h1>
          <label>
            Language
            <select
              value={language}
              onChange={(event) => changeLanguage(event.target.value)}
            >
              {UI_LANGUAGES.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <p>
            {tr(
              authMode === "login"
                ? "Đăng nhập để bắt đầu."
                : "Tạo tài khoản dùng chung với AI Role Play.",
            )}
          </p>
          {error && (
            <div className="assistantError">{tr(errorSource(error))}</div>
          )}
          {authMode === "register" && (
            <input
              placeholder={tr("Tên hiển thị")}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          )}
          <input
            placeholder={tr("Tên đăng nhập")}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
          <div className="loginPasswordField">
            <input
              ref={loginPasswordInput}
              type="password"
              placeholder={tr("Mật khẩu")}
              aria-label={tr("Mật khẩu")}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && submitAuth()}
            />
            <span ref={loginPasswordReveal} className="loginPasswordReveal" aria-hidden="true">{password}</span>
            <button ref={loginLampButton} className="loginLamp" type="button" onClick={() => { setLampOn((value) => !value); loginBeamPath.current?.setAttribute("d", ""); loginBeamSpot.current?.setAttribute("r", "0"); loginPasswordReveal.current?.style.setProperty("--reveal-x", "-100px"); loginOwl.current?.classList.remove("owlShone"); loginCard.current?.querySelectorAll(".loginSparrow").forEach((bird) => bird.classList.remove("sparrowShone")); }} aria-label={tr(lampOn ? "Tắt đèn và ẩn mật khẩu" : "Bật đèn để soi mật khẩu")} aria-pressed={lampOn} title={tr(lampOn ? "Tắt đèn" : "Bật đèn rồi đưa đến mật khẩu")}>
              <svg viewBox="0 0 32 32" aria-hidden="true"><path d="m6 5 7 7-3 3-7-7 3-3Zm8 8 12 12-4 4-12-12 4-4Zm12 10 3-3M5 2 2 5m12 3 3-3"/></svg>
            </button>
          </div>
          <button onClick={submitAuth}>
            {tr(authMode === "login" ? "Đăng nhập" : "Tạo tài khoản")}
          </button>
          <button
            className="linkButton"
            onClick={() =>
              setAuthMode(authMode === "login" ? "register" : "login")
            }
          >
            {tr(
              authMode === "login"
                ? "Chưa có tài khoản? Đăng ký"
                : "Đã có tài khoản? Đăng nhập",
            )}
          </button>
        </section>
      </div>
    );
  if (landingOnly)
    return (
      <div className={`platformWorkspace${workspaceCollapsed ? " platformWorkspaceCollapsed" : ""}`}>
        <aside className="platformWorkspaceSidebar">
          <a className="platformWorkspaceBrand" href="/" title="Avibi Platform"><span>AI</span><b>Avibi Platform</b></a>
          <section className="platformWorkspaceGroup">
            <small>{tr("\u004b\u0068\u00f4\u006e\u0067 \u0067\u0069\u0061\u006e")}</small>
            <button className={workspacePath.includes("/ai-assistant") ? "active" : ""} onClick={() => navigateWorkspace("/ai-assistant?workspace=1")} title={tr("AI Assistant")}><span className="platformWorkspaceNavIcon" aria-hidden="true">✦</span><span className="platformWorkspaceNavLabel">{tr("AI Assistant")}</span></button>
            <button className={workspacePath.includes("/role-play-ai") ? "active" : ""} onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=characters")} title={tr("AI Role Play")}><span className="platformWorkspaceNavIcon" aria-hidden="true">◉</span><span className="platformWorkspaceNavLabel">{tr("AI Role Play")}</span></button>
          </section>
          {workspacePath.includes("/ai-assistant") && <section className="platformWorkspaceGroup platformWorkspaceTaskGroup">
            <small>{tr("\u0054\u00e1\u0063 \u0076\u1ee5 \u0074\u0072\u1ee3 \u006c\u00fd")}</small>
            {(["assistant_general", "assistant_psychology", "assistant_health", "assistant_homework", "assistant_tarot"] as Mode[]).map((item) => (
              <button key={item} onClick={() => navigateWorkspace(`/ai-assistant?workspace=1&mode=${item}`)}>{tr(MODES.find((modeItem) => modeItem.id === item)?.title || "AI Assistant")}</button>
            ))}
          </section>}
          {workspacePath.includes("/role-play-ai") && <section className="platformWorkspaceGroup platformWorkspaceRoleTasks platformWorkspaceTaskGroup">
            <small>{tr("Nhân vật")}</small>
            <button onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=characters")}>{tr("Nhân vật của tôi")}</button>
            <button onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=create&createMode=preset")}>{tr("Tạo nhân vật")}</button>
            <button onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=create&createMode=mirror")}>{tr("Tạo bản sao")}</button>
            <button onClick={() => navigateWorkspace("/role-play-ai?workspace=1&view=create&createMode=custom")}>{tr("Sáng tạo")}</button>
          </section>}
          <section className="platformWorkspaceGroup platformWorkspaceRecent">
            <small>{tr("\u0047\u1ea7\u006e \u0111\u00e2\u0079")}</small>
            {historyError && <button onClick={() => void loadChats().catch(() => setHistoryError(true))}>{tr("Không tải được lịch sử. Thử lại")}</button>}
            {(workspacePath.includes("/ai-assistant")
              ? chats.map((item) => ({ id: item.id, kind: "assistant" as const, label: chatTitle(item), date: item.created_at || "", path: `/ai-assistant?workspace=1&chat=${item.id}` }))
              : rolePlayRooms.map((item) => ({ id: item.id, kind: "roleplay" as const, label: item.name, date: item.created_at || "", path: `/role-play-ai?workspace=1&view=chat&room=${item.id}` }))
            ).sort((left, right) => right.date.localeCompare(left.date)).map((item) => (
              <div className="platformWorkspaceRecentRow" key={`${item.kind}:${item.id}`}>
                <button title={item.label} onClick={() => navigateWorkspace(item.path)}>{item.label}</button>
                <button className="platformWorkspaceRecentDelete" title={tr("Xóa cuộc trò chuyện")} aria-label={`${tr("Xóa cuộc trò chuyện")}: ${item.label}`} onClick={() => void removeWorkspaceConversation(item.id, item.kind, item.label)}>×</button>
              </div>
            ))}
          </section>
          <button className="platformWorkspaceMemory" onClick={() => navigateWorkspace("/ai-assistant?workspace=1&panel=memory")} title={tr("Ghi nhớ & nhắc nhở")}><span className="platformWorkspaceNavIcon" aria-hidden="true">◷</span><span className="platformWorkspaceNavLabel">{tr("Ghi nhớ & nhắc nhở")}</span></button>
          <section className="platformWorkspaceAccount" aria-label={tr("Tài khoản")}>
            <button className="platformWorkspaceIdentity" onClick={() => setWorkspaceAccountMenuOpen((open) => !open)} aria-expanded={workspaceAccountMenuOpen} aria-haspopup="dialog" title={tr("Cài đặt tài khoản")}>
              {account.avatar_url
                ? <img src={account.avatar_url} alt="" />
                : <span>{account.display_name?.[0]?.toUpperCase() || "AI"}</span>}
              <span className="platformWorkspaceIdentityText"><b>{account.display_name}</b><small>{account.username ? `@${account.username}` : tr("Tài khoản")}</small></span>
            </button>
            <button className="platformWorkspaceCollapse" onClick={() => { const next = !workspaceCollapsed; setWorkspaceCollapsed(next); localStorage.setItem("avibi_workspace_collapsed", String(next)); setWorkspaceAccountMenuOpen(false); }} aria-label={tr(workspaceCollapsed ? "Mở rộng thanh công cụ" : "Thu gọn thanh công cụ")} title={tr(workspaceCollapsed ? "Mở rộng thanh công cụ" : "Thu gọn thanh công cụ")}>{workspaceCollapsed ? "›" : "‹"}</button>
          </section>
        </aside>
        {workspaceCollapsed && <button
          className="platformWorkspaceRestore"
          onClick={() => { setWorkspaceCollapsed(false); localStorage.setItem("avibi_workspace_collapsed", "false"); }}
          aria-label={tr("Mở rộng thanh công cụ")}
          title={tr("Mở rộng thanh công cụ")}
        >›</button>}
        {workspaceAccountMenuOpen && <>
          <button className="platformWorkspaceMenuScrim" onClick={() => setWorkspaceAccountMenuOpen(false)} aria-label={tr("Đóng")} tabIndex={-1} />
          <section className="platformWorkspaceAccountMenu" role="dialog" aria-label={tr("Cài đặt tài khoản")}>
            <div className="platformWorkspaceAccountMenuHead"><b>{account.display_name}</b><small>@{account.username || account.id}</small></div>
            <button onClick={() => openWorkspaceAccount("profile")}><span aria-hidden="true">♙</span>{tr("Hồ sơ")}</button>
            <button onClick={() => openWorkspaceAccount("security")}><span aria-hidden="true">⚿</span>{tr("Đổi mật khẩu")}</button>
            <div className="platformWorkspaceAccountMenuDivider" />
            <button onClick={() => void toggleTheme()}><span aria-hidden="true">◐</span>{tr("Giao diện")}: {account.theme === "dark" ? tr("Tối") : tr("Sáng")}</button>
            <label className="platformWorkspaceAccountMenuLanguage"><span aria-hidden="true">◎</span><span>{tr("Ngôn ngữ")}</span><select value={language} onChange={(event) => void changeLanguage(event.target.value)} aria-label={tr("Ngôn ngữ")}>{UI_LANGUAGES.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>
            <div className="platformWorkspaceAccountMenuDivider" />
            <button onClick={() => void logout()}><span aria-hidden="true">↪</span>{tr("Đăng xuất")}</button>
          </section>
        </>}
        <section className="platformWorkspaceContent">
          {workspaceFramePaths.map((framePath, frameIndex) => framePath !== "about:blank" && (
            <iframe
              key={frameIndex}
              ref={(node) => { workspaceFrameRefs.current[frameIndex] = node; }}
              title={framePath.includes("role-play-ai") ? "AI Role Play" : "AI Assistant"}
              src={framePath}
              className={activeWorkspaceFrame === frameIndex ? "active" : "inactive"}
              aria-hidden={activeWorkspaceFrame !== frameIndex}
              onLoad={(event) => {
                try {
                  const doc = event.currentTarget.contentDocument;
                  if (!doc || doc.getElementById("avibi-workspace-frame-style")) return;
                  const style = doc.createElement("style");
                  style.id = "avibi-workspace-frame-style";
                  doc.documentElement.dataset.embeddedWorkspace = "true";
                  style.textContent = `.shell>aside,.assistantApp>aside{display:none!important}.shell{min-height:100vh}.shell>main{max-width:none;width:100%;margin:0;padding:26px 36px}.assistantApp{grid-template-columns:minmax(0,1fr)!important;width:100%;height:100vh}.assistantApp>main{min-width:0}`;
                  doc.head.appendChild(style);
                } catch {}
              }}
            />
          ))}
          {!workspaceFrameReady && <div className="platformWorkspaceLoading"><span>AI</span><b>Avibi Platform</b></div>}
          {reminderToast && <button className="assistantReminderToast platformReminderToast" onClick={() => setReminderToast("")}><b>{tr("\u0110\u1ebfn gi\u1edd r\u1ed3i")}</b><span>{reminderToast}</span><i>x</i></button>}
        </section>
          {workspaceAccountPanel && <div className="platformWorkspaceAccountBackdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setWorkspaceAccountPanel(null); }}>
            <section className="platformWorkspaceAccountDialog" role="dialog" aria-modal="true" aria-label={tr("Tài khoản")}>
              <header><div><small>AVIBI PLATFORM</small><h2>{tr("Tài khoản")}</h2></div><button onClick={() => setWorkspaceAccountPanel(null)} aria-label={tr("Đóng")}>×</button></header>
              <div className="platformWorkspaceAccountTabs">
                <button className={workspaceAccountPanel === "profile" ? "active" : ""} onClick={() => { setWorkspaceAccountPanel("profile"); setWorkspaceAccountMessage(""); setWorkspaceAccountError(""); }}>{tr("Hồ sơ")}</button>
                <button className={workspaceAccountPanel === "security" ? "active" : ""} onClick={() => { setWorkspaceAccountPanel("security"); setWorkspaceAccountMessage(""); setWorkspaceAccountError(""); }}>{tr("Mật khẩu")}</button>
              </div>
              <div className="platformWorkspaceAccountBody">
                {workspaceAccountError && <p className="platformWorkspaceAccountError" role="alert">{tr(errorSource(workspaceAccountError))}</p>}
                {workspaceAccountMessage && <p className="platformWorkspaceAccountSuccess" role="status">{tr(workspaceAccountMessage)}</p>}
                {workspaceAccountPanel === "profile" ? <>
                  <label className="platformWorkspaceAvatarPicker">
                    {account.avatar_url ? <img src={account.avatar_url} alt="" /> : <span>{account.display_name?.[0]?.toUpperCase() || "AI"}</span>}
                    <b>{tr("Thay ảnh đại diện")}</b>
                    <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" disabled={workspaceAccountBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadWorkspaceAvatar(file); event.target.value = ""; }} />
                  </label>
                  <label>{tr("Tên đăng nhập")}<input value={account.username || ""} disabled /></label>
                  <label>{tr("Tên hiển thị")}<input maxLength={80} value={workspaceProfileName} onChange={(event) => setWorkspaceProfileName(event.target.value)} /></label>
                  <label>{tr("Giới thiệu")}<textarea maxLength={500} value={workspaceProfileBio} onChange={(event) => setWorkspaceProfileBio(event.target.value)} /></label>
                  <button disabled={workspaceAccountBusy || !workspaceProfileName.trim()} onClick={() => void saveWorkspaceProfile()}>{tr("Lưu hồ sơ")}</button>
                </> : <>
                  <label>{tr("Mật khẩu hiện tại")}<input type={workspaceShowPasswords ? "text" : "password"} value={workspaceCurrentPassword} onChange={(event) => setWorkspaceCurrentPassword(event.target.value)} /></label>
                  <label>{tr("Mật khẩu mới")}<input type={workspaceShowPasswords ? "text" : "password"} value={workspaceNewPassword} onChange={(event) => setWorkspaceNewPassword(event.target.value)} /></label>
                  <label className="platformWorkspaceShowPassword"><input type="checkbox" checked={workspaceShowPasswords} onChange={(event) => setWorkspaceShowPasswords(event.target.checked)} />{tr("Hiện mật khẩu")}</label>
                  <button disabled={workspaceAccountBusy || !workspaceCurrentPassword || workspaceNewPassword.length < 6} onClick={() => void saveWorkspacePassword()}>{tr("Đổi mật khẩu")}</button>
                </>}
              </div>
            </section>
          </div>}
      </div>
    );
  const selectedMode = MODES.find((item) => item.id === mode)!;
  const taskRoom = Boolean(chat && mode !== "assistant_general");
  return (
    <div className="assistantApp">
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
        <button className="newAssistantChat" onClick={() => newChat()}>
          ＋ {tr("Cuộc trò chuyện mới")}
        </button>
        <button className="assistantMemoryButton" onClick={() => {setMemoryPanelOpen(true);setSidebarOpen(false);}}>
          ◷ {tr("Ghi nhớ & nhắc nhở")}
        </button>
        <nav className="assistantShortcuts">
          <strong>{tr("Tác vụ")}</strong>
          {MODES.filter((item) => item.id !== "assistant_general").map(
            (item) => (
              <button
                className={mode === item.id && Boolean(chat) ? "active" : ""}
                onClick={() => openTaskRoom(item.id)}
                key={item.id}
              >
                <i>{item.icon}</i>
                <span>
                  <b>{tr(item.title)}</b>
                  <small>{tr(item.copy)}</small>
                </span>
              </button>
            ),
          )}
        </nav>
        <div className="assistantHistory">
          <strong>{tr("Gần đây")}</strong>
          {historyError && <button onClick={() => void loadChats().catch(() => setHistoryError(true))}>{tr("Không tải được lịch sử. Thử lại")}</button>}
          {chats.length ? (
            chats.map((item) => (
              <div className="assistantHistoryItem" key={item.id}>
                <button onClick={() => openChat(item)}>
                  {chatTitle(item)}
                </button>
                <button
                  title={tr("Xóa cuộc trò chuyện")}
                  onClick={() => removeChat(item)}
                >
                  ×
                </button>
              </div>
            ))
          ) : (
            <small>{tr("Bạn chưa có cuộc trò chuyện nào.")}</small>
          )}
        </div>
        <div className="assistantSideBottom">
          <a href="/role-play-ai">AI Role Play →</a>
          <button onClick={logout}>{tr("Đăng xuất")}</button>
        </div>
      </aside>
      <main>
        {reminderToast && <button className="assistantReminderToast" onClick={()=>setReminderToast("")}><b>{tr("Đến giờ rồi")}</b><span>{reminderToast}</span><i>×</i></button>}
        {!window.location.search.includes("workspace=1") && <header>
          <button
            className="assistantMobileMenu"
            onClick={() => setSidebarOpen((value) => !value)}
          >
            ☰
          </button>
          <span className="assistantHeaderSpacer" />
          <div>
            <select
              value={language}
              onChange={(event) => changeLanguage(event.target.value)}
            >
              {UI_LANGUAGES.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.label}
                </option>
              ))}
            </select>
            <button onClick={toggleTheme}>
              {account.theme === "dark" ? `☀ ${tr("Sáng")}` : `☾ ${tr("Tối")}`}
            </button>
          </div>
        </header>}
        {memoryPanelOpen && <div className="assistantMemoryBackdrop" role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)setMemoryPanelOpen(false);}}>
          <section className="assistantMemoryPanel" role="dialog" aria-modal="true" aria-label={tr("Ghi nhớ & nhắc nhở")}>
            <header><div><small>AVIBI ASSISTANT</small><h2>{tr("Ghi nhớ & nhắc nhở")}</h2></div><button onClick={()=>setMemoryPanelOpen(false)} aria-label="Close">×</button></header>
            {error&&<div className="assistantError assistantMemoryError">{tr(errorSource(error))}</div>}
            <div className="assistantMemoryBody">
              <section className="assistantMemorySection">
                <h3>{tr("Trí nhớ của bạn")}</h3>
                <label className="assistantMemoryConsent"><input type="checkbox" checked={memoryEnabled} onChange={(event)=>void toggleMemory(event.target.checked).catch((reason)=>setError(String(reason)))}/><span>{tr("Cho phép AI Assistant ghi nhớ điều bạn chủ động lưu")}</span></label>
                {memoryEnabled && <>
                  <div className="assistantMemoryCreate"><textarea value={memoryDraft} onChange={(event)=>setMemoryDraft(event.target.value)} maxLength={500} placeholder={tr("Thêm điều cần ghi nhớ")}/><div><small>{chat?tr("Ghi nhớ chỉ dùng trong cuộc hội thoại này."):tr("Mở một cuộc hội thoại để thêm ghi nhớ.")}</small><button disabled={!chat||!memoryDraft.trim()} onClick={()=>void saveMemory().catch((reason)=>setError(String(reason)))}>{tr("Lưu trí nhớ")}</button></div></div>
                  {savedMemories.length?savedMemories.map((item)=><article className="assistantMemoryItem" key={item.id}><span><b>{tr(MODES.find((value)=>value.id===item.mode)?.title||"AI Assistant")}</b>{editingMemoryId===item.id?<textarea value={editingMemoryDraft} maxLength={500} onChange={(event)=>setEditingMemoryDraft(event.target.value)}/>:<p>{item.content}</p>}</span><div>{editingMemoryId===item.id?<><button onClick={()=>void updateMemory(item).catch((reason)=>setError(String(reason)))}>{tr("Lưu")}</button><button onClick={()=>setEditingMemoryId("")}>{tr("Hủy")}</button></>:<button onClick={()=>{setEditingMemoryId(item.id);setEditingMemoryDraft(item.content);}}>{tr("Sửa")}</button>}<button onClick={()=>void removeMemory(item).catch((reason)=>setError(String(reason)))}>{tr("Xóa")}</button></div></article>):<p className="assistantMemoryEmpty">{tr("Chưa có điều gì được lưu.")}</p>}
                  <button className="assistantMemoryDisable" onClick={()=>void toggleMemory(false).catch((reason)=>setError(String(reason)))}>{tr("Tắt và xóa mọi trí nhớ")}</button>
                </>}
              </section>
              <section className="assistantMemorySection">
                <h3>{tr("Nhắc nhở")}</h3><label className="assistantMemoryConsent"><input type="checkbox" checked={notificationsEnabled} onChange={(event)=>void toggleClientNotifications(event.target.checked)}/><span>{tr("Thông báo trên client")}</span></label><p className="assistantMemoryHint">{tr("Để ứng dụng mở để nhận nhắc. Có thể cấp quyền trình duyệt để hiện thông báo khi chuyển tab.")}</p>
                <div className="assistantReminderCreate"><input value={reminderDraft} onChange={(event)=>setReminderDraft(event.target.value)} maxLength={200} placeholder={tr("Nhắc mình về…")}/><label>{tr("Ngày và giờ")}<input type="datetime-local" value={reminderTime} min={localDateTimeValue()} onChange={(event)=>setReminderTime(event.target.value)}/></label><button disabled={!reminderDraft.trim()||!reminderTime} onClick={()=>void createReminder().catch((reason)=>setError(String(reason)))}>{tr("Tạo nhắc nhở")}</button></div>
                {reminders.length?reminders.map((item)=><article className="assistantMemoryItem" key={item.id}><span><b>{item.title}</b><p>{new Date(item.due_at).toLocaleString(language==="vi"?"vi-VN":language)}</p><small>{item.status==="done"?tr("Hoàn tất"):item.status==="paused"?tr("Tạm dừng"):item.last_notified_at?tr("Đến giờ rồi"):""}</small></span><div>{item.status!=="done"&&<><button onClick={()=>void updateReminder(item,{status:item.status==="active"?"paused":"active"}).catch((reason)=>setError(String(reason)))}>{tr(item.status==="active"?"Tạm dừng":"Bật lại")}</button><button onClick={()=>void updateReminder(item,{status:"done"}).catch((reason)=>setError(String(reason)))}>{tr("Hoàn tất")}</button></>}<button onClick={()=>void removeReminder(item).catch((reason)=>setError(String(reason)))}>{tr("Xóa")}</button></div></article>):<p className="assistantMemoryEmpty">{tr("Chưa có nhắc nhở.")}</p>}
              </section>
            </div>
          </section>
        </div>}
        <section
          ref={conversationRef}
          className={`assistantConversation ${messages.length ? "hasMessages" : ""}`}
        >
          {!messages.length && !taskRoom && (
            <div className="assistantWelcome">
              <span>✦</span>
              <h1>AI Assistant</h1>
              <p>{tr("Hỏi mình bất cứ điều gì")}</p>
            </div>
          )}
          <div className="assistantMessages">
            {taskRoom && (
              <div className="assistantRoomHero">
                <i>{selectedMode.icon}</i>
                <div>
                  <small>{tr("Phòng chat chuyên biệt")}</small>
                  <h1>{tr(selectedMode.title)}</h1>
                  <strong className="assistantRoomSlogan">
                    {tr(selectedMode.slogan)}
                  </strong>
                  <p>{tr(selectedMode.copy)}</p>
                </div>
              </div>
            )}
            {taskRoom && !messages.length && (
              <article className="assistant assistantRoomGreeting">
                <b>{tr(selectedMode.title)}</b>
                <p>{tr(selectedMode.greeting)}</p>
              </article>
            )}
            {taskRoom && mode === "assistant_tarot" && (
              <p className="tarotNotice assistantRoomNotice">
                {tr(
                  "Nội dung chỉ để tham khảo và chiêm nghiệm. Không có lá số hay quẻ bài nào thay đổi được vận mệnh của bạn ngoài lựa chọn và sự cố gắng của chính bạn.",
                )}
              </p>
            )}
            {messages.map((item, index) => (
              <article className={item.role} key={item.id}>
                <b>
                  {item.role === "user" ? tr("Bạn") : tr(selectedMode.title)}
                </b>
                <p data-no-translate="true" translate="no">
                  {item.text}
                </p>
                {item.role==="user"&&<button className="assistantSaveMemory" onClick={()=>{setMemoryDraft(item.text.slice(0,500));setMemoryPanelOpen(true);}}>{tr("Lưu vào trí nhớ")}</button>}
                {item.interrupted && (
                  <div className="assistantInterrupted">
                    <span>{tr("Câu trả lời bị gián đoạn")}</span>
                    <button
                      disabled={busy}
                      onClick={() => {
                        const previous = messages
                          .slice(0, index)
                          .reverse()
                          .find((message) => message.role === "user");
                        if (previous) {
                          const attachment = previous.sources?.[0];
                          const storedFile = attachment?.document_id
                            ? roomFiles.find(
                                (file) => file.id === attachment.document_id,
                              )
                            : undefined;
                          if (storedFile)
                            void retryPrevious(previous, storedFile);
                          else void send(previous.text);
                        }
                      }}
                    >
                      {tr("Thử lại")}
                    </button>
                  </div>
                )}
                {Boolean(item.sources?.length) && (
                  <div className="assistantSources">
                    {item.sources!.map((source) => (
                      <span key={`${item.id}-${source.index}`}>
                        [{source.index}] {source.filename}
                        {source.location ? ` · ${source.location}` : ""}
                      </span>
                    ))}
                  </div>
                )}
                {item.role === "assistant" &&
                  index === messages.length - 1 &&
                  Boolean(item.suggestions?.length) && (
                    <div className="assistantSuggestions">
                      {item.suggestions!.map((suggestion) => (
                        <button
                          key={suggestion}
                          disabled={busy}
                          onClick={() => send(suggestion)}
                          data-no-translate="true"
                          translate="no"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
              </article>
            ))}
            {busy &&
              !messages.some((item) => item.id.startsWith("stream-")) && (
                <article className="assistant">
                  <b>{tr(selectedMode.title)}</b>
                  <p>{tr("Đang suy nghĩ…")}</p>
                </article>
              )}
          </div>
        </section>
        <footer className="assistantComposer">
          {availableModels.length > 0 && (
            <label className="assistantModelPicker">
              {tr("Model")}
              <select
                value={selectedModel}
                onChange={(event) => setSelectedModel(event.target.value)}
              >
                {availableModels.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {roomFiles.length > 0 && (
            <div className="assistantKnowledge">
              {roomFiles.map((item) => (
                <span key={item.id}>
                  📚 {item.filename}
                  <button
                    title={tr("Xóa nguồn")}
                    onClick={() => removeRoomFile(item)}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          {file && (
            <div className="assistantFile">
              📎 {file.name}
              <button onClick={() => setFile(null)}>×</button>
            </div>
          )}
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send();
              }
            }}
            placeholder={tr(
              mode === "assistant_tarot"
                ? "Gửi Bát Tự, lá số minh họa hoặc đặt câu hỏi để chiêm nghiệm…"
                : "Hỏi mình bất cứ điều gì…",
            )}
          />
          <div>
            <input
              ref={fileInput}
              type="file"
              accept=".txt,.md,.pdf,.docx,.pptx,.csv,.xlsx,.jpg,.jpeg,.png,.webp,.gif"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
            <button onClick={() => fileInput.current?.click()}>
              📎 {tr("Gửi file")}
            </button>
            <span>
              {selectedMode.icon} {tr(selectedMode.title)}
            </span>
            <button
              className="assistantSend"
              onClick={() => send()}
              disabled={busy}
            >
              ↑
            </button>
          </div>
          {error && (
            <div className="assistantError">{tr(errorSource(error))}</div>
          )}
        </footer>
        {!messages.length && !taskRoom && (
          <section className="assistantTasks">
            <h2>{tr("Phòng chat chuyên biệt")}</h2>
            <div>
              {MODES.filter((item) => item.id !== "assistant_general").map(
                (item) => {
                  const room = chats.find((value) => value.mode === item.id);
                  return (
                    <button
                      className={mode === item.id ? "active" : ""}
                      onClick={() => openTaskRoom(item.id)}
                      key={item.id}
                    >
                      <i>{item.icon}</i>
                      <span>
                        <b>{tr(item.title)}</b>
                        <small>{tr(item.copy)}</small>
                        <em>
                          {room ? chatTitle(room) : tr("Mở phòng chat")} →
                        </em>
                      </span>
                    </button>
                  );
                },
              )}
            </div>
            {mode === "assistant_tarot" && (
              <p className="tarotNotice">
                {tr(
                  "Nội dung chỉ để tham khảo và chiêm nghiệm. Không có lá số hay quẻ bài nào thay đổi được vận mệnh của bạn ngoài lựa chọn và sự cố gắng của chính bạn.",
                )}
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
