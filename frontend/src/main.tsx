import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import "./style.css";
import "./chat.css";
import AssistantApp from "./assistant/AssistantApp";
import {
  localizeInterface,
  localizedError,
  rememberLanguage,
  setRuntimeTranslations,
  storedLanguage,
  translationSources,
  translateUiText,
  UI_LANGUAGES,
  type UiLanguage,
} from "./i18n";

type Character = {
  id: string;
  name: string;
  display_name: string;
  description: string;
  creation_type: string;
  simulation_label: boolean;
  preset_type?: string;
  category?: "utility" | "entertainment";
  avatar_url?: string;
  is_public?: boolean;
  character_type?: string;
  tags?: string[];
  creator?: { id: string; name: string; followers?: number };
  rating?: number;
  rating_count?: number;
  usage_count?: number;
  trending_score?: number;
  home_section?: "auto" | "featured" | "popular" | "top_rated" | "hidden";
  reactions?: Record<string, number>;
  identity?: { role?: string };
  support?: {
    primary_role: "study" | "work" | "health" | "lifestyle" | "companion";
    strengths: ("study" | "work" | "health" | "lifestyle" | "companion")[];
    introduction: string;
  };
};
type Room = { id: string; name: string; character_ids: string[] };
type StoryCandidate = { name: string; description: string; source_evidence: string[]; importance: number };
type Message = {
  id: string;
  sender_type: string;
  character_id: string | null;
  text: string;
  interrupted?: boolean;
  sources?: { document_id: string }[];
  suggestions?: string[];
  emotion?: "neutral" | "happy" | "sad" | "angry" | "surprised" | "shy";
  attachment?: {
    document_id: string;
    filename: string;
    status: string;
    error?: string;
  };
};
type HomeSection = {
  id: string;
  name: string;
  rule: "popular" | "trending" | "top_rated" | "favorites" | "tags";
  tags: string[];
};
const reactionEmojis = ["❤️", "😂", "🔥", "👍", "😮"] as const;
function renderRoleplayText(text: string, isCharacter: boolean): ReactNode {
  if (!isCharacter) return text;
  let hasRenderedAction = false;
  return text.split(/(\*\*[^*\n]+\*\*)/g).map((part, index) => {
    const action = part.match(/^\*\*(.+)\*\*$/);
    if (action) {
      hasRenderedAction = true;
      return <strong className="roleplayActionBeat" key={index}>{action[1]}</strong>;
    }
    const content = hasRenderedAction ? part.replace(/^\n/, "") : part;
    hasRenderedAction = false;
    return content;
  });
}
const reactionTotal = (character: Character) =>
  Object.values(character.reactions || {}).reduce(
    (sum, count) => sum + count,
    0,
  );
const API = import.meta.env.VITE_API_URL || "";
const characterSpecPayload = (character: Character) => {
  const presentationFields = new Set([
    "usage_count",
    "trending_score",
    "reactions",
    "rating",
    "rating_count",
    "home_section",
    "creator",
    "is_public",
    "character_type",
    "tags",
  ]);
  return Object.fromEntries(
    Object.entries(character).filter(([key]) => !presentationFields.has(key)),
  );
};
const assetUrl = (value?: string | null): string | undefined =>
  value
    ? /^(https?:|data:|blob:)/.test(value)
      ? value
      : API + value
    : undefined;
const roleLabels = {
  companion: "Đồng hành",
  study: "Học tập",
  work: "Công việc",
  health: "Sức khỏe",
  lifestyle: "Lối sống",
} as const;
const roleOrder = ["companion", "study", "work"] as const;
const suggestedTags = [
  "Anime",
  "Boss",
  "Mafia",
  "Romance",
  "Action",
  "Adventure",
  "Comedy",
  "Comics",
  "Drama",
  "Fantasy",
  "Horror",
  "Sports",
  "Supernatural",
  "Slice of Life",
  "Academy",
  "Actor",
  "Adaptive",
  "AI",
  "Alien",
  "Amnesia",
  "Ancient",
  "Android",
  "Angel",
  "Angst",
  "Animal",
  "Anthro",
  "Anxious",
  "Mystery",
  "Friendship",
  "Work",
  "Study",
];
const userId = localStorage.getItem("demo_user_id") || crypto.randomUUID();
localStorage.setItem("demo_user_id", userId);
const authHeaders = (): Record<string, string> => {
  const token = localStorage.getItem("auth_token");
  return token
    ? { Authorization: `Bearer ${token}` }
    : { "X-Demo-User-Id": userId };
};
type Account = {
  id: string;
  username: string;
  display_name: string;
  theme: "light" | "dark";
  bio: string;
  language: UiLanguage;
  reduced_motion: boolean;
  avatar_url?: string | null;
};
async function responseError(response: Response): Promise<string> {
  const text = await response.text();
  if (storedLanguage() !== "vi") return localizedError(response.status);
  try {
    const payload = JSON.parse(text);
    const detail = payload.detail || payload.error?.message;
    if (Array.isArray(detail))
      return detail
        .map((item: unknown) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") {
            const value = item as { loc?: unknown[]; msg?: string };
            return `${value.loc?.slice(1).join(" → ") || "Dữ liệu"}: ${value.msg || "không hợp lệ"}`;
          }
          return String(item);
        })
        .join("; ");
    if (detail && typeof detail === "object") return JSON.stringify(detail);
    return String(detail || response.statusText || "Yêu cầu không hợp lệ");
  } catch {
    if (/modal-http|internal server error|runner terminated/i.test(text)) {
      return "Dịch vụ vừa được khởi động lại. Vui lòng gửi lại tin nhắn.";
    }
    return (
      text.trim().slice(0, 500) ||
      response.statusText ||
      "Không thể kết nối tới máy chủ."
    );
  }
}
async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch(API + path, {
    method,
    headers: {
      ...authHeaders(),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(await responseError(r));
  const contentType = r.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error("Máy chủ trả về dữ liệu không hợp lệ. Vui lòng thử lại.");
  }
  return r.json();
}
const translationCacheKey = (language: UiLanguage) =>
  `ui_translation_cache_v2:${language}`;
function readTranslationCache(language: UiLanguage): Record<string, string> {
  try {
    return JSON.parse(
      localStorage.getItem(translationCacheKey(language)) || "{}",
    );
  } catch {
    return {};
  }
}
async function translateCached(
  language: UiLanguage,
  texts: string[],
): Promise<string[]> {
  if (language === "vi") return texts;
  const cache = readTranslationCache(language);
  const missing = [...new Set(texts.filter((text) => text && (!cache[text] || cache[text] === text)))];
  if (missing.length) {
    const result = await api<{ translations: string[] }>(
      "/v1/i18n/translate",
      "POST",
      { language, texts: missing },
    );
    missing.forEach((text, index) => {
      const translated = result.translations[index];
      if (translated && translated !== text) cache[text] = translated;
    });
    try {
      localStorage.setItem(
        translationCacheKey(language),
        JSON.stringify(cache),
      );
    } catch {}
  }
  return texts.map((text) => cache[text] || text);
}
const expressionPortraitCache = new Map<string, string>();
const expressionPortraitRequests = new Map<string, Promise<string>>();
const EXPRESSION_CACHE_VERSION = "3";
const expressionPortraitKey = (characterId: string, emotion: string) =>
  `${EXPRESSION_CACHE_VERSION}:${characterId}:${emotion}`;
async function loadExpressionPortrait(
  characterId: string,
  emotion: NonNullable<Message["emotion"]>,
): Promise<string> {
  const key = expressionPortraitKey(characterId, emotion);
  const cached = expressionPortraitCache.get(key);
  if (cached) return cached;
  const pending = expressionPortraitRequests.get(key);
  if (pending) return pending;
  const request = (async () => {
    const response = await fetch(
      `${API}/v1/characters/${characterId}/expression/${emotion}?v=${EXPRESSION_CACHE_VERSION}`,
      { headers: authHeaders() },
    );
    if (!response.ok) throw new Error(String(response.status));
    const url = URL.createObjectURL(await response.blob());
    expressionPortraitCache.set(key, url);
    return url;
  })().finally(() => expressionPortraitRequests.delete(key));
  expressionPortraitRequests.set(key, request);
  return request;
}
function EmotionPortrait({
  characterId,
  emotion,
  name,
}: {
  characterId: string;
  emotion: NonNullable<Message["emotion"]>;
  name: string;
}) {
  const key = expressionPortraitKey(characterId, emotion);
  const [src, setSrc] = useState<string | undefined>(() =>
    expressionPortraitCache.get(key),
  );
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const url = await loadExpressionPortrait(characterId, emotion);
        if (!cancelled) setSrc(url);
      } catch {
        // The message pipeline retries by keeping the typing state visible.
      }
    };
    const cached = expressionPortraitCache.get(key);
    if (cached) setSrc(cached);
    load();
    return () => {
      cancelled = true;
    };
  }, [characterId, emotion, key]);
  const readySrc = expressionPortraitCache.get(key) || src;
  return (
    <div className="emotionPortraitWrap">
      {readySrc && (
        <img
          className="emotionPortrait"
          src={readySrc}
          alt={`Chân dung biểu cảm ${name}`}
        />
      )}
    </div>
  );
}
function MarketCard({
  character,
  onOpen,
}: {
  character: Character;
  onOpen: () => void;
}) {
  return (
    <button className="marketCard" onClick={onOpen}>
      {character.avatar_url ? (
        <img src={assetUrl(character.avatar_url)} alt={character.name} />
      ) : (
        <span className="marketInitial">{character.name[0]}</span>
      )}
      <span className="marketCopy">
        <b>{character.name}</b>
        <small>bởi {character.creator?.name || "Người dùng"}</small>
        <p>{character.description}</p>
        <em>
          ★ {character.rating || "Mới"} · ◉ {character.usage_count || 0} lượt
          dùng
        </em>
        <ReactionSummary character={character} />
      </span>
    </button>
  );
}
function ReactionSummary({ character }: { character: Character }) {
  if (!reactionTotal(character)) return null;
  return (
    <span className="reactionSummary" aria-label="Biểu cảm từ cộng đồng">
      {reactionEmojis
        .filter((emoji) => (character.reactions?.[emoji] || 0) > 0)
        .map((emoji) => (
          <span key={emoji}>
            {emoji} {character.reactions?.[emoji]}
          </span>
        ))}
    </span>
  );
}
function CharacterAvatar({
  character,
  className = "avatar",
}: {
  character: Character;
  className?: string;
}) {
  return character.avatar_url ? (
    <img
      className={`${className} imageAvatar`}
      src={assetUrl(character.avatar_url)}
      alt={character.name}
    />
  ) : (
    <div className={className}>{character.name[0]}</div>
  );
}
function CommunityShowcase({
  character,
  onOpen,
}: {
  character: Character;
  onOpen: () => void;
}) {
  return (
    <button className="card characterIntro showcaseCard" onClick={onOpen}>
      <CharacterAvatar character={character} className="showcaseImage" />
      <div className="showcaseCopy">
        <span className="roleBadge companion">
          {character.character_type || "Cộng đồng"}
        </span>
        <strong>{character.name}</strong>
        <h3>bởi {character.creator?.name || "Người dùng"}</h3>
        <p>{character.description}</p>
        <span className="showcaseMeta">
          ★ {character.rating || "Mới"} · ◉ {character.usage_count || 0} lượt
          dùng <b>Xem →</b>
        </span>
        <ReactionSummary character={character} />
      </div>
    </button>
  );
}
function AssistantHome(){return <AssistantApp landingOnly/>;}
function RolePlayApp() {
  const [uiLanguage, setUiLanguage] = useState<UiLanguage>(storedLanguage);
  const [, setTranslationRevision] = useState(0);
  const [languageLoading, setLanguageLoading] = useState(false);
  const [resourcePreparing, setResourcePreparing] = useState(false);
  const [page, setPage] = useState<
    | "home"
    | "discover"
    | "characters"
    | "create"
    | "rooms"
    | "chat"
    | "memories"
  >(() => {
    const requested = new URLSearchParams(window.location.search).get("view");
    return ["home", "discover", "characters", "create", "rooms", "chat", "memories"].includes(requested || "")
      ? requested as "home" | "discover" | "characters" | "create" | "rooms" | "chat" | "memories"
      : "home";
  });
  const [account, setAccount] = useState<Account | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false),
    [settingsTab, setSettingsTab] = useState<
      "profile" | "account" | "preferences"
    >("profile"),
    [profileName, setProfileName] = useState(""),
    [profileBio, setProfileBio] = useState(""),
    [currentPassword, setCurrentPassword] = useState(""),
    [newPassword, setNewPassword] = useState("");
  const [authReady, setAuthReady] = useState(false),
    [authMode, setAuthMode] = useState<"login" | "register">("login"),
    [authUser, setAuthUser] = useState(""),
    [authPassword, setAuthPassword] = useState(""),
    [authName, setAuthName] = useState("");
  const [chars, setChars] = useState<Character[]>([]),
    [presets, setPresets] = useState<Character[]>([]),
    [rooms, setRooms] = useState<Room[]>([]),
    [room, setRoom] = useState<Room | null>(null),
    [messages, setMessages] = useState<Message[]>([]),
    [homeSections, setHomeSections] = useState<HomeSection[]>([]);
  const [publicCharacters, setPublicCharacters] = useState<Character[]>([]),
    [avatarFile, setAvatarFile] = useState<File | null>(null),
    [makePublic, setMakePublic] = useState(false),
    [characterType, setCharacterType] = useState("companion"),
    [characterTags, setCharacterTags] = useState("");
  const [tagSearch, setTagSearch] = useState("");
  const [publicFilter, setPublicFilter] = useState("all");
  const [myCharacterSourceFilter, setMyCharacterSourceFilter] = useState("all");
  const [myCharacterFilter, setMyCharacterFilter] = useState("all");
  const [myCharacterTypeFilter, setMyCharacterTypeFilter] = useState("all");
  const [typingIds, setTypingIds] = useState<string[]>([]);
  const [speechLoadingId, setSpeechLoadingId] = useState<string | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const speechAbortRef = useRef<AbortController | null>(null);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const speechUrlRef = useRef<string | null>(null);
  const [activeExpression, setActiveExpression] =
    useState<NonNullable<Message["emotion"]>>("neutral");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false),
    [chatToolsCollapsed, setChatToolsCollapsed] = useState(() => window.matchMedia("(max-width: 820px)").matches);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const messagesBox = useRef<HTMLDivElement>(null);
  const activeRoomIdRef = useRef<string | null>(null);
  const workspaceInitialRoomRef = useRef("");
  const rolePlayStreamRef = useRef<AbortController | null>(null);
  const rolePlayStreamSequence = useRef(0);
  function stopRoleplayAudio() {
    speechAbortRef.current?.abort();
    speechAbortRef.current = null;
    const audio = speechAudioRef.current;
    if (audio) { audio.onended = null; audio.onerror = null; audio.pause(); speechAudioRef.current = null; }
    if (speechUrlRef.current) { URL.revokeObjectURL(speechUrlRef.current); speechUrlRef.current = null; }
    setSpeechLoadingId(null);
    setSpeakingId(null);
  }
  async function playRoleplayMessage(messageId: string) {
    if (speechLoadingId === messageId || speakingId === messageId) { stopRoleplayAudio(); return; }
    stopRoleplayAudio();
    setError("");
    const controller = new AbortController();
    speechAbortRef.current = controller;
    setSpeechLoadingId(messageId);
    try {
      const response = await fetch(`${API}/v1/roleplay/messages/${encodeURIComponent(messageId)}/speech`, {
        method: "POST", headers: authHeaders(), signal: controller.signal,
      });
      if (!response.ok) throw new Error(await responseError(response));
      if (!(response.headers.get("content-type") || "").startsWith("audio/")) throw new Error("Gateway không trả về âm thanh.");
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      speechUrlRef.current = url;
      const audio = new Audio(url);
      speechAudioRef.current = audio;
      audio.onended = stopRoleplayAudio;
      audio.onerror = () => { stopRoleplayAudio(); setError("Không phát được tệp âm thanh TTS."); };
      await audio.play();
      if (controller.signal.aborted || speechAudioRef.current !== audio) return;
      setSpeechLoadingId(null);
      setSpeakingId(messageId);
    } catch (error) {
      if (!controller.signal.aborted) { stopRoleplayAudio(); setError(String(error)); }
    }
  }
  useEffect(() => { stopRoleplayAudio(); }, [room?.id, account?.id]);
  useEffect(() => () => {
    speechAbortRef.current?.abort();
    speechAudioRef.current?.pause();
    if (speechUrlRef.current) URL.revokeObjectURL(speechUrlRef.current);
  }, []);
  function cancelRolePlayStream() {
    rolePlayStreamSequence.current += 1;
    rolePlayStreamRef.current?.abort();
    rolePlayStreamRef.current = null;
    setBusy(false);
    setTypingIds([]);
  }
  useEffect(() => () => {
    rolePlayStreamSequence.current += 1;
    rolePlayStreamRef.current?.abort();
  }, []);
  const [selected, setSelected] = useState<string[]>([]),
    [mode, setMode] = useState(() => {
      const requested = new URLSearchParams(window.location.search).get("createMode");
      return ["preset", "custom", "mirror"].includes(requested || "") ? requested! : "preset";
    }),
    [description, setDescription] = useState(""),
    [name, setName] = useState(""),
    [birthDate, setBirthDate] = useState(""),
    [introduction, setIntroduction] = useState(""),
    [customRole, setCustomRole] = useState("companion"),
    [customScenario, setCustomScenario] = useState(""),
    [customGreeting, setCustomGreeting] = useState(""),
    [customExamples, setCustomExamples] = useState(""),
    [existingMediaCharacter, setExistingMediaCharacter] = useState(false),
    [mediaCharacterName, setMediaCharacterName] = useState(""),
    [mediaTitle, setMediaTitle] = useState(""),
    [storyFile, setStoryFile] = useState<File | null>(null),
    [storyUrl, setStoryUrl] = useState(""),
    [storyDocument, setStoryDocument] = useState<{ id: string; filename: string } | null>(null),
    [storyCandidates, setStoryCandidates] = useState<StoryCandidate[]>([]),
    [storyCharacterName, setStoryCharacterName] = useState(""),
    [text, setText] = useState(""),
    [speaker, setSpeaker] = useState("auto"),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [memoryDraft, setMemoryDraft] = useState(""),
    [memoryTarget, setMemoryTarget] = useState<{ kind: "character" | "room"; id: string; label: string } | null>(null),
    [memories, setMemories] = useState<
      { id: string; content: string; pinned: boolean }[]
    >([]);
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 4000);
    return () => window.clearTimeout(timeout);
  }, [notice]);
  useLayoutEffect(() => {
    const root = document.getElementById("root");
    if (root) localizeInterface(root, uiLanguage);
  });
  useEffect(() => {
    let active = true;
    const load = async () => {
      const texts = translationSources();
      const cached = readTranslationCache(uiLanguage);
      const hasCompleteUiCache =
        uiLanguage === "vi" ||
        uiLanguage === "en" ||
        texts.every((text) => Boolean(cached[text]));
      setLanguageLoading(!hasCompleteUiCache);
      try {
        if (uiLanguage === "vi" || uiLanguage === "en")
          setRuntimeTranslations({});
        else {
          const translations = await translateCached(uiLanguage, texts);
          if (!active) return;
          setRuntimeTranslations(
            Object.fromEntries(
              texts.map((text, index) => [text, translations[index] || text]),
            ),
          );
        }
        if (account) await refresh(uiLanguage);
        if (active) setTranslationRevision((value) => value + 1);
      } catch {
        if (active) {
          setRuntimeTranslations({});
          setTranslationRevision((value) => value + 1);
        }
      } finally {
        if (active) setLanguageLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [uiLanguage]);
  function chooseLanguage(language: UiLanguage) {
    rememberLanguage(language);
    if (language === "vi" || language === "en") setRuntimeTranslations({});
    else {
      const texts = translationSources();
      const cached = readTranslationCache(language);
      setRuntimeTranslations(
        Object.fromEntries(
          texts
            .filter((text) => cached[text])
            .map((text) => [text, cached[text]]),
        ),
      );
    }
    setUiLanguage(language);
  }
  async function refresh(language: UiLanguage = uiLanguage) {
    try {
      let [c, p, r, publicItems, sections] = await Promise.all([
        api<Character[]>("/v1/characters"),
        api<{
          characters: Character[];
          groups: {
            name: string;
            description: string;
            members: string;
            preset_types: string[];
          }[];
        }>("/v1/presets"),
        api<Room[]>("/v1/rooms"),
        api<Character[]>("/v1/public/characters"),
        api<HomeSection[]>("/v1/home-sections"),
      ]);
      if (language !== "vi") {
        const catalog = [...c, ...p.characters, ...publicItems];
        const texts = [
          ...new Set(
            catalog
              .flatMap((item) => [
                item.description,
                item.support?.introduction || "",
              ])
              .filter(Boolean),
          ),
        ];
        if (texts.length) {
          const localized = await translateCached(language, texts).catch(() => texts);
          const translations = new Map(
            texts.map((value, index) => [value, localized[index] || value]),
          );
          const apply = (item: Character): Character => ({
            ...item,
            description: translations.get(item.description) || item.description,
            support: item.support
              ? {
                  ...item.support,
                  introduction:
                    translations.get(item.support.introduction) ||
                    item.support.introduction,
                }
              : item.support,
          });
          c = c.map(apply);
          p = { ...p, characters: p.characters.map(apply) };
          publicItems = publicItems.map(apply);
        }
      }
      setChars(c);
      setPresets(p.characters);
      setRooms(r);
      setPublicCharacters(publicItems);
      setHomeSections(sections);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setAuthReady(true);
      return;
    }
    api<Account>("/v1/auth/me")
      .then((value) => {
        setAccount(value);
        chooseLanguage(value.language || storedLanguage());
        document.documentElement.dataset.theme = value.theme || "light";
        localStorage.setItem("preferred_theme", value.theme || "light");
        document.documentElement.dataset.reducedMotion = String(
          value.reduced_motion,
        );
        refresh(value.language || storedLanguage());
      })
      .catch(() => localStorage.removeItem("auth_token"))
      .finally(() => setAuthReady(true));
  }, []);
  useEffect(() => {
    const syncTheme = (event: StorageEvent) => {
      if (event.key !== "preferred_theme" || (event.newValue !== "light" && event.newValue !== "dark")) return;
      document.documentElement.dataset.theme = event.newValue;
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
        setUiLanguage(event.newValue);
        document.documentElement.lang = event.newValue;
        setAccount((current) => current ? { ...current, language: event.newValue! } : current);
      }
      if (event.key === "avibi_account_refresh" && localStorage.getItem("auth_token")) {
        void api<Account>("/v1/auth/me").then(setAccount).catch(() => {});
      }
    };
    window.addEventListener("storage", syncAccount);
    return () => window.removeEventListener("storage", syncAccount);
  }, []);

  async function submitAuth() {
    setError("");
    try {
      const value = await api<Account & { token: string }>(
        `/v1/auth/${authMode}`,
        "POST",
        { username: authUser, password: authPassword, display_name: authName },
      );
      localStorage.setItem("auth_token", value.token);
      let localizedAccount: Account = value;
      if (value.language !== uiLanguage) {
        localizedAccount = await api<Account>("/v1/auth/me", "PATCH", {
          language: uiLanguage,
        });
      }
      setAccount(localizedAccount);
      document.documentElement.dataset.theme = value.theme;
      localStorage.setItem("preferred_theme", value.theme);
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  }
  async function toggleTheme() {
    if (!account) return;
    const theme = account.theme === "dark" ? "light" : "dark";
    const updated = await api<Account>("/v1/auth/me", "PATCH", { theme });
    setAccount(updated);
    document.documentElement.dataset.theme = updated.theme;
    localStorage.setItem("preferred_theme", updated.theme);
  }
  async function logout() {
    await api("/v1/auth/logout", "POST", {}).catch(() => {});
    localStorage.removeItem("auth_token");
    window.location.assign("/");
  }
  function openSettings() {
    if (!account) return;
    setProfileName(account.display_name);
    setProfileBio(account.bio || "");
    setSettingsOpen(true);
  }
  async function saveProfile() {
    if (!account) return;
    const updated = await api<Account>("/v1/auth/me", "PATCH", {
      display_name: profileName,
      bio: profileBio,
    });
    setAccount(updated);
    localStorage.setItem("avibi_account_refresh", String(Date.now()));
    setNotice("Đã lưu hồ sơ");
  }
  async function savePreferences(values: Partial<Account>) {
    const updated = await api<Account>("/v1/auth/me", "PATCH", values);
    setAccount(updated);
    if (values.language) {
      chooseLanguage(updated.language);
    }
    document.documentElement.dataset.theme = updated.theme;
    localStorage.setItem("preferred_theme", updated.theme);
    document.documentElement.dataset.reducedMotion = String(
      updated.reduced_motion,
    );
    setNotice("Đã lưu tùy chọn");
  }
  async function changePassword() {
    const updated = await api<Account>("/v1/auth/me", "PATCH", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    setAccount(updated);
    setCurrentPassword("");
    setNewPassword("");
    setNotice("Đã đổi mật khẩu");
  }
  async function uploadUserAvatar(file: File) {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(API + "/v1/auth/me/avatar", {
      method: "POST",
      headers: authHeaders(),
      body: form,
    });
    if (!response.ok) throw new Error(await responseError(response));
    setAccount(await api<Account>("/v1/auth/me"));
    localStorage.setItem("avibi_account_refresh", String(Date.now()));
  }
  async function finishCreatedCharacter(character: Character) {
    await api(`/v1/characters/${character.id}/publication`, "PATCH", {
      is_public: makePublic,
      character_type: characterType,
      tags: characterTags
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    });
    if (avatarFile) {
      const form = new FormData();
      form.append("file", avatarFile);
      const response = await fetch(
        API + `/v1/characters/${character.id}/avatar`,
        { method: "POST", headers: authHeaders(), body: form },
      );
      if (!response.ok) throw new Error(await responseError(response));
      await waitForExpressionSet(character.id);
    }
    setAvatarFile(null);
    setMakePublic(false);
    setCharacterTags("");
    await refresh();
    const nextRoom = await api<Room>("/v1/rooms", "POST", {
      name: `Trò chuyện với ${character.name}`,
      character_ids: [character.id],
    });
    setRooms((current) => [nextRoom, ...current]);
    await openRoom(nextRoom);
  }
  async function waitForExpressionSet(characterId: string) {
    for (let attempt = 0; attempt < 300; attempt += 1) {
      const result = await api<{ status: "processing" | "ready" }>(
        `/v1/characters/${characterId}/expressions/status`,
      );
      if (result.status === "ready") return;
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    throw new Error("Bộ ảnh biểu cảm tạo quá lâu. Vui lòng thử lại sau.");
  }
  async function prepareStorySource() {
    if (!storyFile && !storyUrl.trim()) throw new Error("Chọn file truyện hoặc nhập đường dẫn truyện trước.");
    let document: { id: string; filename: string };
    if (storyFile) {
      const form = new FormData();
      form.append("file", storyFile);
      const response = await fetch(API + "/v1/character-sources", { method: "POST", headers: authHeaders(), body: form });
      if (!response.ok) throw new Error(await responseError(response));
      document = await response.json();
    } else {
      document = await api("/v1/documents/from-url", "POST", { url: storyUrl.trim() });
    }
    setStoryDocument(document);
    let ready = false;
    for (let attempt = 0; attempt < 90; attempt += 1) {
      const status = await api<{ status: string; error?: string }>(`/v1/documents/${document.id}`);
      if (status.status === "ready") { ready = true; break; }
      if (status.status === "failed") throw new Error(status.error || "Không thể đọc nội dung truyện.");
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    if (!ready) throw new Error("Đọc truyện quá lâu. Hãy thử file TXT hoặc đường dẫn khác.");
    const result = await api<{ candidates: StoryCandidate[] }>(`/v1/documents/${document.id}/discover-characters`, "POST", {});
    setStoryCandidates(result.candidates);
    setStoryCharacterName(result.candidates[0]?.name || "");
  }
  async function createStoryCharacter() {
    if (!storyDocument || !storyCharacterName.trim()) return;
    const character = await api<Character>("/v1/characters/from-document", "POST", { document_id: storyDocument.id, candidate_name: storyCharacterName.trim() });
    await finishCreatedCharacter(character);
    setStoryDocument(null);
    setStoryCandidates([]);
    setStoryCharacterName("");
    setStoryFile(null);
    setStoryUrl("");
  }
  async function reactCharacter(characterId: string, reaction: string) {
    await api(`/v1/characters/${characterId}/reaction`, "PUT", { reaction });
    await refresh();
  }
  useLayoutEffect(() => {
    const box = messagesBox.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [messages, typingIds]);
  async function act(f: () => Promise<void>, preparesResources = false, successMessage = "Tài nguyên đã chuẩn bị xong. Bạn có thể bắt đầu trò chuyện.") {
    setBusy(true);
    if (preparesResources) setResourcePreparing(true);
    setNotice("");
    setError("");
    try {
      await f();
      await refresh();
      if (preparesResources) setNotice(successMessage);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
      if (preparesResources) setResourcePreparing(false);
    }
  }
  async function openRoleplayMemories(target: { kind: "character" | "room"; id: string; label: string }) {
    await act(async () => {
      const path = target.kind === "room" ? `/v1/rooms/${target.id}/memories` : `/v1/characters/${target.id}/memories`;
      setMemories(await api(path));
      setMemoryTarget(target);
      setMemoryDraft("");
      setPage("memories");
    });
  }
  async function addRoleplayMemory() {
    if (!memoryTarget || !memoryDraft.trim()) return;
    const path = memoryTarget.kind === "room" ? `/v1/rooms/${memoryTarget.id}/memories` : `/v1/characters/${memoryTarget.id}/memories`;
    const saved = await api<{ id: string; content: string; pinned: boolean }>(path, "POST", { content: memoryDraft.trim() });
    setMemories((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
    setMemoryDraft("");
    setNotice("Đã lưu ký ức");
  }
  async function localizeStoredSuggestions(items: Message[]) {
    if (uiLanguage === "vi") return items;
    let seenUser = false;
    const initialMessages = new Set<string>();
    for (const item of items) {
      if (item.sender_type === "user") seenUser = true;
      else if (!seenUser && item.sender_type === "character")
        initialMessages.add(item.id);
    }
    const texts = [
      ...new Set(
        items
          .filter((item) => initialMessages.has(item.id))
          .flatMap((item) => item.suggestions || [])
          .filter(Boolean),
      ),
    ];
    if (!texts.length) return items;
    try {
      const result = await translateCached(uiLanguage, texts);
      const translated = new Map(
        texts.map((text, index) => [text, result[index] || text]),
      );
      return items.map((item) =>
        initialMessages.has(item.id)
          ? {
              ...item,
              suggestions: item.suggestions?.map(
                (value) => translated.get(value) || value,
              ),
            }
          : item,
      );
    } catch {
      return items;
    }
  }
  async function openRoom(r: Room) {
    cancelRolePlayStream();
    for (const url of expressionPortraitCache.values()) URL.revokeObjectURL(url);
    expressionPortraitCache.clear();
    activeRoomIdRef.current = r.id;
    setActiveExpression("neutral");
    setRoom(r);
    const stored = await api<Message[]>(`/v1/rooms/${r.id}/messages`);
    if (activeRoomIdRef.current !== r.id) return;
    setMessages(await localizeStoredSuggestions(stored));
    setPage("chat");
  }
  useEffect(() => {
    if (!window.location.search.includes("workspace=1")) return;
    const roomId = new URLSearchParams(window.location.search).get("room");
    if (!roomId || roomId === workspaceInitialRoomRef.current) return;
    const requestedRoom = rooms.find((item) => item.id === roomId);
    if (!requestedRoom) return;
    workspaceInitialRoomRef.current = roomId;
    void openRoom(requestedRoom);
  }, [rooms]);
  useEffect(() => {
    if (!account || !authReady || window.parent === window) return;
    window.parent.postMessage({ type: "avibi-workspace-ready" }, window.location.origin);
  }, [account?.id, authReady]);
  useEffect(() => {
    if (!account || !authReady || window.parent === window) return;
    window.parent.postMessage({ type: "avibi-workspace-history-updated" }, window.location.origin);
  }, [account?.id, authReady, rooms]);
  useEffect(() => {
    if (window.parent === window) return;
    const onWorkspaceNavigation = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.data?.type !== "avibi-workspace-navigate") return;
      const params = new URL(event.data.path, window.location.origin).searchParams;
      const requestedView = params.get("view");
      const requestedMode = params.get("createMode");
      setSettingsOpen(false);
      if (requestedView === "chat") {
        const roomId = params.get("room");
        const requestedRoom = rooms.find((item) => item.id === roomId);
        if (requestedRoom) void openRoom(requestedRoom);
        return;
      }
      if (requestedView === "create") {
        setMode(requestedMode === "mirror" || requestedMode === "custom" ? requestedMode : "preset");
        cancelRolePlayStream();
        activeRoomIdRef.current = null;
        setRoom(null);
        setMessages([]);
        setPage("create");
        return;
      }
      cancelRolePlayStream();
      activeRoomIdRef.current = null;
      setPage("characters");
      setRoom(null);
      setMessages([]);
    };
    window.addEventListener("message", onWorkspaceNavigation);
    return () => window.removeEventListener("message", onWorkspaceNavigation);
  }, [account?.id, authReady, rooms]);
  async function startCharacterChat(character: Character) {
    await act(async () => {
      const nextRoom = await api<Room>("/v1/rooms", "POST", {
        name: `Trò chuyện với ${character.name}`,
        character_ids: [character.id],
      });
      setRooms((current) => [nextRoom, ...current]);
      await openRoom(nextRoom);
    }, true);
  }
  async function addPreset(p: Character) {
    let character = chars.find(
      (character) =>
        character.creation_type === "preset" &&
        character.preset_type === p.preset_type,
    );
    await act(async () => {
      if (!character) {
        character = await api<Character>(
          "/v1/characters",
          "POST",
          characterSpecPayload(p),
        );
        setChars((current) => [...current, character!]);
      }
      const nextRoom = await api<Room>("/v1/rooms", "POST", {
        name: `Trò chuyện với ${character.name}`,
        character_ids: [character.id],
      });
      setRooms((current) => [nextRoom, ...current]);
      await openRoom(nextRoom);
    }, true);
  }
  async function startPublicCharacter(character: Character) {
    const ownedCharacter = chars.find((item) => item.id === character.id);
    if (ownedCharacter) {
      await startCharacterChat(ownedCharacter);
      return;
    }
    await act(async () => {
      const cloned = await api<Character>(
        `/v1/public/characters/${character.id}/clone`,
        "POST",
        {},
      );
      setChars((current) => [...current, cloned]);
      const nextRoom = await api<Room>("/v1/rooms", "POST", {
        name: `Trò chuyện với ${cloned.name}`,
        character_ids: [cloned.id],
      });
      setRooms((current) => [nextRoom, ...current]);
      await openRoom(nextRoom);
    }, true);
  }
  async function createMirror() {
    await act(async () => {
      const character = await api<Character>("/v1/characters/mirror", "POST", {
        name: name.trim(),
        birth_date: birthDate || null,
        description: description.trim(),
        introduction: introduction.trim(),
      });
      setChars((current) =>
        current.some((c) => c.id === character.id)
          ? current
          : [...current, character],
      );
      await finishCreatedCharacter(character);
    }, true);
  }
  async function send(suggestedText?: string) {
    const outgoing = (suggestedText ?? text).trim();
    if (!room || !outgoing || busy) return;
    const sentRoomId = room.id;
    const streamSequence = ++rolePlayStreamSequence.current;
    const controller = new AbortController();
    rolePlayStreamRef.current = controller;
    const value = outgoing,
      tempId = "local-" + crypto.randomUUID();
    const immediateTyper =
      roomChars.length === 1
        ? roomChars[0].id
        : speaker.startsWith("character:")
          ? speaker.slice(10)
          : speaker === "everyone"
            ? roomChars[0]?.id
            : undefined;
    flushSync(() => {
      setText("");
      setError("");
      setBusy(true);
      setTypingIds(immediateTyper ? [immediateTyper] : []);
      setMessages((m) => [
        ...m.map((message) => ({ ...message, suggestions: undefined })),
        { id: tempId, sender_type: "user", character_id: null, text: value },
      ]);
    });
    if (messagesBox.current)
      messagesBox.current.scrollTop = messagesBox.current.scrollHeight;
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    try {
      const response = await fetch(
        API + `/v1/rooms/${sentRoomId}/messages/stream`,
        {
          method: "POST",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ message: value, speaker_mode: speaker }),
          signal: controller.signal,
        },
      );
      if (!response.ok || !response.body)
        throw new Error(await responseError(response));
      const reader = response.body.getReader(),
        decoder = new TextDecoder();
      let buffer = "", receivedDone = false;
      const handle = async (block: string) => {
        if (streamSequence !== rolePlayStreamSequence.current || activeRoomIdRef.current !== sentRoomId) return;
        let event = "",
          data = "";
        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        if (!data) return;
        let payload: any;
        try {
          payload = JSON.parse(data);
        } catch {
          setError(
            "Phản hồi trò chuyện bị gián đoạn. Vui lòng gửi lại tin nhắn.",
          );
          return;
        }
        if (event === "user_message")
          setMessages((m) => m.map((x) => (x.id === tempId ? payload : x)));
        if (event === "typing")
          setTypingIds((ids) =>
            ids.includes(payload.character_id)
              ? ids
              : [...ids, payload.character_id],
          );
        if (event === "character_message") {
          if (
            typeof payload.suggestions_raw === "string" &&
            payload.suggestions_raw.startsWith("@@")
          ) {
            const parsed = payload.suggestions_raw
              .slice(2)
              .split("|")
              .map((item: string) => item.trim())
              .filter(Boolean)
              .slice(0, 3);
            if (parsed.length === 3) payload.suggestions = parsed;
          }
          const emotion = payload.emotion || "neutral";
          if (roomChars.length === 1)
            void loadExpressionPortrait(payload.character_id, emotion).catch(() => {});
          if (streamSequence !== rolePlayStreamSequence.current || activeRoomIdRef.current !== sentRoomId) return;
          flushSync(() => {
            setTypingIds((ids) =>
              ids.filter((id) => id !== payload.character_id),
            );
            setActiveExpression(emotion);
            setMessages((m) => [...m, payload]);
          });
        }
        if (event === "character_error") {
          setTypingIds((ids) =>
            ids.filter((id) => id !== payload.character_id),
          );
          setError(payload.message);
        }
        if (event === "error") setError(payload.message);
        if (event === "done") receivedDone = true;
      };
      while (true) {
        const { done, value: chunk } = await reader.read();
        if (streamSequence !== rolePlayStreamSequence.current || activeRoomIdRef.current !== sentRoomId) break;
        buffer += decoder
          .decode(chunk, { stream: !done })
          .replace(/\r\n/g, "\n");
        let cut;
        while ((cut = buffer.indexOf("\n\n")) >= 0) {
          await handle(buffer.slice(0, cut));
          buffer = buffer.slice(cut + 2);
        }
        if (done) break;
      }
      if (!receivedDone && streamSequence === rolePlayStreamSequence.current) throw new Error("Phản hồi bị gián đoạn trước khi hoàn tất.");
    } catch (e) {
      if (streamSequence === rolePlayStreamSequence.current && activeRoomIdRef.current === sentRoomId) {
        if (!(e instanceof DOMException && e.name === "AbortError")) setError(String(e));
        setTypingIds([]);
        setMessages((current) => current.filter((message) => message.id !== tempId));
      }
    } finally {
      if (streamSequence === rolePlayStreamSequence.current) {
        rolePlayStreamRef.current = null;
        setBusy(false);
        setTypingIds([]);
      }
    }
  }
  async function regenerateMessage(message: Message) {
    if (!room || busy) return;
    await act(async () => {
      const replacement = await api<Message>(
        `/v1/rooms/${room.id}/messages/${message.id}/regenerate`,
        "POST",
      );
      const emotion = replacement.emotion || "neutral";
      if (roomChars.length === 1 && replacement.character_id)
        await loadExpressionPortrait(replacement.character_id, emotion);
      flushSync(() => {
        setMessages((current) =>
          current.map((item) => (item.id === message.id ? replacement : item)),
        );
        setActiveExpression(emotion);
      });
    });
  }
  async function deleteRoom(roomToDelete: Room) {
    if (!confirm(`Xóa cuộc trò chuyện “${roomToDelete.name}”?`)) return;
    await act(async () => {
      await api(`/v1/rooms/${roomToDelete.id}`, "DELETE");
      setRooms((current) => current.filter((r) => r.id !== roomToDelete.id));
      if (room?.id === roomToDelete.id) {
        cancelRolePlayStream();
        activeRoomIdRef.current = null;
        setRoom(null);
        setMessages([]);
        setActiveExpression("neutral");
        setPage("home");
      }
    });
  }
  const roomChars =
    room?.character_ids
      .map((id) => chars.find((c) => c.id === id))
      .filter((c): c is Character => !!c) || [];
  const hasPreset = (preset: Character) =>
    chars.some(
      (character) =>
        character.creation_type === "preset" &&
        character.preset_type === preset.preset_type,
    );
  const matchesSearch = (...values: (string | undefined)[]) =>
    values
      .join(" ")
      .toLocaleLowerCase()
      .includes(search.trim().toLocaleLowerCase());
  // Keep legacy duplicate rows available in `chars` so old rooms can still
  // resolve their member, while showing only one card for each preset.
  const visibleCharacters = chars.filter((character, index, all) => {
    if (character.creation_type !== "preset" || !character.preset_type)
      return true;
    return (
      all.findIndex(
        (item) =>
          item.creation_type === "preset" &&
          item.preset_type === character.preset_type,
      ) === index
    );
  });
  const characterCatalog = [
    ...presets.filter((preset) => !chars.some((character) => character.id === preset.id))
      .map((character) => ({ character, source: "system" as const })),
    ...chars.map((character) => ({ character, source: "owned" as const })),
  ];
  const catalogCharacterType = (character: Character) =>
    character.character_type || character.support?.primary_role || character.category || "other";
  const filteredMyCharacters = characterCatalog.filter(({ character, source }) => {
    const sourceMatch = myCharacterSourceFilter === "all" || myCharacterSourceFilter === source;
    const visibilityMatch = myCharacterFilter === "all" ||
      (myCharacterFilter === "public" ? source === "system" || Boolean(character.is_public) : source === "owned" && !character.is_public);
    const typeMatch = myCharacterTypeFilter === "all" ||
      catalogCharacterType(character) === myCharacterTypeFilter;
    return sourceMatch && visibilityMatch && typeMatch && matchesSearch(
      character.name,
      character.display_name,
      character.description,
      catalogCharacterType(character),
      ...(character.tags || []),
    );
  });
  const myCharacterTypes = [...new Set(characterCatalog.map(({ character }) => catalogCharacterType(character)))].sort();
  const customHomeCharacters = visibleCharacters
    .filter((character) => character.creation_type !== "preset")
    .map((character) => ({
      ...character,
      creator:
        character.creator ||
        (account ? { id: account.id, name: account.display_name } : undefined),
    }));
  const adminCatalogCharacters = presets.map((character) => ({
    ...character,
    creator: { id: "system", name: "Avibi Platform" },
  }));
  const systemHomeCharacters = adminCatalogCharacters.filter(
    (character) =>
      character.category !== "entertainment" &&
      character.home_section !== "hidden",
  );
  const homeCatalogCharacters = [
    ...adminCatalogCharacters,
    ...publicCharacters,
  ];
  const charactersForSection = (section: HomeSection) => {
    const matching = homeCatalogCharacters.filter((character) => {
      if (section.rule === "favorites") return reactionTotal(character) > 0;
      if (section.rule === "trending")
        return (character.trending_score || 0) > 0;
      if (section.rule === "top_rated")
        return (character.rating_count || 0) > 0;
      if (section.rule !== "tags") return true;
      const labels = [
        character.category,
        character.character_type,
        character.identity?.role,
        character.support?.primary_role,
        ...(character.tags || []),
      ]
        .join(" ")
        .toLowerCase();
      return section.tags.some((tag) => labels.includes(tag.toLowerCase()));
    });
    return matching.sort((a, b) => {
      if (section.rule === "favorites")
        return reactionTotal(b) - reactionTotal(a);
      if (section.rule === "top_rated")
        return (b.rating || 0) - (a.rating || 0);
      if (section.rule === "trending")
        return (b.trending_score || 0) - (a.trending_score || 0);
      return (b.usage_count || 0) - (a.usage_count || 0);
    });
  };
  const publicCategories = [
    ["all", "Tất cả"],
    ["companion", "Đồng hành"],
    ["study", "Học tập"],
    ["work", "Công việc"],
    ["entertainment", "Giải trí"],
    ["roleplay", "Role play"],
  ] as const;
  const filteredPublicCharacters = publicCharacters.filter((character) => {
    const labels = [character.character_type, ...(character.tags || [])]
      .join(" ")
      .toLowerCase();
    const categoryMatch =
      publicFilter === "all" ||
      (publicFilter === "roleplay"
        ? /role.?play|fantasy|adventure|drama/.test(labels)
        : labels.includes(publicFilter));
    return (
      categoryMatch &&
      matchesSearch(
        character.name,
        character.description,
        character.character_type,
        ...(character.tags || []),
      )
    );
  });
  const selectedTags = characterTags
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const toggleTag = (tag: string) =>
    setCharacterTags(
      selectedTags.includes(tag)
        ? selectedTags.filter((x) => x !== tag).join(", ")
        : [...selectedTags, tag].slice(0, 8).join(", "),
    );
  if (!authReady)
    return (
      <div className="authPage">
        <div className="authCard">
          <b>AI</b>
          <p>Đang tải…</p>
        </div>
      </div>
    );
  if (!account)
    return (
      <div className="authPage">
        <section className="authCard">
          <div className="authLogo">AI</div>
          <h1>Avibi Platform</h1>
          <label className="authLanguage">
            Ngôn ngữ
            <select
              value={uiLanguage}
              onChange={(event) =>
                chooseLanguage(event.target.value as UiLanguage)
              }
            >
              {UI_LANGUAGES.map((language) => (
                <option value={language.code} key={language.code}>
                  {language.label}
                </option>
              ))}
            </select>
          </label>
          <p>
            {authMode === "login"
              ? "Đăng nhập để tiếp tục các cuộc trò chuyện của bạn."
              : "Tạo tài khoản demo được lưu trong database."}
          </p>
          {error && <div className="error">{error}</div>}
          {authMode === "register" && (
            <label>
              Tên hiển thị
              <input
                value={authName}
                onChange={(e) => setAuthName(e.target.value)}
                placeholder="Tên của bạn"
              />
            </label>
          )}
          <label>
            Tên đăng nhập
            <input
              value={authUser}
              onChange={(e) => setAuthUser(e.target.value)}
              placeholder="ví dụ: thanhcong"
            />
          </label>
          <label>
            Mật khẩu
            <input
              type="password"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitAuth()}
            />
          </label>
          <button onClick={submitAuth}>
            {authMode === "login" ? "Đăng nhập" : "Tạo tài khoản"}
          </button>
          <button
            className="textButton"
            onClick={() =>
              setAuthMode(authMode === "login" ? "register" : "login")
            }
          >
            {authMode === "login"
              ? "Chưa có tài khoản? Đăng ký"
              : "Đã có tài khoản? Đăng nhập"}
          </button>
        </section>
      </div>
    );
  return (
    <div
      className={`shell ${sidebarCollapsed ? "sidebarCollapsed" : ""} ${page === "chat" ? "chatShell" : ""} ${page === "home" ? "homeShell" : ""}`}
    >
      {settingsOpen && account && (
        <div
          className="settingsOverlay"
          onMouseDown={(e) =>
            e.target === e.currentTarget && setSettingsOpen(false)
          }
        >
          <section className="personalSettings">
            <aside className="settingsNav">
              <div className="settingsIdentity">
                {account.avatar_url ? (
                  <img src={API + account.avatar_url} alt="Avatar" />
                ) : (
                  <span>{account.display_name[0]?.toUpperCase()}</span>
                )}
                <b>{account.display_name}</b>
                <small>@{account.username}</small>
              </div>
              <button
                className={settingsTab === "profile" ? "active" : ""}
                onClick={() => setSettingsTab("profile")}
              >
                Hồ sơ công khai
              </button>
              <button
                className={settingsTab === "account" ? "active" : ""}
                onClick={() => setSettingsTab("account")}
              >
                Tài khoản
              </button>
              <button
                className={settingsTab === "preferences" ? "active" : ""}
                onClick={() => setSettingsTab("preferences")}
              >
                Tùy chọn
              </button>
              <button className="settingsLogout" onClick={logout}>
                Đăng xuất
              </button>
            </aside>
            <div className="settingsContent">
              <button
                className="settingsClose"
                onClick={() => setSettingsOpen(false)}
              >
                ×
              </button>
              {settingsTab === "profile" && (
                <>
                  <h2>Hồ sơ công khai</h2>
                  <label className="profileAvatar">
                    {account.avatar_url ? (
                      <img src={API + account.avatar_url} alt="Avatar" />
                    ) : (
                      <span>{account.display_name[0]?.toUpperCase()}</span>
                    )}
                    <b>Thay avatar</b>
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/gif"
                      onChange={(e) =>
                        e.target.files?.[0] &&
                        act(() => uploadUserAvatar(e.target.files![0]))
                      }
                    />
                  </label>
                  <label>
                    Tên đăng nhập
                    <input value={account.username} disabled />
                  </label>
                  <label>
                    Tên hiển thị
                    <input
                      maxLength={80}
                      value={profileName}
                      onChange={(e) => setProfileName(e.target.value)}
                    />
                  </label>
                  <label>
                    Giới thiệu
                    <textarea
                      maxLength={500}
                      value={profileBio}
                      onChange={(e) => setProfileBio(e.target.value)}
                      placeholder="Giới thiệu ngắn về bạn…"
                    />
                  </label>
                  <button onClick={() => act(saveProfile)}>Lưu hồ sơ</button>
                </>
              )}
              {settingsTab === "account" && (
                <>
                  <h2>Tài khoản</h2>
                  <div className="accountSummary">
                    <span>Gói hiện tại</span>
                    <b>Demo</b>
                  </div>
                  <label>
                    Mật khẩu hiện tại
                    <input
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                    />
                  </label>
                  <label>
                    Mật khẩu mới
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Ít nhất 6 ký tự"
                    />
                  </label>
                  <button
                    disabled={!currentPassword || newPassword.length < 6}
                    onClick={() => act(changePassword)}
                  >
                    Đổi mật khẩu
                  </button>
                </>
              )}
              {settingsTab === "preferences" && (
                <>
                  <h2>Tùy chọn</h2>
                  <label>
                    Giao diện
                    <select
                      value={account.theme}
                      onChange={(e) =>
                        savePreferences({
                          theme: e.target.value as Account["theme"],
                        })
                      }
                    >
                      <option value="light">Sáng</option>
                      <option value="dark">Tối</option>
                    </select>
                  </label>
                  <label>
                    Ngôn ngữ
                    <select
                      value={account.language}
                      onChange={(e) =>
                        savePreferences({
                          language: e.target.value as UiLanguage,
                        })
                      }
                    >
                      {UI_LANGUAGES.map((language) => (
                        <option value={language.code} key={language.code}>
                          {language.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="preferenceToggle">
                    <span>
                      <b>Giảm chuyển động</b>
                      <small>Hạn chế animation trong giao diện.</small>
                    </span>
                    <input
                      type="checkbox"
                      checked={account.reduced_motion}
                      onChange={(e) =>
                        savePreferences({ reduced_motion: e.target.checked })
                      }
                    />
                  </label>
                </>
              )}
            </div>
          </section>
        </div>
      )}
      {(languageLoading ||
        resourcePreparing ||
        (busy && page === "create")) && (
        <div className="creatingOverlay" role="status" aria-live="polite">
          <div className="creatingCard">
            <div className="creatingSpinner" />
            {languageLoading ? (
              <>
                <h2>Đang tải ngôn ngữ...</h2>
                <p>Lần đầu lúc nào cũng lâu, chờ xíu nha.</p>
                <small>Giao diện sẽ tự mở khi mọi nội dung đã sẵn sàng.</small>
              </>
            ) : resourcePreparing ? (
              <>
                <h2>Đang chuẩn bị tài nguyên...</h2>
                <p>Nhân vật đang đến với bạn, hãy chờ một xíu.</p>
                <small>Bạn có thể chat ngay khi quá trình hoàn tất.</small>
              </>
            ) : (
              <>
                <h2>Đang hoàn thiện nhân vật...</h2>
                <p>Nhân vật đang đến với bạn, hãy chờ một xíu.</p>
                <small>Khung chat sẽ tự mở sau khi mọi bước hoàn tất.</small>
              </>
            )}
          </div>
        </div>
      )}
      <aside>
        <button
          className="collapseNav"
          onClick={() => setSidebarCollapsed((value) => !value)}
          title={
            sidebarCollapsed ? "Mở thanh điều hướng" : "Thu thanh điều hướng"
          }
        >
          {sidebarCollapsed ? ">>" : "<<"}
        </button>
        <a className="brand" href="/">
          <span className="brandMark">AI</span>
          <span>
            Avibi Platform
          </span>
        </a>
        <nav className="platformPrimaryNav">
          <a className="platformSectionLink" href="/ai-assistant">✦　Trợ lý</a>
          <button className={page === "characters" || page === "discover" || page === "create" ? "active" : ""} onClick={() => setPage("characters")}>◉　Nhân vật</button>
        </nav>
        <nav className="platformSubNav">
          {(["home", "discover", "characters", "rooms"] as const).map(
            (p) => (
              <button
                className={page === p ? "active" : ""}
                onClick={() => {
                  setPage(p);
                }}
                key={p}
              >
                {
                  {
                    home: "⌂  Trang chủ",
                    discover: "⌕  Cộng đồng",
                    characters: "☺  Nhân vật của tôi",
                    create: "＋  Tạo nhân vật",
                    rooms: "▣  Cuộc trò chuyện",
                  }[p]
                }
              </button>
            ),
          )}
        </nav>
        <div className="sideTitle">Trò chuyện gần đây</div>
        {rooms.map((r) => (
          <div className="recentRoom" key={r.id}>
            <button className="roomLink" onClick={() => openRoom(r)}>
              {r.name}
            </button>
            <button
              className="deleteRoom"
              title="Xóa cuộc trò chuyện"
              aria-label={`Xóa ${r.name}`}
              onClick={() => deleteRoom(r)}
            >
              ×
            </button>
          </div>
        ))}
      </aside>
      <main>
        {page !== "chat" && (
          <div className="appTopbar">
            <label className="searchBox">
              <span>⌕</span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm nhân vật hoặc cuộc trò chuyện"
              />
            </label>
            {!window.location.search.includes("workspace=1") && <><button className="themeButton" onClick={toggleTheme}>
              {account.theme === "dark" ? "☀ Sáng" : "☾ Tối"}
            </button>
            <button
              className="accountButton"
              onClick={openSettings}
              title="Cài đặt cá nhân"
            >
              {account.avatar_url ? (
                <img src={API + account.avatar_url} alt="" />
              ) : (
                <span>{account.display_name[0]?.toUpperCase()}</span>
              )}
              <b>{account.display_name}</b>
              <small>Cài đặt</small>
            </button>
            </>}
          </div>
        )}
        {error && (
          <div className="error" onClick={() => setError("")}>
            {error} ×
          </div>
        )}
        {notice && (
          <div className="notice" role="status" aria-live="polite" onClick={() => setNotice("")}>
            {notice} ×
          </div>
        )}
        {page === "home" && (
          <>
            <header>
              <span className="eyebrow">KHÁM PHÁ NHÂN VẬT</span>
              <h1>Hôm nay bạn cần ai đồng hành?</h1>
              <p>
                Chọn một người phù hợp với tâm trạng, học tập hoặc công việc của
                bạn.
              </p>
            </header>
            <div className="actions">
              <button
                className="secondaryButton"
                onClick={() => setPage("rooms")}
              >
                Tạo phòng nhóm
              </button>
            </div>
            {!!systemHomeCharacters.length && (
              <section className="systemCharacterLane">
                <div className="laneHeading">
                  <h2>Nhân vật hệ thống</h2>
                  <span> </span>
                </div>
                <div className="marketRow">
                  {systemHomeCharacters.map((character) => (
                    <MarketCard
                      key={character.id}
                      character={character}
                      onOpen={() => addPreset(character)}
                    />
                  ))}
                </div>
              </section>
            )}
            {!!customHomeCharacters.length && (
              <section className="largeCharacterSection">
                <div className="laneHeading">
                  <h2>Nhân vật của bạn</h2>
                  <span> </span>
                </div>
                <div className="grid showcaseGrid">
                  {customHomeCharacters.map((character) => (
                    <button
                      className="card characterIntro showcaseCard"
                      key={character.id}
                      onClick={() => startCharacterChat(character)}
                    >
                      <CharacterAvatar
                        character={character}
                        className="showcaseImage"
                      />
                      <div className="showcaseCopy">
                        <span className="roleBadge companion">
                          {character.character_type || "Custom"}
                        </span>
                        <strong>{character.name}</strong>
                        <h3>{character.display_name || character.name}</h3>
                        <p>{character.description}</p>
                        <span className="showcaseMeta">
                          ◉ {character.usage_count || 0} người dùng{" "}
                          <b>Trò chuyện →</b>
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </section>
            )}
            {homeSections.map((section) => {
              const members = charactersForSection(section);
              if (!members.length) return null;
              return (
                <section className="largeCharacterSection" key={section.id}>
                  <div className="laneHeading">
                    <h2>{section.name}</h2>
                    <span></span>
                  </div>
                  <div className="grid showcaseGrid">
                    {members.map((character) => (
                      <CommunityShowcase
                        key={`${section.id}:${character.id}`}
                        character={character}
                        onOpen={() =>
                          character.creation_type === "preset"
                            ? addPreset(character)
                            : startPublicCharacter(character)
                        }
                      />
                    ))}
                  </div>
                </section>
              );
            })}
            <h2>Tiếp tục trò chuyện</h2>
            <div className="grid">
              {rooms
                .filter((r) => matchesSearch(r.name))
                .map((r) => (
                  <button
                    className="card"
                    key={r.id}
                    onClick={() => openRoom(r)}
                  >
                    {r.name}
                  </button>
                ))}
            </div>
          </>
        )}
        {page === "discover" && (
          <>
            <header>
              <span className="eyebrow">NHÂN VẬT CỘNG ĐỒNG</span>
              <h1>Khám phá nhân vật public</h1>
              <p>
                Tìm theo tên, loại hoặc thẻ; mỗi nhân vật hiển thị rõ người tạo.
              </p>
            </header>
            <div className="filterBar">
              <div className="publicFilterTabs">
                {publicCategories.map(([value, label]) => (
                  <button
                    key={value}
                    className={publicFilter === value ? "active" : ""}
                    onClick={() => setPublicFilter(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <span>{filteredPublicCharacters.length} nhân vật</span>
            </div>
            <div className="publicGrid">
              {filteredPublicCharacters.map((c) => (
                <article className="publicCard" key={c.id}>
                  {c.avatar_url ? (
                    <img src={assetUrl(c.avatar_url)} alt={c.name} />
                  ) : (
                    <div className="avatar publicAvatar">{c.name[0]}</div>
                  )}
                  <div className="publicBody">
                    <span className="roleBadge companion">
                      {c.character_type || "companion"}
                    </span>
                    <h3>{c.name}</h3>
                    <div className="creatorLine">
                      <small>
                        bởi {c.creator?.name || "Người dùng"} ·{" "}
                        {c.creator?.followers || 0} người theo dõi
                      </small>
                      <button
                        onClick={() =>
                          act(async () => {
                            await api(
                              `/v1/public/creators/${c.creator?.id}/follow`,
                              "PUT",
                              { following: true },
                            );
                            setNotice("Đã theo dõi người tạo");
                          })
                        }
                      >
                        Theo dõi
                      </button>
                    </div>
                    <div className="socialStats">
                      <span>
                        ★ {c.rating || "Mới"} ({c.rating_count || 0})
                      </span>
                      <span>◉ {c.usage_count || 0} người đã dùng</span>
                    </div>
                    <div className="reactionBar">
                      {["❤️", "😂", "🔥", "👍", "😮"].map((emoji) => (
                        <button
                          key={emoji}
                          onClick={() =>
                            act(async () => {
                              await api(
                                `/v1/characters/${c.id}/reaction`,
                                "PUT",
                                { reaction: emoji },
                              );
                              await refresh();
                            })
                          }
                        >
                          {emoji} {c.reactions?.[emoji] || ""}
                        </button>
                      ))}
                    </div>
                    <p>{c.description}</p>
                    <div className="tagRow">
                      {c.tags?.map((tag) => (
                        <span key={tag}>#{tag}</span>
                      ))}
                    </div>
                    <div className="ratingRow">
                      <small>Đánh giá:</small>
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() =>
                            act(async () => {
                              await api(
                                `/v1/public/characters/${c.id}/rating`,
                                "PUT",
                                { rating: star },
                              );
                              setNotice(`Đã đánh giá ${star} sao`);
                              await refresh();
                            })
                          }
                        >
                          {star}★
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() =>
                        act(async () => {
                          const cloned = await api<Character>(
                            `/v1/public/characters/${c.id}/clone`,
                            "POST",
                            {},
                          );
                          setChars((items) => [...items, cloned]);
                          setPage("characters");
                        })
                      }
                    >
                      Thêm vào nhân vật của tôi
                    </button>
                  </div>
                </article>
              ))}
            </div>
            {!filteredPublicCharacters.length && (
              <div className="emptyState">Chưa có nhân vật public phù hợp.</div>
            )}
          </>
        )}
        {page === "characters" && (
          <>
            <header className="collectionHeader">
              <div>
                <span className="eyebrow">AI ROLE PLAY</span>
                <h1>AI Role Play</h1>
                <p>Browse all your characters, find one to chat with, or create a new one.</p>
              </div>
            </header>
            <div className="collectionToolbar">
              <div className="tabs collectionTabs">
                <button className="active">{translateUiText("Nh\u00e2n v\u1eadt c\u1ee7a t\u00f4i", uiLanguage)} <span>{filteredMyCharacters.length}</span></button>
                <button onClick={() => { setSearch(""); setPublicFilter("all"); setPage("discover"); }}>{translateUiText("C\u1ed9ng \u0111\u1ed3ng", uiLanguage)}</button>
              </div>
              <div className="characterCreateActions">
                <button onClick={() => { setMode("preset"); setPage("create"); }}>{translateUiText("T\u1ea1o nh\u00e2n v\u1eadt", uiLanguage)}</button>
                <button className="secondaryButton" onClick={() => { setMode("mirror"); setPage("create"); }}>{translateUiText("T\u1ea1o b\u1ea3n sao", uiLanguage)}</button>
                <button className="secondaryButton" onClick={() => { setMode("custom"); setPage("create"); }}>{translateUiText("S\u00e1ng t\u1ea1o", uiLanguage)}</button>
              </div>
            </div>
            <div className="myCharacterFilters">
              <select value={myCharacterSourceFilter} onChange={(event) => setMyCharacterSourceFilter(event.target.value)} aria-label="Filter characters by source">
                <option value="all">{translateUiText("Tất cả nhân vật", uiLanguage)}</option>
                <option value="system">{translateUiText("Nhân vật hệ thống", uiLanguage)}</option>
                <option value="owned">{translateUiText("Nhân vật của bạn", uiLanguage)}</option>
              </select>
              <select value={myCharacterFilter} onChange={(event) => setMyCharacterFilter(event.target.value)} aria-label="Filter characters by visibility">
                <option value="all">{translateUiText("T\u1ea5t c\u1ea3", uiLanguage)}</option>
                <option value="private">{translateUiText("Ri\u00eang t\u01b0", uiLanguage)}</option>
                <option value="public">{translateUiText("C\u00f4ng khai", uiLanguage)}</option>
              </select>
              <select value={myCharacterTypeFilter} onChange={(event) => setMyCharacterTypeFilter(event.target.value)} aria-label="Filter characters by type">
                <option value="all">{translateUiText("T\u1ea5t c\u1ea3 lo\u1ea1i", uiLanguage)}</option>
                {myCharacterTypes.map((type) => <option value={type} key={type}>{type}</option>)}
              </select>
              <span>{filteredMyCharacters.length} {translateUiText("nh\u00e2n v\u1eadt", uiLanguage)}</span>
            </div>
            <div className="grid myCharacterGrid">
              {filteredMyCharacters.map(({ character: c, source }) => (
                  <article className="card myCharacterCard" key={`${source}:${c.id}`}>
                    <CharacterAvatar character={c} className="myCharacterCover" />
                    <strong>{c.name}</strong>
                    <small>
                      {source === "system" ? translateUiText("Nhân vật hệ thống", uiLanguage) : c.is_public ? "Công khai" : "Riêng tư"} ·{" "}
                      {catalogCharacterType(c)} · ◉ {c.usage_count || 0}{" "}
                      người dùng
                    </small>
                    {source === "owned" && <div className="reactionBar">
                      {["❤️", "😂", "🔥", "👍", "😮"].map((emoji) => (
                        <button
                          key={emoji}
                          onClick={() => act(() => reactCharacter(c.id, emoji))}
                        >
                          {emoji} {c.reactions?.[emoji] || ""}
                        </button>
                      ))}
                    </div>}
                    {c.simulation_label && <small>AI simulation</small>}
                    <p>{c.description}</p>
                    <button
                      disabled={busy}
                      onClick={() => source === "system" ? void addPreset(c) : void startCharacterChat(c)}
                    >
                      Trò chuyện
                    </button>
                    {source === "owned" && <button
                      className="link"
                      onClick={() => void openRoleplayMemories({ kind: "character", id: c.id, label: c.name })}
                    >
                      Ký ức
                    </button>}
                    {source === "owned" && <button
                      className="deleteCharacter"
                      disabled={busy}
                      onClick={() => {
                        if (
                          !window.confirm(
                            c.is_public
                              ? `Xóa nhân vật công khai “${c.name}”? Nhân vật sẽ biến mất khỏi cộng đồng và dữ liệu trò chuyện của bạn cũng bị xóa.`
                              : `Xóa nhân vật riêng tư “${c.name}” và dữ liệu trò chuyện liên quan?`,
                          )
                        )
                          return;
                        act(async () => {
                          await api(`/v1/characters/${c.id}`, "DELETE");
                          setChars((current) =>
                            current.filter((item) => item.id !== c.id),
                          );
                          setRooms((current) =>
                            current
                              .filter(
                                (item) =>
                                  !(
                                    item.character_ids.length === 1 &&
                                    item.character_ids[0] === c.id
                                  ),
                              )
                              .map((item) => ({
                                ...item,
                                character_ids: item.character_ids.filter(
                                  (id) => id !== c.id,
                                ),
                              })),
                          );
                        });
                      }}
                    >
                      {c.is_public
                        ? "Xóa nhân vật công khai"
                        : "Xóa nhân vật riêng tư"}
                    </button>}
                  </article>
                ))}
            </div>
          </>
        )}
        {page === "create" && (
          <>
            <header>
              <h1>Tạo nhân vật</h1>
              <p>
                Preset là điểm bắt đầu; nhân vật sẽ thân thiết dần qua trò
                chuyện.
              </p>
            </header>
            <div className="tabs">
              {[
                ["preset", "Có sẵn"],
                ["custom", "Tự sáng tạo"],
                ["mirror", "Bản sao của ai đó"],
              ].map(([k, v]) => (
                <button
                  className={mode === k ? "active" : ""}
                  onClick={() => setMode(k)}
                  key={k}
                >
                  {v}
                </button>
              ))}
              <button className={mode === "story" ? "active" : ""} onClick={() => setMode("story")}>
                Tạo từ truyện
              </button>
            </div>
            {mode === "preset" && (
              <div className="roleSections">
                {roleOrder.map((role) => {
                  const members = presets.filter(
                    (character) =>
                      character.category !== "entertainment" &&
                      character.support?.primary_role === role,
                  );
                  if (!members.length) return null;
                  return (
                    <section className="roleSection" key={role}>
                      <div className="roleTitle">
                        <h2>{roleLabels[role]}</h2>
                        <span>{members.length} nhân vật</span>
                      </div>
                      <div className="grid">
                        {members.map((p) => (
                          <article className="card roleCard" key={p.id}>
                            <CharacterAvatar character={p} />
                            <span className={`roleBadge ${role}`}>
                              {roleLabels[role]}
                            </span>
                            <strong>{p.name}</strong>
                            <p>{p.support?.introduction || p.description}</p>
                            {!!p.support?.strengths.length && (
                              <div className="strengths">
                                {p.support.strengths.map((item) => (
                                  <span key={item}>{roleLabels[item]}</span>
                                ))}
                              </div>
                            )}
                            <button
                              disabled={busy || hasPreset(p)}
                              onClick={() => addPreset(p)}
                            >
                              {hasPreset(p) ? "Đã thêm" : "Thêm nhân vật"}
                            </button>
                          </article>
                        ))}
                      </div>
                    </section>
                  );
                })}
                <section className="roleSection entertainmentSection">
                  <div className="roleTitle">
                    <h2>Giải trí</h2>
                    <span>3 nhân vật</span>
                  </div>
                  <div className="grid">
                    {presets
                      .filter((p) => p.category === "entertainment")
                      .map((p) => (
                        <article className="card roleCard" key={p.id}>
                          <CharacterAvatar character={p} />
                          <span className="roleBadge entertainment">
                            Giải trí
                          </span>
                          <strong>{p.name}</strong>
                          <p>{p.description}</p>
                          <div className="functionIntro">
                            {p.support?.introduction}
                          </div>
                          <button
                            disabled={busy || hasPreset(p)}
                            onClick={() => addPreset(p)}
                          >
                            {hasPreset(p) ? "Đã thêm" : "Thêm nhân vật"}
                          </button>
                        </article>
                      ))}
                  </div>
                </section>
              </div>
            )}
            {mode === "custom" && (
              <section className="form">
                <div className="characterCreateHead">
                  <label className="avatarPicker">
                    {avatarFile ? (
                      <img
                        src={URL.createObjectURL(avatarFile)}
                        alt="Avatar preview"
                      />
                    ) : (
                      <span>
                        ＋<small>Avatar</small>
                      </span>
                    )}
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/gif"
                      onChange={(e) =>
                        setAvatarFile(e.target.files?.[0] || null)
                      }
                    />
                  </label>
                  <div>
                    <h2>{name || "Nhân vật mới"}</h2>
                    <p>Thiết lập hồ sơ và quyền hiển thị của nhân vật.</p>
                  </div>
                </div>
                <label>
                  Tên nhân vật
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ví dụ: Linh"
                  />
                </label>
                <label>
                  Mô tả tính cách
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Linh hơi lạnh lúc đầu, hài hước khi thân, thích âm nhạc..."
                  />
                  <small>
                    {description.length.toLocaleString()} ký tự
                    {description.length > 6000
                      ? " · AI sẽ tóm tắt có cấu trúc trước khi tạo nhân vật"
                      : ""}
                  </small>
                </label>
                <label className="publishToggle mediaCharacterToggle">
                  <span>
                    <b>Đây là nhân vật trong phim hoặc hoạt hình?</b>
                    <small>
                      AI sẽ nghiên cứu nguồn công khai rồi kết hợp với mô tả của
                      bạn.
                    </small>
                  </span>
                  <input
                    type="checkbox"
                    checked={existingMediaCharacter}
                    onChange={(e) =>
                      setExistingMediaCharacter(e.target.checked)
                    }
                  />
                </label>
                {existingMediaCharacter && (
                  <div className="mediaCharacterFields">
                    <label>
                      Tên nhân vật
                      <input
                        value={mediaCharacterName}
                        onChange={(e) => setMediaCharacterName(e.target.value)}
                        placeholder="Ví dụ: Tony Stark, Gojo Satoru..."
                      />
                    </label>
                    <label>
                      Tên phim / hoạt hình <small>(không bắt buộc)</small>
                      <input
                        value={mediaTitle}
                        onChange={(e) => setMediaTitle(e.target.value)}
                        placeholder="Ví dụ: Iron Man, Jujutsu Kaisen..."
                      />
                    </label>
                    <p>
                      Agent chỉ dùng nguồn công khai làm dữ kiện tham khảo. Mô
                      tả của bạn vẫn được ưu tiên khi tạo phiên bản role play.
                    </p>
                  </div>
                )}
                <label>
                  Vai trò của nhân vật
                  <input
                    value={customRole}
                    onChange={(e) => setCustomRole(e.target.value)}
                    placeholder="Ví dụ: bạn học, đồng nghiệp, người bạn thân..."
                  />
                </label>
                <div className="formColumns">
                  <label>
                    Loại nhân vật
                    <select
                      value={characterType}
                      onChange={(e) => setCharacterType(e.target.value)}
                    >
                      <option value="companion">Đồng hành</option>
                      <option value="study">Học tập</option>
                      <option value="work">Công việc</option>
                      <option value="entertainment">Giải trí</option>
                      <option value="romance">Tình cảm</option>
                      <option value="roleplay">Role play</option>
                    </select>
                  </label>
                </div>
                <label>
                  Tags <small>Chọn tối đa 8 tags</small>
                  <div className="tagPicker">
                    <input
                      value={tagSearch}
                      onChange={(e) => setTagSearch(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && tagSearch.trim()) {
                          e.preventDefault();
                          toggleTag(tagSearch.trim());
                          setTagSearch("");
                        }
                      }}
                      placeholder="Tìm hoặc nhập tag rồi nhấn Enter"
                    />
                    <div className="selectedTags">
                      {selectedTags.map((tag) => (
                        <button
                          type="button"
                          key={tag}
                          onClick={() => toggleTag(tag)}
                        >
                          #{tag} ×
                        </button>
                      ))}
                    </div>
                    <div className="tagOptions">
                      {suggestedTags
                        .filter((tag) =>
                          tag.toLowerCase().includes(tagSearch.toLowerCase()),
                        )
                        .map((tag) => (
                          <button
                            type="button"
                            className={
                              selectedTags.includes(tag) ? "selected" : ""
                            }
                            key={tag}
                            onClick={() => toggleTag(tag)}
                          >
                            {selectedTags.includes(tag) ? "✓" : "＋"} {tag}
                          </button>
                        ))}
                    </div>
                  </div>
                </label>
                <label className="publishToggle">
                  <span>
                    <b>Công khai nhân vật</b>
                    <small>
                      Cho phép mọi người tìm thấy và thêm một bản sao.
                    </small>
                  </span>
                  <input
                    type="checkbox"
                    checked={makePublic}
                    onChange={(e) => setMakePublic(e.target.checked)}
                  />
                </label>
                <label>
                  Bối cảnh trò chuyện <small>(không bắt buộc)</small>
                  <textarea
                    value={customScenario}
                    onChange={(e) => setCustomScenario(e.target.value)}
                    placeholder="Hai người quen nhau thế nào, đang ở đâu, mối quan hệ hiện tại..."
                  />
                </label>
                <label>
                  Lời chào đầu tiên <small>(không bắt buộc)</small>
                  <textarea
                    value={customGreeting}
                    onChange={(e) => setCustomGreeting(e.target.value)}
                    placeholder="Câu đầu tiên nhân vật nói khi bắt đầu chat"
                  />
                </label>
                <label>
                  Ví dụ cách nói <small>(mỗi câu một dòng)</small>
                  <textarea
                    value={customExamples}
                    onChange={(e) => setCustomExamples(e.target.value)}
                    placeholder={
                      "Ví dụ:\nÊ, hôm nay thế nào?\nKể tiếp đi, tới đoạn hay rồi."
                    }
                  />
                </label>
                <button
                  disabled={busy || description.length < 3}
                  onClick={() =>
                    act(async () => {
                      const character = await api<Character>(
                        "/v1/characters/generate",
                        "POST",
                        {
                          name,
                          description,
                          role: customRole,
                          scenario: customScenario,
                          initial_greeting: customGreeting,
                          dialogue_examples: customExamples
                            .split("\n")
                            .map((item) => item.trim())
                            .filter(Boolean)
                            .slice(0, 8),
                          existing_media_character: existingMediaCharacter,
                          media_character_name: mediaCharacterName,
                          media_title: mediaTitle,
                        },
                      );
                      await finishCreatedCharacter(character);
                    }, true)
                  }
                >
                  Tạo bằng AI
                </button>
              </section>
            )}
            {mode === "story" && (
              <section className="form storyCharacterForm">
                <h2>Tạo nhân vật từ truyện</h2>
                <p>Tải truyện lên hoặc nhập link. Hệ thống sẽ đọc nội dung, tìm nhân vật trong truyện, rồi tạo tính cách và cách nói dựa trên các đoạn có nhân vật đó.</p>
                <label>
                  Tải file truyện (.txt, .md, .pdf, .docx)
                  <input type="file" accept=".txt,.md,.pdf,.docx,.pptx" onChange={(event) => setStoryFile(event.target.files?.[0] || null)} />
                </label>
                <label>
                  Hoặc dán link truyện
                  <input type="url" value={storyUrl} onChange={(event) => setStoryUrl(event.target.value)} placeholder="https://..." />
                </label>
                <button disabled={busy || (!storyFile && !storyUrl.trim())} onClick={() => act(prepareStorySource, true, "Đã đọc truyện. Chọn nhân vật muốn tạo.")}>Tải lên và tìm nhân vật</button>
                {storyDocument && (
                  <>
                    <p>Nguồn: {storyDocument.filename}. Chọn một nhân vật được tìm thấy hoặc nhập tên có trong truyện.</p>
                    {storyCandidates.map((candidate) => (
                      <button type="button" key={candidate.name} className={`card storyCandidate ${storyCharacterName === candidate.name ? "selected" : ""}`} onClick={() => setStoryCharacterName(candidate.name)}>
                        <strong>{candidate.name}</strong>
                        <span>{candidate.description}</span>
                        {!!candidate.source_evidence.length && <small>Trích dẫn: {candidate.source_evidence.slice(0, 2).join(" · ")}</small>}
                      </button>
                    ))}
                    {!storyCandidates.length && <p>Chưa tự tìm thấy nhân vật. Hãy nhập tên nhân vật xuất hiện trong truyện.</p>}
                    <label>Tên nhân vật trong truyện<input value={storyCharacterName} onChange={(event) => setStoryCharacterName(event.target.value)} placeholder="Tên nhân vật" /></label>
                    <button disabled={busy || !storyCharacterName.trim()} onClick={() => act(createStoryCharacter, true, "Đã tạo nhân vật từ truyện.")}>Tạo nhân vật từ truyện</button>
                  </>
                )}
              </section>
            )}
            {mode === "mirror" && (
              <section className="form">
                <p>
                  Tạo một phiên bản AI mô phỏng nhân vật. Nếu nhập ngày sinh, hệ
                  thống sẽ bổ sung kiến thức cung hoàng đạo mang tính tham khảo.
                </p>
                <label>
                  Tên nhân vật
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ví dụ: Minh Anh"
                  />
                </label>
                <label>
                  Ngày tháng năm sinh <small>(không bắt buộc)</small>
                  <input
                    type="date"
                    value={birthDate}
                    onChange={(e) => setBirthDate(e.target.value)}
                  />
                </label>
                <label>
                  Mô tả nhân vật
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Tính cách, sở thích, cách nói chuyện và cách họ phản ứng khi vui, buồn hoặc bất đồng..."
                  />
                </label>
                <label>
                  Lời giới thiệu đầu tiên
                  <textarea
                    value={introduction}
                    onChange={(e) => setIntroduction(e.target.value)}
                    placeholder="Ví dụ: Chào bạn, mình là Minh Anh. Hôm nay bạn thế nào?"
                  />
                </label>
                <button
                  disabled={
                    busy || !name.trim() || description.trim().length < 3
                  }
                  onClick={createMirror}
                >
                  {busy ? "Đang tạo..." : "Tạo phiên bản AI"}
                </button>
              </section>
            )}
          </>
        )}
        {page === "rooms" && (
          <>
            <header>
              <h1>Tạo phòng chat</h1>
              <p>
                Chọn một nhân vật để chat riêng, hoặc 2–6 nhân vật để chat nhóm.
              </p>
            </header>
            <div className="grid">
              {chars.map((c) => (
                <button
                  key={c.id}
                  className={
                    "card " + (selected.includes(c.id) ? "selected" : "")
                  }
                  onClick={() =>
                    setSelected((s) =>
                      s.includes(c.id)
                        ? s.filter((x) => x !== c.id)
                        : s.length < 6
                          ? [...s, c.id]
                          : s,
                    )
                  }
                >
                  <div className="avatar">{c.name[0]}</div>
                  <strong>{c.display_name || c.name}</strong>
                </button>
              ))}
            </div>
            <div className="bottom">
              <span>Đã chọn {selected.length} nhân vật</span>
              <button
                disabled={!selected.length || busy}
                onClick={() =>
                  act(async () => {
                    const r = await api<Room>("/v1/rooms", "POST", {
                      character_ids: selected,
                    });
                    setSelected([]);
                    await openRoom(r);
                  })
                }
              >
                Bắt đầu chat
              </button>
            </div>
          </>
        )}
        {page === "chat" && room && (
          <div
            className={`chatWorkspace ${chatToolsCollapsed ? "toolsCollapsed" : ""}`}
          >
            <div className="chat">
              <header
                key={`emotion-header-${activeExpression}`}
                className={`chatEmotionHeader emotion-${activeExpression} ${roomChars.length === 1 ? "singleCharacter" : "groupChatHeader"}`}
              >
                {roomChars.length === 1 && (
                  <EmotionPortrait
                    characterId={roomChars[0].id}
                    emotion={activeExpression}
                    name={roomChars[0].name}
                  />
                )}
                <h1>{room.name}</h1>
                <p>{roomChars.map((c) => c.name).join(" · ")}</p>
              </header>
              <div className="messages" ref={messagesBox}>
                {messages.map((m, messageIndex) => {
                  const author = chars.find((c) => c.id === m.character_id);
                  const isLatestCharacter =
                    messageIndex ===
                    messages
                      .map((item) => item.sender_type)
                      .lastIndexOf("character");
                  return (
                    <div
                      key={m.id}
                      className={
                        "messageBlock " +
                        (m.sender_type === "user" ? "mineBlock" : m.sender_type === "character" ? "characterBlock" : "")
                      }
                    >
                      {m.sender_type === "character" && author && <CharacterAvatar character={author} className="chatMessageAvatar" />}
                      {m.sender_type === "document" && m.attachment ? (
                        <div
                          className={`documentMessage ${m.attachment.status}`}
                        >
                          <div className="documentIcon">📄</div>
                          <div>
                            <strong>{m.attachment.filename}</strong>
                            <span>
                              {m.attachment.status === "ready"
                                ? "Đã gửi"
                                : m.attachment.status === "failed"
                                  ? "Lỗi!"
                                  : "Đang gửi…"}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div
                          className={
                            "bubble " + (m.sender_type === "user" ? "mine" : "")
                          }
                        >
                          {m.sender_type === "character" && author && !m.id.startsWith("local-") && (
                            <button
                              type="button"
                              className={`roleplaySpeakButton ${speakingId === m.id ? "playing" : ""}`}
                              onClick={() => void playRoleplayMessage(m.id)}
                              aria-label={`${speakingId === m.id || speechLoadingId === m.id ? "Dừng" : "Nghe"} giọng ${author.name}`}
                              aria-pressed={speakingId === m.id}
                              title={speakingId === m.id ? "Dừng phát" : "Phát bằng TTS"}
                            >{speechLoadingId === m.id ? "◌ Đang tạo" : speakingId === m.id ? "■ Dừng" : "▶ Nghe"}</button>
                          )}
                          <small>
                            {m.sender_type === "user"
                              ? "Bạn"
                              : author?.name}
                          </small>
                          <div data-no-translate="true" translate="no">{renderRoleplayText(m.text, m.sender_type === "character")}</div>
                          {m.interrupted && <p className="chatInterrupted">Câu trả lời bị gián đoạn. Hãy thử gửi lại.</p>}
                          {m.sender_type === "character" &&
                            !m.id.startsWith("local-") && (
                              <button
                                className="regenerate"
                                disabled={busy}
                                onClick={() => regenerateMessage(m)}
                              >
                                ↻ Trả lời khác
                              </button>
                            )}
                          {!!m.sources?.length && (
                            <details>
                              <summary>Nguồn ({m.sources.length})</summary>
                              {m.sources.map((s, i) => (
                                <p key={i}>{s.document_id}</p>
                              ))}
                            </details>
                          )}
                        </div>
                      )}
                      {isLatestCharacter && !!m.suggestions?.length && (
                        <div className="suggestions">
                          {m.suggestions.map((suggestion) => (
                            <button
                              key={suggestion}
                              disabled={busy}
                              onClick={() => send(suggestion)}
                              data-no-translate="true"
                              translate="no"
                            >
                              {suggestion} ›
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
                {typingIds.map((id) => (
                  <div className="typingBubble" key={"typing-" + id} role="status" aria-label={`${chars.find((c) => c.id === id)?.name || "Nhân vật"} đang nhập`}>
                    {chars.find((c) => c.id === id) && <CharacterAvatar character={chars.find((c) => c.id === id)!} className="chatTypingAvatar" />}
                    <div className="typingDots">
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                ))}
                <div ref={messagesEnd} />
              </div>
              <div className="composer">
                <div className="mentions">
                  {text.includes("@") &&
                    roomChars.map((c) => (
                      <button
                        key={c.id}
                        onClick={() =>
                          setText(text.replace(/@[^\s]*$/, `@${c.name} `))
                        }
                      >
                        @{c.name}
                      </button>
                    ))}
                </div>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  placeholder="Nhắn gì đó... Gõ @ để gọi nhân vật"
                />
                <div>
                  <select
                    value={speaker}
                    onChange={(e) => setSpeaker(e.target.value)}
                  >
                    <option value="auto">Tự chọn</option>
                    {roomChars.map((c) => (
                      <option key={c.id} value={"character:" + c.id}>
                        {c.name}
                      </option>
                    ))}
                    {roomChars.length > 1 && (
                      <option value="everyone">Mọi người</option>
                    )}
                  </select>
                  <button
                    disabled={busy || !text.trim()}
                    onClick={() => send()}
                  >
                    Gửi →
                  </button>
                </div>
              </div>
            </div>
            <aside className="characterTools">
              <button
                className="collapseTools"
                onClick={() => setChatToolsCollapsed((value) => !value)}
              >
                {chatToolsCollapsed ? "‹" : "›"}
              </button>
              {!chatToolsCollapsed && (
                <>
                  {roomChars.length === 1 && (
                    <div className="toolProfile">
                      <div className="toolProfileArtwork">
                        <CharacterAvatar
                          character={roomChars[0]}
                          className="toolAvatar"
                        />
                      </div>
                      <div>
                        <strong>{roomChars[0].name}</strong>
                        <small>
                          {roomChars[0].support?.introduction ||
                            roomChars[0].description}
                        </small>
                        <span>
                          ◉ {roomChars[0].usage_count || 0} người dùng
                        </span>
                      </div>
                    </div>
                  )}
                  <div className="toolReactions">
                    {roomChars.length === 1 &&
                      ["❤️", "😂", "🔥", "👍", "😮"].map((emoji) => (
                        <button
                          key={emoji}
                          onClick={() =>
                            act(() => reactCharacter(roomChars[0].id, emoji))
                          }
                        >
                          {emoji}
                          <small>{roomChars[0].reactions?.[emoji] || 0}</small>
                        </button>
                      ))}
                  </div>
                  <button
                    className="newChatTool"
                    onClick={() =>
                      roomChars.length &&
                      act(async () => {
                        const next = await api<Room>("/v1/rooms", "POST", {
                          name: `Trò chuyện với ${roomChars.map((c) => c.name).join(", ")}`,
                          character_ids: roomChars.map((c) => c.id),
                        });
                        await openRoom(next);
                      })
                    }
                  >
                    ＋ Cuộc trò chuyện mới
                  </button>
                  <div className="toolMenu">
                    <button onClick={() => setPage("rooms")}>
                      <span>◷</span>
                      <b>Lịch sử trò chuyện</b>
                      <i>›</i>
                    </button>
                    <button
                      onClick={() => {
                        if (roomChars.length > 1 && room) void openRoleplayMemories({ kind: "room", id: room.id, label: room.name });
                        else if (roomChars[0]) void openRoleplayMemories({ kind: "character", id: roomChars[0].id, label: roomChars[0].name });
                      }}
                    >
                      <span>♟</span>
                      <b>Ký ức</b>
                      <i>›</i>
                    </button>
                    <button onClick={() => setPage("characters")}>
                      <span>✦</span>
                      <b>Thông tin nhân vật</b>
                      <i>›</i>
                    </button>
                    <button onClick={openSettings}>
                      <span>⚙</span>
                      <b>Tùy chỉnh</b>
                      <i>›</i>
                    </button>
                  </div>
                </>
              )}
            </aside>
          </div>
        )}
        {page === "memories" && (
          <>
            <header>
              <h1>{memoryTarget?.label || name} nhớ gì?</h1>
              <p>Thêm, chỉnh sửa, ghim hoặc xóa ký ức cho {memoryTarget?.kind === "room" ? "phòng trò chuyện này" : "nhân vật này"}.</p>
            </header>
            <section className="form memoryCreateForm">
              <label>
                Ký ức mới
                <textarea
                  value={memoryDraft}
                  maxLength={1000}
                  onChange={(event) => setMemoryDraft(event.target.value)}
                  placeholder="Ví dụ: Mình thích uống cà phê ít đường vào buổi sáng."
                />
              </label>
              <button disabled={busy || !memoryTarget || !memoryDraft.trim()} onClick={() => void act(addRoleplayMemory)}>
                Lưu ký ức
              </button>
            </section>
            {!memories.length && <p>Chưa có ký ức nào. Hãy nhập một điều bạn muốn nhân vật nhớ.</p>}
            {memories.map((m) => (
              <article className="card memory" key={m.id}>
                <textarea
                  value={m.content}
                  onChange={(e) =>
                    setMemories((s) =>
                      s.map((x) =>
                        x.id === m.id ? { ...x, content: e.target.value } : x,
                      ),
                    )
                  }
                />
                <button
                  onClick={() =>
                    act(async () => {
                      await api(`/v1/memories/${m.id}`, "PATCH", {
                        content: m.content,
                        pinned: m.pinned,
                      });
                    })
                  }
                >
                  Lưu
                </button>
                <button
                  onClick={() =>
                    act(async () => {
                      await api(`/v1/memories/${m.id}`, "PATCH", {
                        pinned: !m.pinned,
                      });
                      setMemories((s) =>
                        s.map((x) =>
                          x.id === m.id ? { ...x, pinned: !x.pinned } : x,
                        ),
                      );
                    })
                  }
                >
                  {m.pinned ? "Bỏ ghim" : "Ghim"}
                </button>
                <button
                  onClick={() =>
                    act(async () => {
                      await api(`/v1/memories/${m.id}`, "DELETE");
                      setMemories((s) => s.filter((x) => x.id !== m.id));
                    })
                  }
                >
                  Xóa
                </button>
              </article>
            ))}
          </>
        )}
      </main>
    </div>
  );
}
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
createRoot(document.getElementById("root")!).render(
  rolePlayRoute && internalWorkspaceRoute ? <RolePlayApp /> : assistantRoute && internalWorkspaceRoute ? <AssistantApp /> : <AssistantHome />,
);
