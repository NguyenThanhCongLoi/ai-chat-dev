import { roomCharacterPool } from "./roomCharacterPool";
import { openingVoiceMessages } from "./openingVoiceMessages";
import { CharacterFeelings } from "./CharacterFeelings";
import {
  useActionSounds,
  prepareActionSounds,
  activateActionSounds,
} from "./useActionSounds";
import {
  prepareRoomReactions,
  warmReactionClips,
  isReactionPreparationCancelled,
} from "./reactionCache";
import { useReactionSounds } from "./useReactionSounds";
import { canSpeak, playbackMessage, shouldAutoplaySpeech } from "./voicePreferences";
import { BackgroundSpeech } from "./backgroundSpeech";
import { useBackgroundMusic } from "./useBackgroundMusic";
import { BackgroundMusicButton } from "./BackgroundMusicButton";
import { RoleplayStoryHero } from "./RoleplayStoryHero";
import {
  afterUiLanguagePaint,
  loadCharacterIntroductions,
  loadCompleteUiTranslations,
  setUiLanguageGate,
  uiLanguageErrorMessage,
} from "../uiLocales";
import { reportFirstChunk } from "../chatTiming";
import { AutoGrowTextarea, Icon, formatStarText } from "../ui";
import { EmojiPicker } from "../EmojiPicker";
import {
  type ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { RolePlayLoadingCat } from "./RolePlayLoadingCat";
import { PcmStreamPlayer, playSseSpeech } from "./streamSpeech";
import { flushSync } from "react-dom";
import type { Character, Message, Account } from "./types";
import { API, api, authHeaders, responseError } from "./api";
import {
  EmotionPortrait,
  expressionPortraitCache,
  loadExpressionPortrait,
} from "./EmotionPortrait";
import {
  MarketCard,
  ReactionSummary,
  reactionEmojis,
  CharacterAvatar,
  CommunityShowcase,
  reactionTotal,
  assetUrl,
} from "./CharacterCards";
import {
  localizeInterface,
  rememberLanguage,
  restoredLanguage,
  setRuntimeTranslations,
  storedLanguage,
  supportedUiLanguage,
  UI_LANGUAGES,
  type UiLanguage,
} from "../i18n";

type Room = {
  topic?: string;
  id: string;
  name: string;
  character_ids: string[];
  created_at?: string;
  created?: boolean;
  is_public?: boolean;
};
type StoryCandidate = {
  name: string;
  description: string;
  source_evidence: string[];
  importance: number;
};
type HomeSection = {
  id: string;
  name: string;
  rule: "popular" | "trending" | "top_rated" | "favorites" | "tags";
  tags: string[];
};
function renderRoleplayText(text: string, isCharacter: boolean): ReactNode {
  if (!isCharacter) return text;
  const normalized = text
    .replace(/\\r\\n|\\n|\\r/g, "\n")
    .split("\n")
    .filter((line) => line.trim() !== "*")
    .join("\n")
    .trim()
    .replace(/(^|\n)([ \t]*)\*([^*\n]{1,240})\*(?=[ \t]|\n|$)/g, "$1$2**$3**");
  return formatStarText(normalized, "roleplay");
}
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
const roleLabels = {
  companion: "Đồng hành",
  study: "Học tập",
  work: "Công việc",
  health: "Sức khỏe",
  lifestyle: "Lối sống",
} as const;
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
export default function RolePlayApp() {
  const [uiLanguage, setUiLanguage] = useState<UiLanguage>(storedLanguage);
  const [, setTranslationRevision] = useState(0);
  const [languageAttempt, setLanguageAttempt] = useState(0);
  const [appliedLanguage, setAppliedLanguage] = useState<UiLanguage | null>(
    null,
  );
  const [resourcePreparing, setResourcePreparing] = useState(false);
  const [page, setPage] = useState<
    | "home"
    | "discover"
    | "system"
    | "characters"
    | "create"
    | "rooms"
    | "chat"
    | "memories"
  >(() => {
    const requested = new URLSearchParams(window.location.search).get("view");
    return [
      "home",
      "discover",
      "system",
      "characters",
      "create",
      "rooms",
      "chat",
      "memories",
    ].includes(requested || "")
      ? (requested as
          | "home"
          | "discover"
          | "system"
          | "characters"
          | "create"
          | "rooms"
          | "chat"
          | "memories")
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
  const [introTranslations, setIntroTranslations] = useState<
    Record<string, string>
  >({});
  const [catalogReady, setCatalogReady] = useState(false);
  const introSources = [
    ...new Set(
      [...chars, ...presets, ...publicCharacters]
        .flatMap((item) => [
          item.support?.introduction || "",
          item.description,
          item.initial_greeting || "",
        ])
        .filter(Boolean),
    ),
  ];
  const introSignature = JSON.stringify(introSources);
  const introText = (value: string) => introTranslations[value] || value;
  const [tagSearch, setTagSearch] = useState("");
  const [publicFilter, setPublicFilter] = useState("all");
  const [myCharacterFilter, setMyCharacterFilter] = useState("all");
  const [myCharacterTypeFilter, setMyCharacterTypeFilter] = useState("all");
  const [typingIds, setTypingIds] = useState<string[]>([]);
  const [speechLoadingId, setSpeechLoadingId] = useState<string | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const reactionSounds = useReactionSounds(
    page === "chat" ? room?.id || null : null,
    account?.id,
    room?.character_ids || [],
  );
  const actionSounds = useActionSounds(
    page === "chat" ? room?.id || null : null,
    account?.id,
    reactionSounds.enabled,
  );
  useEffect(() => {
    if (account?.id) void prepareActionSounds(account.id).catch(() => {});
  }, [account?.id]);
  const backgroundMusic = useBackgroundMusic(
    Boolean(account) &&
      ["home", "characters", "system", "discover", "chat"].includes(page),
    Boolean(speakingId),
    page === "chat" ? room?.id || null : null,
  );
  const speechAbortRef = useRef<AbortController | null>(null);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const speechStreamRef = useRef<PcmStreamPlayer | null>(null);
  const speechUrlRef = useRef<string | null>(null);
  const speechQueueRef = useRef<string[]>([]);
  const primedSpeechPlayerRef = useRef<PcmStreamPlayer | null>(null);
  const speechMessagesRef = useRef(messages);
  speechMessagesRef.current = messages;
  const automaticSpeechMessages = useRef(new Map<string, Message>());
  const [activeExpression, setActiveExpression] =
    useState<NonNullable<Message["emotion"]>>("neutral");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false),
    [chatToolsCollapsed, setChatToolsCollapsed] = useState(
      () => window.matchMedia("(max-width: 820px)").matches,
    );
  const messagesEnd = useRef<HTMLDivElement>(null);
  const messagesBox = useRef<HTMLDivElement>(null);
  const activeRoomIdRef = useRef<string | null>(null);
  const workspaceInitialRoomRef = useRef("");
  const rolePlayStreamRef = useRef<AbortController | null>(null);
  const rolePlayStreams = useRef(new Set<AbortController>());
  const rolePlayStreamSequence = useRef(0);
  function stopRoleplayAudio(clearQueue = true) {
    if (clearQueue) {
      speechQueueRef.current = [];
      primedSpeechPlayerRef.current?.stop();
      primedSpeechPlayerRef.current = null;
      automaticSpeechMessages.current.clear();
      openingSpeechIdsRef.current.clear();
      reactionMetadataRef.current.clear();
    }
    speechAbortRef.current?.abort();
    speechAbortRef.current = null;
    speechStreamRef.current?.stop();
    speechStreamRef.current = null;
    const audio = speechAudioRef.current;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      speechAudioRef.current = null;
    }
    if (speechUrlRef.current) {
      URL.revokeObjectURL(speechUrlRef.current);
      speechUrlRef.current = null;
    }
    setSpeechLoadingId(null);
    setSpeakingId(null);
  }
  const [backgroundSpeech] = useState(() => new BackgroundSpeech());
  const playingCharacterRef = useRef<string | null>(null);
  const greetingSpeechRef = useRef<Message | null>(null);
  const openingSpeechIdsRef = useRef(new Set<string>());
  const reactionMetadataRef = useRef(new Map<string, {emotion:string;language?:string;voiceId?:string}>());
  const openingGreetingVersion = useRef(0);
  const [openingGreeting, setOpeningGreeting] = useState<{
    roomId: string;
    messages: Message[];
  } | null>(null);
  const volumeFor = (id: string) =>
    chars.find((item) => item.id === id)?.tts_volume ?? 0.8;
  useEffect(() => {
    const id = playingCharacterRef.current;
    if (!id) return;
    const volume = volumeFor(id);
    speechStreamRef.current?.setVolume(volume);
  }, [chars]);
  const speechPreparationScope = useRef("");
  speechPreparationScope.current = (account?.id || "") + ":" + uiLanguage;
  function prepareRoleplaySpeech(message: Message, incremental = false, autoplay = true) {
    if (!account || !message.text || !canSpeak(message)) return;
    const scope = speechPreparationScope.current;
    const version = scope + ":" + (incremental ? "incremental:" + message.id : message.text);
    void backgroundSpeech
      .prepare(message.id, version, () =>
        fetch(
          API +
            "/v1/roleplay/messages/" +
            encodeURIComponent(message.id) +
            "/speech/stream",
          {
            method: "POST",
            headers: authHeaders(),
            signal: AbortSignal.timeout(180000),
          },
        ),
      )
      .then(() => {
        if (speechPreparationScope.current !== scope) return;
        setMessages((current) =>
          current.map((item) =>
            item.id === message.id && item.text === message.text
              ? { ...item, speech_ready: true, speech_error: "" }
              : item,
          ),
        );
      })
      .catch((error) => {
        if (speechPreparationScope.current !== scope) return;
        setMessages((current) =>
          current.map((item) =>
            item.id === message.id && item.text === message.text
              ? { ...item, speech_ready: false, speech_error: String(error) }
              : item,
          ),
        );
      });
    if (autoplay && shouldAutoplaySpeech(room?.character_ids.length || 0)) {
      automaticSpeechMessages.current.set(message.id, message);
      queueRoleplaySpeech(message.id);
    }
  }
  useEffect(
    () => () => {
      speechPreparationScope.current = "";
    },
    [],
  );
  const voiceCacheScope = JSON.stringify(
    chars.map((item) => [
      item.id,
      item.tts_voice_id,
      item.tts_voice_mode,
      item.tts_voice_vi,
      item.tts_voice_en,
      item.tts_languages,
      item.tts_gender,
    ]),
  );
  useEffect(() => {
    backgroundSpeech.clear();
  }, [account?.id, uiLanguage, voiceCacheScope]);
  function playNextQueuedSpeech() {
    const next = speechQueueRef.current.shift();
    if (next) void startRoleplayAudio(next, true);
  }
  function queueRoleplaySpeech(messageId: string) {
    if (!shouldAutoplaySpeech(room?.character_ids.length || 0)) return;
    speechQueueRef.current.push(messageId);
    if (
      !speechAbortRef.current &&
      !speechAudioRef.current &&
      !speechStreamRef.current
    )
      playNextQueuedSpeech();
  }
  async function startRoleplayAudio(messageId: string, automatic = false) {
    if (automatic && !shouldAutoplaySpeech(room?.character_ids.length || 0)) return;
    if (!automatic) {
      ++openingGreetingVersion.current;
      reactionSounds.stop();
      setOpeningGreeting(null);
    }

    setError("");
    const selected = playbackMessage(
      messageId, automatic, speechMessagesRef.current,
      automaticSpeechMessages.current.get(messageId), greetingSpeechRef.current,
    );
    if (selected && !canSpeak(selected)) return;
    playingCharacterRef.current = selected?.character_id || null;
    const playbackVolume = selected?.character_id
      ? volumeFor(selected.character_id)
      : 0.8;
    const playbackStartedAt = performance.now();
    const controller = new AbortController();
    speechAbortRef.current = controller;
    setSpeechLoadingId(messageId);
    const player = primedSpeechPlayerRef.current || new PcmStreamPlayer();
    primedSpeechPlayerRef.current = null;
    speechStreamRef.current = player;
    player.setVolume(playbackVolume);
    player.activate();
    const reportListen = () => {
      void fetch(
        `${API}/v1/roleplay/messages/${encodeURIComponent(messageId)}/listen`,
        {
          method: "POST",
          headers: { ...authHeaders(), "Content-Type": "application/json" },
          body: JSON.stringify({
            automatic,
            latency_ms: Math.round(performance.now() - playbackStartedAt),
          }),
        },
      ).catch(() => {});
    };
    try {
      if (automatic && selected?.character_id && !openingSpeechIdsRef.current.has(messageId)) {
        // Audio preparation already runs in parallel. Hold playback only.
        const reaction = reactionMetadataRef.current.get(messageId);
        await reactionSounds.react(messageId, selected.character_id,
          reaction?.emotion || selected.emotion || "neutral",
          reaction?.language || selected.speech_languages?.[0], reaction?.voiceId);
        if (controller.signal.aborted || speechAbortRef.current !== controller) return;
      }
      const firstAudio = () => {
        if (controller.signal.aborted || speechAbortRef.current !== controller)
          return;
        setSpeechLoadingId(null);
        setSpeakingId(messageId);
        reportListen();
      };
      // Subscribe to existing preparation: replay received PCM immediately.
      const prepared = await backgroundSpeech.play(
        messageId,
        controller.signal,
        player,
        firstAudio,
      );
      if (controller.signal.aborted || speechAbortRef.current !== controller)
        return;
      if (prepared && "played" in prepared) {
        stopRoleplayAudio(false);
        playNextQueuedSpeech();
        return;
      }
      let blob: Blob;
      if (prepared && "blob" in prepared) blob = prepared.blob;
      else {
        const response = await fetch(
          `${API}/v1/roleplay/messages/${encodeURIComponent(messageId)}/speech/stream`,
          {
            method: "POST",
            headers: authHeaders(),
            signal: controller.signal,
          },
        );
        if (!response.ok) throw new Error(await responseError(response));
        if (controller.signal.aborted || speechAbortRef.current !== controller)
          return;
        const contentType = (
          response.headers.get("content-type") || ""
        ).toLowerCase();
        if (contentType.startsWith("text/event-stream")) {
          await playSseSpeech(response, controller.signal, player, firstAudio);
          if (
            controller.signal.aborted ||
            speechAbortRef.current !== controller
          )
            return;
          stopRoleplayAudio(false);
          playNextQueuedSpeech();
          return;
        }
        if (!contentType.startsWith("audio/"))
          throw new Error("Gateway không trả về âm thanh.");
        blob = await response.blob();
      }
      if (controller.signal.aborted || speechAbortRef.current !== controller)
        return;
      const url = URL.createObjectURL(blob);
      speechUrlRef.current = url;
      const audio = new Audio(url);
      player.connectMedia(audio);
      speechAudioRef.current = audio;
      audio.onended = () => {
        stopRoleplayAudio(false);
        playNextQueuedSpeech();
      };
      audio.onerror = () => {
        stopRoleplayAudio(false);
        setError("Không phát được tệp âm thanh TTS.");
        playNextQueuedSpeech();
      };
      await audio.play();
      if (controller.signal.aborted || speechAudioRef.current !== audio) return;
      reportListen();
      setSpeechLoadingId(null);
      setSpeakingId(messageId);
    } catch (error) {
      if (!controller.signal.aborted) {
        stopRoleplayAudio(false);
        setError(
          error instanceof DOMException && error.name === "NotAllowedError"
            ? "Trình duyệt chặn phát tự động. Hãy bấm Nghe một lần để cho phép âm thanh."
            : String(error),
        );
        if (automatic) playNextQueuedSpeech();
      }
    }
  }
  function playRoleplayMessage(messageId: string) {
    if (speechLoadingId === messageId || speakingId === messageId) {
      stopRoleplayAudio();
      return;
    }
    stopRoleplayAudio();
    void startRoleplayAudio(messageId);
  }
  useEffect(() => {
    stopRoleplayAudio();
  }, [account?.id, uiLanguage]);
  useEffect(
    () => () => {
      speechAbortRef.current?.abort();
      speechAudioRef.current?.pause();
      speechStreamRef.current?.stop();
      if (speechUrlRef.current) URL.revokeObjectURL(speechUrlRef.current);
    },
    [],
  );
  function cancelRolePlayStream() {
    rolePlayStreamSequence.current += 1;
    rolePlayStreams.current.forEach((controller) => controller.abort());
    rolePlayStreams.current.clear();
    rolePlayStreamRef.current?.abort();
    rolePlayStreamRef.current = null;
    setBusy(false);
    setTypingIds([]);
  }
  useEffect(
    () => () => {
      rolePlayStreamSequence.current += 1;
      rolePlayStreams.current.forEach((controller) => controller.abort());
      rolePlayStreams.current.clear();
      rolePlayStreamRef.current?.abort();
    },
    [],
  );
  const [mode, setMode] = useState(() => {
      const requested = new URLSearchParams(window.location.search).get(
        "createMode",
      );
      return requested === "story" ? "story" : "custom";
    }),
    [description, setDescription] = useState(""),
    [name, setName] = useState(""),
    [customRole, setCustomRole] = useState("companion"),
    [customScenario, setCustomScenario] = useState(""),
    [customGreeting, setCustomGreeting] = useState(""),
    [customExamples, setCustomExamples] = useState(""),
    [existingMediaCharacter, setExistingMediaCharacter] = useState(false),
    [mediaCharacterName, setMediaCharacterName] = useState(""),
    [mediaTitle, setMediaTitle] = useState(""),
    [storyFile, setStoryFile] = useState<File | null>(null),
    [storyUrl, setStoryUrl] = useState(""),
    [storyDocument, setStoryDocument] = useState<{
      id: string;
      filename: string;
    } | null>(null),
    [storyCandidates, setStoryCandidates] = useState<StoryCandidate[]>([]),
    [storyCharacterName, setStoryCharacterName] = useState(""),
    [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [memoryDraft, setMemoryDraft] = useState(""),
    [memoryTarget, setMemoryTarget] = useState<{
      kind: "character" | "room";
      id: string;
      label: string;
    } | null>(null),
    [memories, setMemories] = useState<
      {
        id: string;
        content: string;
        pinned: boolean;
      }[]
    >([]);
  useEffect(() => {
    const active = speakingId || speechLoadingId;
    const message = messages.find((item) => item.id === active);
    // Partial text can temporarily report no spoken content while action beats
    // stream. Only a completed reply or interruption can revoke playback.
    if (message && !canSpeak(message) && (!busy || message.interrupted)) stopRoleplayAudio();
  }, [messages, speakingId, speechLoadingId, busy]);
  const [memoryPopupOpen, setMemoryPopupOpen] = useState(false);
  const [roomWizard, setRoomWizard] = useState<{
    step: 1 | 2;
    selected: string[];
    query: string;
    source: "all" | "owned" | "system";
    topic: string;
    name: string;
    is_public: boolean;
  } | null>(null);
  const [characterInfo, setCharacterInfo] = useState<{
    ids: string[];
    id: string;
  } | null>(null);
  const [catalogView, setCatalogView] = useState("all");
  const [favorites, setFavorites] = useState<string[]>([]);
  const [favoritesReady, setFavoritesReady] = useState(false);
  const [publicRooms, setPublicRooms] = useState<Room[]>([]);
  useEffect(() => {
    setFavoritesReady(false);
    let stale = false;
    if (account) {
      api<{ keys: string[] }>("/v1/roleplay/favorites")
        .then((result) => {
          if (!stale) {
            setFavorites(result.keys);
            setFavoritesReady(true);
          }
        })
        .catch(() => {
          if (!stale) setError("Không tải được danh sách yêu thích.");
        });
      api<Room[]>("/v1/public/rooms")
        .then((result) => {
          if (!stale) setPublicRooms(result);
        })
        .catch(() => {});
    }
    return () => {
      stale = true;
    };
  }, [account?.id, page]);
  const favoriteKey = (c: Character) =>
    c.creation_type === "preset" && c.preset_type
      ? "preset:" + c.preset_type
      : "character:" + c.id;
  const favoriteButton = (c: Character) => (
    <button
      className="btn sm rpFavoriteAction"
      title="Yêu thích"
      aria-label="Yêu thích"
      disabled={!favoritesReady || busy}
      aria-pressed={favorites.includes(favoriteKey(c))}
      onClick={() =>
        act(async () => {
          const result = await api<{ keys: string[] }>(
            "/v1/roleplay/favorites",
            "PUT",
            {
              key: favoriteKey(c),
              favorite: !favorites.includes(favoriteKey(c)),
            },
          );
          setFavorites(result.keys);
        })
      }
    >
      Yêu thích
    </button>
  );
  function arrangeCatalog(items: Character[]) {
    if (catalogView === "team") return [];
    if (catalogView === "favorites")
      return items.filter((c) => favorites.includes(favoriteKey(c)));
    if (catalogView === "trending")
      return [...items].sort(
        (a, b) =>
          (b.trending_score || b.usage_count || 0) -
          (a.trending_score || a.usage_count || 0),
      );
    return items;
  }
  const [systemTypeFilter, setSystemTypeFilter] = useState("all");
  const [publicRatingFilter, setPublicRatingFilter] = useState(0);
  const openRoomWizard = (preselected: string[] = []) => {
    setRoomWizard({
      step: 1,
      selected: preselected.slice(0, 6),
      query: "",
      source: "owned",
      topic: "",
      name: "",
      is_public: false,
    });
  };
  const resetCreateForm = (nextMode = "custom") => {
    setMode(nextMode);
    setName("");
    setDescription("");
    setCustomRole("companion");
    setCustomScenario("");
    setCustomGreeting("");
    setCustomExamples("");
    setExistingMediaCharacter(false);
    setMediaCharacterName("");
    setMediaTitle("");
    setAvatarFile(null);
    setMakePublic(false);
    setCharacterType("companion");
    setCharacterTags("");
    setTagSearch("");
    setStoryFile(null);
    setStoryUrl("");
    setStoryDocument(null);
    setStoryCandidates([]);
    setStoryCharacterName("");
  };
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 4000);
    return () => window.clearTimeout(timeout);
  }, [notice]);
  useLayoutEffect(() => {
    const root = document.getElementById("root");
    if (root && appliedLanguage === uiLanguage)
      localizeInterface(root, uiLanguage);
  });
  useLayoutEffect(() => {
    let active = true;
    const controls = {
      retry: () => setLanguageAttempt((value) => value + 1),
      cancel: () => chooseLanguage("vi"),
    };
    setUiLanguageGate({ language: uiLanguage, busy: true, ...controls });
    setAppliedLanguage(null);
    const load = async () => {
      if (account && !catalogReady) return;
      const pack = await loadCompleteUiTranslations(uiLanguage);
      const introductions = await loadCharacterIntroductions(
        uiLanguage,
        introSources,
        account?.id || "guest",
      );
      if (!active) return;
      setRuntimeTranslations(pack);
      setIntroTranslations(introductions);
      setAppliedLanguage(uiLanguage);
      setTranslationRevision((value) => value + 1);
      await afterUiLanguagePaint();
      if (active)
        setUiLanguageGate({ language: uiLanguage, busy: false, ...controls });
    };
    void load().catch((error: unknown) => {
      if (active)
        setUiLanguageGate({
          language: uiLanguage,
          busy: false,
          error: uiLanguageErrorMessage(error, uiLanguage),
          ...controls,
        });
    });
    return () => {
      active = false;
    };
  }, [uiLanguage, languageAttempt, introSignature, catalogReady, account?.id]);
  function chooseLanguage(language: UiLanguage) {
    language = supportedUiLanguage(language);
    setLanguageAttempt((value) => value + 1);
    rememberLanguage(language);
    setUiLanguage(language);
  }
  async function refresh() {
    try {
      const [c, p, r, publicItems, sections] = await Promise.all([
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
      setChars(c);
      setPresets(p.characters);
      setRooms(r);
      setPublicCharacters(publicItems);
      setCatalogReady(true);
      setHomeSections(sections);
    } catch (e) {
      setError(String(e));
      setUiLanguageGate({
        language: uiLanguage,
        busy: false,
        error:
          "Could not load characters. Please retry or switch to Vietnamese (vi).",
        retry: () => {
          void refresh();
        },
        cancel: () => chooseLanguage("vi"),
      });
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
        chooseLanguage(restoredLanguage(value.language));
        document.documentElement.dataset.theme = value.theme || "light";
        localStorage.setItem("preferred_theme", value.theme || "light");
        document.documentElement.dataset.reducedMotion = String(
          value.reduced_motion,
        );
        refresh();
      })
      .catch((error) => {
        if (error?.status === 401) localStorage.removeItem("auth_token");
        else setError(String(error));
      })
      .finally(() => setAuthReady(true));
  }, []);
  useEffect(() => {
    const syncTheme = (event: StorageEvent) => {
      if (
        event.key !== "preferred_theme" ||
        (event.newValue !== "light" && event.newValue !== "dark")
      )
        return;
      document.documentElement.dataset.theme = event.newValue;
      setAccount((current) =>
        current && current.theme !== event.newValue
          ? { ...current, theme: event.newValue as Account["theme"] }
          : current,
      );
    };
    window.addEventListener("storage", syncTheme);
    return () => window.removeEventListener("storage", syncTheme);
  }, []);
  useEffect(() => {
    const syncAccount = (event: StorageEvent) => {
      if (
        event.key === "ui_language" &&
        event.newValue &&
        UI_LANGUAGES.some((item) => item.code === event.newValue)
      ) {
        setUiLanguage(event.newValue);
        document.documentElement.lang = event.newValue;
        setAccount((current) =>
          current ? { ...current, language: event.newValue! } : current,
        );
      }
      if (
        event.key === "avibi_account_refresh" &&
        localStorage.getItem("auth_token")
      ) {
        void api<Account>("/v1/auth/me")
          .then(setAccount)
          .catch(() => {});
      }
    };
    window.addEventListener("storage", syncAccount);
    return () => window.removeEventListener("storage", syncAccount);
  }, []);
  async function submitAuth() {
    setError("");
    try {
      const value = await api<
        Account & {
          token: string;
        }
      >(`/v1/auth/${authMode}`, "POST", {
        username: authUser,
        password: authPassword,
        display_name: authName,
      });
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
    await openOrCreateCharacterRoom(character);
  }
  async function waitForExpressionSet(characterId: string) {
    for (let attempt = 0; attempt < 300; attempt += 1) {
      const result = await api<{
        status: "processing" | "ready";
      }>(`/v1/characters/${characterId}/expressions/status`);
      if (result.status === "ready") return;
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    throw new Error("Bộ ảnh biểu cảm tạo quá lâu. Vui lòng thử lại sau.");
  }
  async function prepareStorySource() {
    if (!storyFile && !storyUrl.trim())
      throw new Error("Chọn file truyện hoặc nhập đường dẫn truyện trước.");
    let document: {
      id: string;
      filename: string;
    };
    if (storyFile) {
      const form = new FormData();
      form.append("file", storyFile);
      const response = await fetch(API + "/v1/character-sources", {
        method: "POST",
        headers: authHeaders(),
        body: form,
      });
      if (!response.ok) throw new Error(await responseError(response));
      document = await response.json();
    } else {
      document = await api("/v1/documents/from-url", "POST", {
        url: storyUrl.trim(),
      });
    }
    setStoryDocument(document);
    let ready = false;
    for (let attempt = 0; attempt < 90; attempt += 1) {
      const status = await api<{
        status: string;
        error?: string;
      }>(`/v1/documents/${document.id}`);
      if (status.status === "ready") {
        ready = true;
        break;
      }
      if (status.status === "failed")
        throw new Error(status.error || "Không thể đọc nội dung truyện.");
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    if (!ready)
      throw new Error(
        "Đọc truyện quá lâu. Hãy thử file TXT hoặc đường dẫn khác.",
      );
    const result = await api<{
      candidates: StoryCandidate[];
    }>(`/v1/documents/${document.id}/discover-characters`, "POST", {});
    setStoryCandidates(result.candidates);
    setStoryCharacterName(result.candidates[0]?.name || "");
  }
  async function createStoryCharacter() {
    if (!storyDocument || !storyCharacterName.trim()) return;
    const character = await api<Character>(
      "/v1/characters/from-document",
      "POST",
      {
        document_id: storyDocument.id,
        candidate_name: storyCharacterName.trim(),
      },
    );
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
  async function act(
    f: () => Promise<void>,
    preparesResources = false,
    successMessage = "Tài nguyên đã chuẩn bị xong. Bạn có thể bắt đầu trò chuyện.",
  ) {
    setBusy(true);
    if (preparesResources) setResourcePreparing(true);
    setNotice("");
    setError("");
    try {
      await f();
      await refresh();
      if (preparesResources) setNotice(successMessage);
    } catch (e) {
      if (!isReactionPreparationCancelled(e)) setError(String(e));
    } finally {
      setBusy(false);
      if (preparesResources) setResourcePreparing(false);
    }
  }
  async function openRoleplayMemories(target: {
    kind: "character" | "room";
    id: string;
    label: string;
  }) {
    await act(async () => {
      const path =
        target.kind === "room"
          ? `/v1/rooms/${target.id}/memories`
          : `/v1/characters/${target.id}/memories`;
      setMemories(await api(path));
      setMemoryTarget(target);
      setMemoryDraft("");
      setMemoryPopupOpen(true);
    });
  }
  async function addRoleplayMemory() {
    if (!memoryTarget || !memoryDraft.trim()) return;
    const path =
      memoryTarget.kind === "room"
        ? `/v1/rooms/${memoryTarget.id}/memories`
        : `/v1/characters/${memoryTarget.id}/memories`;
    const saved = await api<{
      id: string;
      content: string;
      pinned: boolean;
    }>(path, "POST", { content: memoryDraft.trim() });
    setMemories((current) => [
      saved,
      ...current.filter((item) => item.id !== saved.id),
    ]);
    setMemoryDraft("");
    setNotice("Đã lưu ký ức");
  }
  async function openRoom(r: Room) {
    activateActionSounds();
    actionSounds.stop();
    ++openingGreetingVersion.current;
    cancelRolePlayStream();
    stopRoleplayAudio();
    primedSpeechPlayerRef.current = new PcmStreamPlayer();
    primedSpeechPlayerRef.current.activate();
    reactionSounds.stop();
    setOpeningGreeting(null);
    const previousRoomId = room?.id || null;
    activeRoomIdRef.current = r.id;
    setResourcePreparing(true);
    setError("");
    try {
      // Optional effects warm in parallel; a failed audio download cannot lock the room.
      if (account) {
        void prepareRoomReactions(account.id, r.character_ids).catch(() => {});
        void prepareActionSounds(account.id).catch(() => {});
      }
      const stored = await api<Message[]>(`/v1/rooms/${r.id}/messages`);
      if (activeRoomIdRef.current !== r.id) return;
      for (const url of expressionPortraitCache.values())
        URL.revokeObjectURL(url);
      expressionPortraitCache.clear();
      for (const id of r.character_ids)
        void loadExpressionPortrait(id, "thinking").catch(() => {});
      setActiveExpression("neutral");
      setRoom(r);
      setMessages(stored);
      setPage("chat");
      {
        const greetings = openingVoiceMessages(stored).filter(canSpeak);
        if (greetings.length) {
          greetingSpeechRef.current = greetings[0];
          setOpeningGreeting({ roomId: r.id, messages: greetings });
        }
      }
    } catch (error) {
      if (activeRoomIdRef.current === r.id) {
        activeRoomIdRef.current = previousRoomId;
        if (!isReactionPreparationCancelled(error)) setError(String(error));
      }
      throw error;
    } finally {
      if (
        activeRoomIdRef.current === r.id ||
        activeRoomIdRef.current === previousRoomId
      )
        setResourcePreparing(false);
    }
  }
  useEffect(() => {
    if (
      !openingGreeting ||
      page !== "chat" ||
      openingGreeting.roomId !== room?.id
    )
      return;
    let active = true;
    const version = ++openingGreetingVersion.current;
    const greetings = openingGreeting.messages;
    for (const greeting of greetings) openingSpeechIdsRef.current.add(greeting.id);
    for (const greeting of greetings) prepareRoleplaySpeech(greeting, false, false);
    queueMicrotask(() => {
      if (
        !active ||
        version !== openingGreetingVersion.current ||
        activeRoomIdRef.current !== openingGreeting.roomId ||
        document.visibilityState === "hidden"
      )
        return;
      for (const greeting of greetings) {
        automaticSpeechMessages.current.set(greeting.id, greeting);
        queueRoleplaySpeech(greeting.id);
      }
      setOpeningGreeting(null);
    });
    return () => {
      active = false;
    };
  }, [openingGreeting, room?.id, page]);
  const greetingLanguageRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    const previous = greetingLanguageRef.current;
    greetingLanguageRef.current = account?.language;
    if (
      !previous ||
      !account?.language ||
      previous === account.language ||
      !room ||
      page !== "chat"
    )
      return;
    const roomId = room.id;
    let active = true;
    stopRoleplayAudio();
    void api<Message[]>(`/v1/rooms/${roomId}/messages`)
      .then((stored) => {
        if (!active || activeRoomIdRef.current !== roomId) return;
        setMessages(stored);
        {
          const greetings = openingVoiceMessages(stored).filter(canSpeak);
          if (greetings.length) {
            greetingSpeechRef.current = greetings[0];
            setOpeningGreeting({ roomId, messages: greetings });
          }
        }
      })
      .catch((error) => {
        if (active) setError(String(error));
      });
    return () => {
      active = false;
    };
  }, [account?.language]);
  useEffect(() => {
    if (!window.location.search.includes("workspace=1")) return;
    const roomId = new URLSearchParams(window.location.search).get("room");
    if (!roomId || roomId === workspaceInitialRoomRef.current) return;
    const requestedRoom = rooms.find((item) => item.id === roomId);
    if (!requestedRoom) return;
    workspaceInitialRoomRef.current = roomId;
    void openRoom(requestedRoom).catch(() => {});
  }, [rooms]);
  useEffect(() => {
    if (
      account &&
      new URLSearchParams(window.location.search).get("wizard") === "1"
    )
      openRoomWizard();
  }, [account?.id]);
  useEffect(() => {
    if (!authReady || window.parent === window) return;
    document.documentElement.dataset.workspaceReady = "true";
    window.parent.postMessage(
      { type: "avibi-workspace-ready" },
      window.location.origin,
    );
  }, [account?.id, authReady]);
  useEffect(() => {
    if (!account || !authReady || window.parent === window) return;
    window.parent.postMessage(
      { type: "avibi-workspace-history-updated" },
      window.location.origin,
    );
  }, [account?.id, authReady, rooms]);
  useEffect(() => {
    if (
      !account ||
      !authReady ||
      window.parent === window ||
      (page === "chat" && !room)
    )
      return;
    const path =
      page === "chat" && room
        ? `/role-play-ai?workspace=1&view=chat&room=${room.id}`
        : page === "create"
          ? "/role-play-ai?workspace=1&view=create"
          : "/role-play-ai?workspace=1&view=characters";
    window.parent.postMessage(
      { type: "avibi-workspace-location", path },
      window.location.origin,
    );
  }, [account?.id, authReady, page, room?.id]);
  useEffect(() => {
    if (window.parent === window) return;
    const onWorkspaceNavigation = (event: MessageEvent) => {
      if (
        event.origin !== window.location.origin ||
        event.data?.type !== "avibi-workspace-navigate"
      )
        return;
      const params = new URL(event.data.path, window.location.origin)
        .searchParams;
      const requestedView = params.get("view");
      const requestedMode = params.get("createMode");
      setSettingsOpen(false);
      if (requestedView === "chat") {
        const roomId = params.get("room");
        const requestedRoom = rooms.find((item) => item.id === roomId);
        if (requestedRoom) void openRoom(requestedRoom).catch(() => {});
        return;
      }
      setMemoryPopupOpen(false);
      setCharacterInfo(null);
      setRoomWizard(null);
      if (requestedView === "create") {
        resetCreateForm(requestedMode === "story" ? "story" : "custom");
        setError("");
        setNotice("");
        cancelRolePlayStream();
        stopRoleplayAudio();
        activeRoomIdRef.current = null;
        setRoom(null);
        setMessages([]);
        setPage("create");
        return;
      }
      cancelRolePlayStream();
      stopRoleplayAudio();
      activeRoomIdRef.current = null;
      setSearch("");
      setMyCharacterFilter("all");
      setMyCharacterTypeFilter("all");
      setSystemTypeFilter("all");
      setPublicFilter("all");
      setPublicRatingFilter(0);
      setError("");
      setNotice("");
      setPage(
        requestedView === "system" || requestedView === "discover"
          ? requestedView
          : "characters",
      );
      setRoom(null);
      setMessages([]);
      if (params.get("wizard") === "1") openRoomWizard();
    };
    window.addEventListener("message", onWorkspaceNavigation);
    return () => window.removeEventListener("message", onWorkspaceNavigation);
  }, [account?.id, authReady, rooms]);
  async function openOrCreateCharacterRoom(character: Character) {
    const existing = rooms.find(
      (item) =>
        item.character_ids.length === 1 &&
        item.character_ids[0] === character.id,
    );
    if (existing) {
      try {
        await openRoom(existing);
        return;
      } catch (error) {
        if (
          !(error instanceof Error) ||
          (error as Error & { status?: number }).status !== 404
        )
          throw error;
        setRooms((current) =>
          current.filter((item) => item.id !== existing.id),
        );
        activeRoomIdRef.current = null;
        setRoom(null);
        setMessages([]);
      }
    }
    const nextRoom = await api<Room>("/v1/rooms", "POST", {
      name: `Chat with ${character.name}`,
      character_ids: [character.id],
    });
    setRooms((current) =>
      current.some((item) => item.id === nextRoom.id)
        ? current
        : [nextRoom, ...current],
    );
    await openRoom(nextRoom);
  }
  async function startCharacterChat(character: Character) {
    await act(() => openOrCreateCharacterRoom(character), true);
  }
  async function addPreset(p: Character) {
    let character = chars.find(
      (item) =>
        item.creation_type === "preset" && item.preset_type === p.preset_type,
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
      await openOrCreateCharacterRoom(character);
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
      setChars((current) =>
        current.some((item) => item.id === cloned.id)
          ? current
          : [...current, cloned],
      );
      await openOrCreateCharacterRoom(cloned);
    }, true);
  }
  async function ensureOwnedPreset(preset: Character): Promise<Character> {
    const owned = chars.find(
      (character) =>
        character.creation_type === "preset" &&
        character.preset_type === preset.preset_type,
    );
    if (owned) return owned;
    const created = await api<Character>(
      "/v1/characters",
      "POST",
      characterSpecPayload(preset),
    );
    setChars((current) => [...current, created]);
    return created;
  }
  async function addPresetOnly(preset: Character) {
    await act(async () => {
      await ensureOwnedPreset(preset);
      setNotice(`Đã thêm ${preset.name} vào nhân vật của bạn.`);
    });
  }
  async function createRoomFromWizard() {
    if (!roomWizard || roomWizard.selected.length < 2) return;
    const wizard = roomWizard;
    await act(async () => {
      const ids: string[] = [];
      for (const id of wizard.selected) {
        const preset = presets.find(
          (item) =>
            item.id === id && !chars.some((character) => character.id === id),
        );
        ids.push(preset ? (await ensureOwnedPreset(preset)).id : id);
      }
      const pool = roomCharacterPool(visibleCharacters, presets);
      const members = wizard.selected
        .map(id => pool.find(item => item.character.id === id)?.character)
        .filter(Boolean) as Character[];
      const nextRoom = await api<Room>("/v1/rooms", "POST", {
        name:
          wizard.name.trim() ||
          `Nhóm: ${members.map((item) => item.name).join(", ")}`,
        character_ids: ids,
        topic: wizard.topic.trim(),
        is_public: wizard.is_public,
      });
      setRooms((current) => [nextRoom, ...current]);
      setRoomWizard(null);
      await openRoom(nextRoom);
    }, true);
  }
  async function send(suggestedText?: string) {
    const outgoing = (suggestedText ?? text).trim();
    if (!room || !outgoing || busy) return;
    ++openingGreetingVersion.current;
    setOpeningGreeting(null);
    reactionSounds.stop();
    actionSounds.stop();
    activateActionSounds();
    stopRoleplayAudio();
    primedSpeechPlayerRef.current = new PcmStreamPlayer();
    primedSpeechPlayerRef.current.activate();
    const sentAt = performance.now();
    const firstChunkTimes = new Map<string, number>();
    const sentRoomId = room.id;
    const streamSequence = ++rolePlayStreamSequence.current;
    const controller = new AbortController();
    rolePlayStreamRef.current = controller;
    rolePlayStreams.current.add(controller);
    const value = outgoing,
      tempId = "local-" + crypto.randomUUID();
    const immediateTyper = roomChars.length === 1 ? roomChars[0].id : undefined;
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
          body: JSON.stringify({ message: value }),
          signal: controller.signal,
        },
      );
      if (!response.ok || !response.body)
        throw new Error(await responseError(response));
      const reader = response.body.getReader(),
        decoder = new TextDecoder();
      let buffer = "",
        receivedDone = false;
      const draftIds = new Map<string, string>();
      const autoSpeechStarted = new Set<string>();
      const suggestionReceipts = new Map<
        string,
        { options: string[]; milliseconds: number }
      >();
      const suggestionMessageIds = new Map<string, string>();
      const handle = async (block: string) => {
        if (controller.signal.aborted || activeRoomIdRef.current !== sentRoomId)
          return;
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
        if (event === "suggestions") {
          const options = Array.isArray(payload.suggestions)
            ? payload.suggestions
            : [];
          suggestionReceipts.set(payload.message_id, {
            options,
            milliseconds: performance.now() - sentAt,
          });
          suggestionMessageIds.set(payload.character_id, payload.message_id);
          const draftId =
            streamSequence === rolePlayStreamSequence.current
              ? draftIds.get(payload.character_id)
              : undefined;
          setMessages((current) =>
            current.map((item) =>
              item.id === payload.message_id || (draftId && item.id === draftId)
                ? { ...item, suggestions: options }
                : item,
            ),
          );
          return;
        }
        if (event === "done") {
          receivedDone = true;
          suggestionReceipts.forEach((receipt, messageId) =>
            reportFirstChunk(
              API,
              authHeaders(),
              messageId,
              undefined,
              receipt.milliseconds,
            ),
          );
          return;
        }
        if (streamSequence !== rolePlayStreamSequence.current) return;
        if (event === "answer_done") {
          setBusy(false);
          setTypingIds([]);
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
        if (
          event === "delta" &&
          typeof payload.character_id === "string" &&
          typeof payload.text === "string"
        ) {
          if (payload.text && !firstChunkTimes.has(payload.character_id))
            firstChunkTimes.set(
              payload.character_id,
              performance.now() - sentAt,
            );
          let draftId = draftIds.get(payload.character_id);
          if (!draftId) {
            draftId =
              typeof payload.message_id === "string"
                ? String(payload.message_id)
                : "local-stream-" + crypto.randomUUID();
            draftIds.set(payload.character_id, draftId);
          }
          const currentDraftId = draftId;
          if (
            payload.speech_incremental &&
            payload.speech_supported === true &&
            typeof payload.message_id === "string" &&
            !autoSpeechStarted.has(payload.message_id)
          ) {
            const spoken: Message = {
              id: payload.message_id, sender_type: "character",
              character_id: payload.character_id, text: payload.text,
              speech_supported: true, speech_languages: payload.speech_languages,
            };
            autoSpeechStarted.add(spoken.id);
            automaticSpeechMessages.current.set(spoken.id, spoken);
            prepareRoleplaySpeech(spoken, true);
          }
          actionSounds.feed(currentDraftId, payload.text);
          setTypingIds((ids) =>
            ids.filter((id) => id !== payload.character_id),
          );
          setMessages((current) =>
            current.some((item) => item.id === currentDraftId)
              ? current.map((item) =>
                  item.id === currentDraftId
                    ? {
                        ...item,
                        text: item.text + payload.text,
                        speech_supported: payload.speech_supported,
                        speech_languages: payload.speech_languages,
                      }
                    : item,
                )
              : [
                  ...current,
                  {
                    id: currentDraftId,
                    sender_type: "character",
                    character_id: payload.character_id,
                    text: payload.text,
                    speech_supported: payload.speech_supported,
                    speech_languages: payload.speech_languages,
                    suggestions: suggestionReceipts.get(
                      suggestionMessageIds.get(payload.character_id) || "",
                    )?.options,
                  },
                ],
          );
        }
        if (event === "reaction" && activeRoomIdRef.current === sentRoomId) {
          if (["neutral","happy","sad","angry","surprised","shy","thinking"].includes(payload.emotion)) {
            setActiveExpression(payload.emotion);
            void loadExpressionPortrait(payload.character_id, payload.emotion).catch(() => {});
          }
          reactionMetadataRef.current.set(payload.message_id, {
            emotion: payload.emotion, language: payload.language, voiceId: payload.voice_id,
          });
        }
        if (event === "character_message") {
          if (
            !payload.interrupted &&
            activeRoomIdRef.current === sentRoomId &&
            typeof payload.text === "string"
          )
            actionSounds.finish(
              draftIds.get(payload.character_id) || payload.id,
              payload.text,
            );
          reportFirstChunk(
            API,
            authHeaders(),
            payload.id,
            firstChunkTimes.get(payload.character_id),
            !suggestionReceipts.has(payload.id) && payload.suggestions?.length
              ? performance.now() - sentAt
              : undefined,
          );
          payload.suggestions = Array.isArray(payload.suggestions)
            ? payload.suggestions
                .filter(
                  (item: unknown) =>
                    typeof item === "string" && !item.includes("@@"),
                )
                .slice(0, 3)
            : [];
          payload.suggestions = payload.interrupted
            ? []
            : suggestionReceipts.get(payload.id)?.options ||
              payload.suggestions;
          const emotion = payload.emotion || "neutral";
          reactionMetadataRef.current.set(payload.id, {
            emotion, language: payload.reaction_language || payload.speech_languages?.[0],
            voiceId: payload.reaction_voice_id,
          });
          // Supported dialogue owns its clip gate and group playback order.
          // A reply without speech may still play its standalone reaction.
          if (!payload.interrupted && activeRoomIdRef.current === sentRoomId && !canSpeak(payload as Message))
            void reactionSounds.react(payload.id, payload.character_id, emotion,
              payload.reaction_language || payload.speech_languages?.[0], payload.reaction_voice_id);

          if (roomChars.length === 1)
            void loadExpressionPortrait(payload.character_id, emotion).catch(
              () => {},
            );
          if (
            streamSequence !== rolePlayStreamSequence.current ||
            activeRoomIdRef.current !== sentRoomId
          )
            return;
          flushSync(() => {
            setTypingIds((ids) =>
              ids.filter((id) => id !== payload.character_id),
            );
            setActiveExpression(emotion);
            const draftId = draftIds.get(payload.character_id);
            setMessages((m) =>
              draftId && m.some((item) => item.id === draftId)
                ? m.map((item) => (item.id === draftId ? payload : item))
                : [...m, payload],
            );
          });
          draftIds.delete(payload.character_id);
          automaticSpeechMessages.current.set(payload.id, payload as Message);
          if (!payload.interrupted && canSpeak(payload as Message)) {
            if (!autoSpeechStarted.has(payload.id)) {
              autoSpeechStarted.add(payload.id);
              prepareRoleplaySpeech(payload as Message);
            } else {
              // A failed early request must not permanently suppress autoplay.
              // Retry once with the complete reply, retaining successful streams.
              const retryCompletedReply = () => {
                if (streamSequence !== rolePlayStreamSequence.current ||
                    activeRoomIdRef.current !== sentRoomId) return;
                prepareRoleplaySpeech(payload as Message);
              };
              const pending = backgroundSpeech.pending(payload.id);
              if (pending) void pending.catch(retryCompletedReply);
              else retryCompletedReply();
            }
          }
          if (payload.speech_error)
            setError(`Không tạo được giọng nói: ${payload.speech_error}`);
        }
        if (event === "character_error") {
          setTypingIds((ids) =>
            ids.filter((id) => id !== payload.character_id),
          );
          const draftId = draftIds.get(payload.character_id);
          if (draftId)
            setMessages((current) =>
              current.map((item) =>
                item.id === draftId ? { ...item, interrupted: true } : item,
              ),
            );
          setError(payload.message);
        }
        if (event === "error") setError(payload.message);
      };
      while (true) {
        const { done, value: chunk } = await reader.read();
        if (controller.signal.aborted || activeRoomIdRef.current !== sentRoomId)
          break;
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
      if (!receivedDone && streamSequence === rolePlayStreamSequence.current)
        throw new Error("Phản hồi bị gián đoạn trước khi hoàn tất.");
    } catch (e) {
      if (
        streamSequence === rolePlayStreamSequence.current &&
        activeRoomIdRef.current === sentRoomId
      ) {
        if (!(e instanceof DOMException && e.name === "AbortError"))
          setError(String(e));
        setTypingIds([]);
        setMessages((current) =>
          current
            .filter((message) => message.id !== tempId)
            .map((message) =>
              message.id.startsWith("local-stream-")
                ? { ...message, interrupted: true }
                : message,
            ),
        );
      }
    } finally {
      rolePlayStreams.current.delete(controller);
      if (streamSequence === rolePlayStreamSequence.current) {
        rolePlayStreamRef.current = null;
        setBusy(false);
        setTypingIds([]);
      }
    }
  }
  async function regenerateMessage(message: Message) {
    if (!room || busy) return;
    stopRoleplayAudio();
    primedSpeechPlayerRef.current = new PcmStreamPlayer();
    primedSpeechPlayerRef.current.activate();
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
      prepareRoleplaySpeech(replacement);
      if (replacement.speech_error)
        setError(`Không tạo được giọng nói: ${replacement.speech_error}`);
    });
  }
  async function deleteRoom(roomToDelete: Room) {
    const targets =
      roomToDelete.character_ids.length === 1
        ? rooms.filter(
            (item) =>
              item.character_ids.length === 1 &&
              item.character_ids[0] === roomToDelete.character_ids[0],
          )
        : [roomToDelete];
    if (!confirm(`Xóa cuộc trò chuyện “${roomToDelete.name}”?`)) return;
    await act(async () => {
      for (const target of targets) {
        try {
          await api(`/v1/rooms/${target.id}`, "DELETE");
        } catch (error) {
          if (
            !(error instanceof Error) ||
            (error as Error & { status?: number }).status !== 404
          )
            throw error;
        }
      }
      const deletedIds = new Set(targets.map((item) => item.id));
      setError("");
      if (deletedIds.has(workspaceInitialRoomRef.current))
        workspaceInitialRoomRef.current = "";
      setRooms((current) => current.filter((item) => !deletedIds.has(item.id)));
      if (room && deletedIds.has(room.id)) {
        cancelRolePlayStream();
        stopRoleplayAudio();
        activeRoomIdRef.current = null;
        setRoom(null);
        setMessages([]);
        setActiveExpression("neutral");
        setPage("home");
      }
    });
  }
  const visibleRooms = [...rooms]
    .sort((left, right) =>
      (right.created_at || "").localeCompare(left.created_at || ""),
    )
    .filter(
      (item, index, ordered) =>
        item.character_ids.length !== 1 ||
        ordered.findIndex(
          (candidate) =>
            candidate.character_ids.length === 1 &&
            candidate.character_ids[0] === item.character_ids[0],
        ) === index,
    );
  useEffect(() => {
    if (account && ["home", "characters", "system", "discover"].includes(page))
      warmReactionClips(account.id, [
        ...rooms.flatMap((item) => item.character_ids),
        ...chars.map((item) => item.id),
      ]);
  }, [account?.id, page, rooms, chars]);
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
  const catalogCharacterType = (character: Character) =>
    character.character_type ||
    character.support?.primary_role ||
    character.category ||
    "other";
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
  const filteredPublicCharacters = arrangeCatalog(
    publicCharacters.filter((character) => {
      const labels = [character.character_type, ...(character.tags || [])]
        .join(" ")
        .toLowerCase();
      const categoryMatch =
        publicFilter === "all" ||
        (publicFilter === "roleplay"
          ? /role.?play|fantasy|adventure|drama|nhập vai|giả tưởng|phiêu lưu|chính kịch/.test(
              labels,
            )
          : labels.includes(publicFilter));
      return (
        categoryMatch &&
        (!publicRatingFilter ||
          (character.rating || 0) >= publicRatingFilter) &&
        matchesSearch(
          character.name,
          character.description,
          character.character_type,
          ...(character.tags || []),
        )
      );
    }),
  );
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
  const filteredOwned = arrangeCatalog(
    visibleCharacters.filter((character) => {
      const visibilityMatch =
        myCharacterFilter === "all" ||
        (myCharacterFilter === "public"
          ? Boolean(character.is_public)
          : !character.is_public);
      const typeMatch =
        myCharacterTypeFilter === "all" ||
        catalogCharacterType(character) === myCharacterTypeFilter;
      return (
        visibilityMatch &&
        typeMatch &&
        matchesSearch(
          character.name,
          character.display_name,
          character.description,
          catalogCharacterType(character),
          ...(character.tags || []),
        )
      );
    }),
  );
  const ownedTypes = [
    ...new Set(
      visibleCharacters.map((character) => catalogCharacterType(character)),
    ),
  ].sort();
  const filteredSystem = arrangeCatalog(
    presets.filter((preset) => {
      if (preset.home_section === "hidden") return false;
      const type =
        preset.category === "entertainment"
          ? "entertainment"
          : preset.support?.primary_role || "companion";
      return (
        (systemTypeFilter === "all" || type === systemTypeFilter) &&
        matchesSearch(
          preset.name,
          preset.description,
          preset.support?.introduction,
          ...(preset.tags || []),
        )
      );
    }),
  );
  const matchingPublicRooms = publicRooms.filter(r => matchesSearch(r.name));
  const matchingOwnedRooms = visibleRooms.filter(r => r.character_ids.length > 1 && matchesSearch(r.name));
  const catalogSections = (
    <>
      <nav className="rpCatalogSections" aria-label="Bộ lọc nhân vật">
        {[
          ["all", "Tất cả"],
          ["trending", "Xu hướng"],
          ["favorites", "Yêu thích"],
          ["team", "Phòng nhóm"],
        ].map(([key, label]) => (
          <button
            key={key}
            className={catalogView === key ? "active" : ""}
            aria-pressed={catalogView === key}
            onClick={() => setCatalogView(key)}
          >
            {label}
          </button>
        ))}
      </nav>
      {(catalogView === "team" ||
        (catalogView === "all" && ((page === "discover" && matchingPublicRooms.length > 0) ||
          (page === "characters" && matchingOwnedRooms.length > 0)))) && (
        <section>
          {catalogView === "all" && <h2>Phòng nhóm</h2>}
        <div className="myCharacterGrid">
          {(page === "discover" ? matchingPublicRooms : matchingOwnedRooms)
            .map((r) => (
              <article className="card" key={r.id}>
                <h3 data-no-translate="true">{r.name}</h3>
                <p>{r.character_ids.length} nhân vật</p>
                <button
                  className="btn primary"
                  onClick={() =>
                    act(async () => {
                      if (page !== "discover") {
                        await openRoom(r);
                        return;
                      }
                      const next = await api<Room>(
                        "/v1/public/rooms/" + r.id + "/start",
                        "POST",
                      );
                      await refresh();
                      await openRoom(next);
                    }, true)
                  }
                >
                  Trò chuyện
                </button>
                {page !== "discover" && (
                  <button
                    className="btn"
                    onClick={() =>
                      act(async () => {
                        await api("/v1/rooms/" + r.id, "PATCH", {
                          is_public: !r.is_public,
                        });
                        await refresh();
                      })
                    }
                  >
                    {r.is_public ? "Đặt riêng tư" : "Công khai phòng chat"}
                  </button>
                )}
              </article>
            ))}
          <button className="btn" onClick={() => openRoomWizard()}>
            Tạo phòng chat
          </button>
        </div>
        </section>
      )}
    </>
  );
  const searchField = (
    <label className="rpSearch">
      <Icon n="search" />

      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Tìm theo tên, mô tả hoặc tag"
        aria-label="Tìm nhân vật"
      />
    </label>
  );
  const collectionTabs = (current: "characters" | "system" | "discover") => (
    <div className="rpTabbar">
      <div className="tabs" role="tablist">
        {(
          [
            ["characters", `Nhân vật của tôi (${visibleCharacters.length})`],
            [
              "system",
              `Nhân vật hệ thống (${presets.filter((item) => item.home_section !== "hidden").length})`,
            ],
            ["discover", "Cộng đồng"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={current === key}
            className={current === key ? "active" : ""}
            onClick={() => setPage(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <button className="btn primary" onClick={() => openRoomWizard()}>
        <Icon n="plus-small" />
        Tạo phòng chat
      </button>
    </div>
  );
  if (!authReady)
    return (
      <div className="authPage">
        <div className="authCard">
          <RolePlayLoadingCat />

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
      {page === "home" && (
        <div className="rpBackgroundMusicFloating">
          <BackgroundMusicButton {...backgroundMusic} />
        </div>
      )}

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

      {memoryPopupOpen && memoryTarget && (
        <div
          className="scrim enter"
          onMouseDown={(event) =>
            event.target === event.currentTarget && setMemoryPopupOpen(false)
          }
        >
          <section
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-label="Ký ức"
          >
            <header>
              <div>
                <span className="eyebrow">
                  Ký ức ·{" "}
                  {memoryTarget.kind === "room" ? "phòng nhóm" : "nhân vật"}
                </span>

                <h2>{memoryTarget.label} nhớ gì?</h2>
              </div>

              <button
                className="iconbtn"
                onClick={() => setMemoryPopupOpen(false)}
                aria-label="Đóng"
              >
                <Icon n="cross-small" />
              </button>
            </header>

            <div className="body">
              <p className="rpMuted">
                {memoryTarget.kind === "room"
                  ? "Ký ức này chỉ dùng trong phòng nhóm hiện tại."
                  : `Những điều ${memoryTarget.label} nhớ về bạn được dùng ở mọi phòng chat 1-1 với nhân vật này.`}{" "}
                Ký ức được ghim luôn được ưu tiên.
              </p>

              <label className="field">
                Thêm ký ức mới
                <textarea
                  value={memoryDraft}
                  maxLength={1000}
                  onChange={(event) => setMemoryDraft(event.target.value)}
                  placeholder="Ví dụ: Mình thích uống cà phê ít đường vào buổi sáng."
                />
              </label>

              <div className="rpRowBetween">
                <small className="rpMuted">Tối đa 1000 ký tự</small>
                <button
                  className="btn primary sm"
                  disabled={busy || !memoryDraft.trim()}
                  onClick={() => void act(addRoleplayMemory)}
                >
                  <Icon n="plus-small" />
                  Thêm ký ức
                </button>
              </div>

              <div className="rpRowBetween">
                <b>Đã nhớ</b>
                <span className="chip">{memories.length} ký ức</span>
              </div>

              {!memories.length && (
                <div className="empty">
                  Chưa có ký ức nào. Thêm điều bạn muốn {memoryTarget.label} ghi
                  nhớ ở ô phía trên.
                </div>
              )}

              {[...memories]
                .sort((x, y) => Number(y.pinned) - Number(x.pinned))
                .map((m) => (
                  <article
                    className={`rpMemoryRow${m.pinned ? " pinned" : ""}`}
                    key={m.id}
                  >
                    <textarea
                      value={m.content}
                      onChange={(e) =>
                        setMemories((items) =>
                          items.map((x) =>
                            x.id === m.id
                              ? { ...x, content: e.target.value }
                              : x,
                          ),
                        )
                      }
                    />

                    <div className="rpRowBetween">
                      {m.pinned ? (
                        <span className="chip accent">
                          <Icon n="thumbtack" />
                          Đã ghim
                        </span>
                      ) : (
                        <span />
                      )}

                      <div className="rpRow">
                        <button
                          className="btn sm"
                          onClick={() =>
                            act(async () => {
                              await api(`/v1/memories/${m.id}`, "PATCH", {
                                content: m.content,
                                pinned: m.pinned,
                              });
                              setNotice("Đã lưu ký ức");
                            })
                          }
                        >
                          Lưu
                        </button>

                        <button
                          className="btn sm"
                          onClick={() =>
                            act(async () => {
                              await api(`/v1/memories/${m.id}`, "PATCH", {
                                pinned: !m.pinned,
                              });
                              setMemories((items) =>
                                items.map((x) =>
                                  x.id === m.id
                                    ? { ...x, pinned: !x.pinned }
                                    : x,
                                ),
                              );
                            })
                          }
                        >
                          {m.pinned ? "Bỏ ghim" : "Ghim"}
                        </button>

                        <button
                          className="btn sm danger"
                          onClick={() =>
                            act(async () => {
                              await api(`/v1/memories/${m.id}`, "DELETE");
                              setMemories((items) =>
                                items.filter((x) => x.id !== m.id),
                              );
                            })
                          }
                        >
                          Xóa
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
            </div>

            <footer>
              <button className="btn" onClick={() => setMemoryPopupOpen(false)}>
                Xong
              </button>
            </footer>
          </section>
        </div>
      )}

      {characterInfo &&
        (() => {
          const info =
            chars.find((item) => item.id === characterInfo.id) ||
            presets.find((item) => item.id === characterInfo.id) ||
            publicCharacters.find((item) => item.id === characterInfo.id);
          if (!info) return null;
          const source =
            info.creation_type === "preset"
              ? "Nhân vật hệ thống"
              : info.is_public
                ? "Công khai"
                : "Riêng tư";
          const type =
            roleLabels[catalogCharacterType(info) as keyof typeof roleLabels] ||
            catalogCharacterType(info);
          return (
            <div
              className="scrim enter"
              onMouseDown={(event) =>
                event.target === event.currentTarget && setCharacterInfo(null)
              }
            >
              <section
                className="dialog"
                role="dialog"
                aria-modal="true"
                aria-label="Thông tin nhân vật"
              >
                <header>
                  <h2>Thông tin nhân vật</h2>
                  <button
                    className="iconbtn"
                    onClick={() => setCharacterInfo(null)}
                    aria-label="Đóng"
                  >
                    <Icon n="cross-small" />
                  </button>
                </header>

                {characterInfo.ids.length > 1 && (
                  <div className="tabs rpModalTabs">
                    {characterInfo.ids.map((id) => {
                      const member = chars.find((item) => item.id === id);
                      return member ? (
                        <button
                          key={id}
                          className={id === characterInfo.id ? "active" : ""}
                          onClick={() =>
                            setCharacterInfo({ ...characterInfo, id })
                          }
                        >
                          {member.name}
                        </button>
                      ) : null;
                    })}
                  </div>
                )}

                <div className="body">
                  <div className="rpInfoHero">
                    <CharacterAvatar
                      character={info}
                      className="rpInfoAvatar"
                    />

                    <div>
                      <h3 data-no-translate="true" translate="no">
                        {info.name}
                      </h3>

                      <p
                        className="rpMuted"
                        data-no-translate="true"
                        translate="no"
                      >
                        {info.identity?.role || type}
                      </p>

                      <div className="rpRow">
                        <span className="chip accent">{source}</span>
                        {info.simulation_label && (
                          <span className="chip warn">AI simulation</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {info.support?.introduction && (
                    <blockquote
                      className="rpQuote"
                      data-no-translate="true"
                      translate="no"
                    >
                      “{introText(info.support.introduction)}”
                    </blockquote>
                  )}

                  <dl className="rpKv">
                    <dt>Mô tả</dt>
                    <dd data-no-translate="true" translate="no">
                      {introText(info.description) || "—"}
                    </dd>

                    <dt>Loại</dt>
                    <dd>{type}</dd>

                    {!!info.support?.strengths.length && (
                      <>
                        <dt>Thế mạnh</dt>
                        <dd>
                          {info.support.strengths
                            .map((item) => roleLabels[item])
                            .join(", ")}
                        </dd>
                      </>
                    )}

                    {!!info.tags?.length && (
                      <>
                        <dt>Tags</dt>
                        <dd
                          className="rpRow"
                          data-no-translate="true"
                          translate="no"
                        >
                          {info.tags.map((tag) => (
                            <span className="chip" key={tag}>
                              #{tag}
                            </span>
                          ))}
                        </dd>
                      </>
                    )}

                    <dt>Người tạo</dt>
                    <dd>
                      {info.creation_type === "preset"
                        ? "Avibi"
                        : info.creator?.name || account?.display_name || "Bạn"}
                    </dd>

                    <dt>Lượt dùng</dt>
                    <dd>
                      {(info.usage_count || 0).toLocaleString("vi-VN")} người
                      dùng
                    </dd>
                  </dl>

                  {reactionTotal(info) > 0 && (
                    <ReactionSummary character={info} />
                  )}
                </div>

                <footer className="split">
                  <button
                    className="btn"
                    onClick={() => {
                      setCharacterInfo(null);
                      void openRoleplayMemories({
                        kind: "character",
                        id: info.id,
                        label: info.name,
                      });
                    }}
                  >
                    <Icon n="brain" />
                    Ký ức
                  </button>

                  <div className="rpRow">
                    {characterInfo.ids.length > 1 && (
                      <button
                        className="btn"
                        onClick={() => {
                          setCharacterInfo(null);
                          void startCharacterChat(info);
                        }}
                      >
                        <Icon n="comment-alt" />
                        Trò chuyện riêng
                      </button>
                    )}

                    <button
                      className="btn primary"
                      onClick={() => setCharacterInfo(null)}
                    >
                      Đóng
                    </button>
                  </div>
                </footer>
              </section>
            </div>
          );
        })()}

      {roomWizard &&
        (() => {
          const pool = roomCharacterPool(visibleCharacters, presets);
          const query = roomWizard.query.trim().toLocaleLowerCase();
          const visible = pool.filter(
            ({ character, source }) =>
              (roomWizard.source === "all" || roomWizard.source === source) &&
              (!query ||
                [
                  character.name,
                  character.description,
                  catalogCharacterType(character),
                ]
                  .join(" ")
                  .toLocaleLowerCase()
                  .includes(query)),
          );
          const picked = roomWizard.selected
            .map(
              (id) => pool.find((item) => item.character.id === id)?.character,
            )
            .filter(Boolean) as Character[];
          const count = roomWizard.selected.length;
          const hint =
            count < 2
              ? `Chọn thêm ít nhất ${2 - count} nhân vật nữa.`
              : count >= 6
                ? "Đã đủ tối đa 6 nhân vật."
                : `Có thể chọn thêm ${6 - count} nhân vật.`;
          const toggle = (id: string) =>
            setRoomWizard({
              ...roomWizard,
              selected: roomWizard.selected.includes(id)
                ? roomWizard.selected.filter((value) => value !== id)
                : count >= 6
                  ? roomWizard.selected
                  : [...roomWizard.selected, id],
            });
          const suggestedName = `Nhóm: ${picked.map((item) => item.name).join(", ")}`;
          return (
            <div
              className="scrim enter"
              onMouseDown={(event) =>
                event.target === event.currentTarget && setRoomWizard(null)
              }
            >
              <section
                className="dialog wide"
                role="dialog"
                aria-modal="true"
                aria-label="Tạo phòng chat"
              >
                <header>
                  <h2>Tạo phòng chat</h2>
                  <button
                    className="iconbtn"
                    onClick={() => setRoomWizard(null)}
                    aria-label="Đóng"
                  >
                    <Icon n="cross-small" />
                  </button>
                </header>

                <ol className="rpStepper">
                  {["Chọn nhân vật", "Xác nhận"].map((label, index) => (
                    <li
                      key={label}
                      className={
                        index + 1 < roomWizard.step
                          ? "done"
                          : index + 1 === roomWizard.step
                            ? "current"
                            : ""
                      }
                    >
                      <span>
                        {index + 1 < roomWizard.step ? (
                          <Icon n="check" />
                        ) : (
                          index + 1
                        )}
                      </span>
                      {label}
                    </li>
                  ))}
                </ol>

                <div className="body">
                  {roomWizard.step === 1 ? (
                    <>
                      <p className="note-info">
                        <Icon n="users-alt" />
                        <span>
                          Phòng chat cần <b>ít nhất 2 nhân vật</b> (tối đa 6).
                          Muốn trò chuyện riêng với 1 nhân vật, bấm{" "}
                          <b>Trò chuyện</b> trên thẻ nhân vật.
                        </span>
                      </p>

                      <div className="rpTray">
                        <div className="rpRowBetween">
                          <b>Đã chọn {count}/6</b>
                          <small className="rpMuted">{hint}</small>
                        </div>

                        <div className="rpRow">
                          {picked.length ? (
                            picked.map((item) => (
                              <span className="rpSelChip" key={item.id}>
                                <CharacterAvatar
                                  character={item}
                                  className="rpSelAvatar"
                                />
                                {item.name}
                                <button
                                  onClick={() => toggle(item.id)}
                                  aria-label={`Bỏ ${item.name}`}
                                >
                                  <Icon n="cross-small" />
                                </button>
                              </span>
                            ))
                          ) : (
                            <small className="rpMuted">
                              Chưa chọn nhân vật nào
                            </small>
                          )}
                        </div>
                      </div>

                      <div className="rpFilters">
                        <label className="rpSearch">
                          <Icon n="search" />
                          <input
                            value={roomWizard.query}
                            onChange={(event) =>
                              setRoomWizard({
                                ...roomWizard,
                                query: event.target.value,
                              })
                            }
                            placeholder="Tìm theo tên hoặc loại"
                            aria-label="Tìm nhân vật"
                          />
                        </label>

                        <label className="rpFilter">
                          Nguồn
                          <select
                            value={roomWizard.source}
                            onChange={(event) =>
                              setRoomWizard({
                                ...roomWizard,
                                source: event.target.value as
                                  | "all"
                                  | "owned"
                                  | "system",
                              })
                            }
                          >
                            <option value="all">Tất cả</option>
                            <option value="owned">Của tôi</option>
                            <option value="system">Hệ thống</option>
                          </select>
                        </label>
                      </div>

                      <div className="rpPickGrid">
                        {visible.map(({ character, source }) => {
                          const on = roomWizard.selected.includes(character.id);
                          return (
                            <button
                              key={character.id}
                              className={`rpPick${on ? " on" : ""}`}
                              aria-pressed={on}
                              onClick={() => toggle(character.id)}
                            >
                              <CharacterAvatar
                                character={character}
                                className="rpPickAvatar"
                              />

                              <span className="rpPickText">
                                <b data-no-translate="true" translate="no">
                                  {character.name}
                                </b>
                                <small>
                                  {roleLabels[
                                    catalogCharacterType(
                                      character,
                                    ) as keyof typeof roleLabels
                                  ] || catalogCharacterType(character)}{" "}
                                  ·{" "}
                                  {source === "owned" ? "Của tôi" : "Hệ thống"}
                                </small>
                              </span>

                              <span className="rpCheck">
                                {on && <Icon n="check" />}
                              </span>
                            </button>
                          );
                        })}

                        {!visible.length && (
                          <div className="empty">Không tìm thấy nhân vật.</div>
                        )}
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="rpSummary">
                        <span className="rpRow rpStack">
                          {picked.map((item) => (
                            <CharacterAvatar
                              key={item.id}
                              character={item}
                              className="rpSummaryAvatar"
                            />
                          ))}
                        </span>

                        <div>
                          <span className="chip accent">
                            Chat nhóm · {picked.length} nhân vật
                          </span>
                          <p>
                            {picked.map((item) => item.name).join(", ")} và bạn
                          </p>
                        </div>
                      </div>

                      <label className="field">
                        Tên phòng
                        <input
                          value={roomWizard.name}
                          onChange={(event) =>
                            setRoomWizard({
                              ...roomWizard,
                              name: event.target.value,
                            })
                          }
                          placeholder={suggestedName}
                        />
                        <small>
                          Để trống sẽ dùng tên gợi ý: {suggestedName}
                        </small>
                      </label>

                      <label className="field">
                        Chủ đề (tuỳ chọn)
                        <textarea
                          value={roomWizard.topic}
                          maxLength={500}
                          rows={3}
                          onChange={(event) => setRoomWizard({
                            ...roomWizard, topic: event.target.value,
                          })}
                        />
                        <small>Để trống để lấy cảm hứng từ tên nhóm hoặc trò chuyện tự nhiên.</small>
                      </label>

                      <label className="field">
                        <span>
                          <input
                            type="checkbox"
                            aria-label="Công khai phòng chat"
                            checked={roomWizard.is_public}
                            onChange={(event) =>
                              setRoomWizard({
                                ...roomWizard,
                                is_public: event.target.checked,
                              })
                            }
                          />{" "}
                          Công khai phòng chat
                        </span>
                        <small>
                          Phòng công khai chỉ chia sẻ nhóm nhân vật, không chia
                          sẻ lịch sử tin nhắn. Nhân vật hệ thống có thể dùng ngay;
                          nhân vật tự tạo cần được công khai trước.
                        </small>
                      </label>
                      <div className="rpNextBox">
                        <b>Sau khi tạo phòng</b>
                        <ul>
                          <li>Phòng xuất hiện ở mục Gần đây trên thanh bên.</li>
                          <li>Từng nhân vật gửi lời chào đầu tiên.</li>
                          {picked.some(
                            (item) =>
                              !chars.some((owned) => owned.id === item.id),
                          ) && (
                            <li>
                              Nhân vật hệ thống được tự thêm vào Nhân vật của
                              tôi.
                            </li>
                          )}
                        </ul>
                      </div>
                    </>
                  )}
                </div>

                <footer className="split">
                  {roomWizard.step === 1 ? (
                    <>
                      <button
                        className="btn"
                        onClick={() => setRoomWizard(null)}
                      >
                        Hủy
                      </button>
                      <button
                        className="btn primary"
                        disabled={count < 2}
                        onClick={() =>
                          setRoomWizard({ ...roomWizard, step: 2 })
                        }
                      >
                        Tiếp tục <Icon n="angle-small-right" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="btn"
                        onClick={() =>
                          setRoomWizard({ ...roomWizard, step: 1 })
                        }
                      >
                        <Icon n="angle-small-left" /> Quay lại
                      </button>
                      <button
                        className="btn primary"
                        disabled={busy}
                        onClick={() => void createRoomFromWizard()}
                      >
                        <Icon n="comment-alt" />
                        Tạo phòng và bắt đầu chat
                      </button>
                    </>
                  )}
                </footer>
              </section>
            </div>
          );
        })()}

      {(resourcePreparing || (busy && page === "create")) && (
        <div className="creatingOverlay" role="status" aria-live="polite">
          <div className="creatingCard">
            <RolePlayLoadingCat />

            {resourcePreparing ? (
              <>
                <h2>Đang chuẩn bị tài nguyên...</h2>

                <p>Nhân vật đang đến với bạn, chờ đợi là hạnh phúc.</p>

                <small>Đi đâu mà vội mà vàng đúng không.</small>
              </>
            ) : (
              <>
                <h2>Đang hoàn thiện nhân vật...</h2>

                <p>Nhân vật đang đến với bạn, chờ đợi là hạnh phúc.</p>

                <small>Đi đâu mà vội mà vàng đúng không.</small>
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

          <span>Avibi Platform</span>
        </a>

        <nav className="platformPrimaryNav">
          <a className="platformSectionLink" href="/ai-assistant">
            <Icon n="sparkles" /> Trợ lý AI
          </a>

          <button
            className={
              page === "characters" || page === "discover" || page === "system"
                ? "active"
                : ""
            }
            onClick={() => setPage("characters")}
          >
            <Icon n="comments" /> Chat Bot AI
          </button>

          <button
            className={page === "create" ? "active" : ""}
            onClick={() => {
              resetCreateForm();
              setPage("create");
            }}
          >
            <Icon n="magic-wand" /> Sáng tạo nhân vật
          </button>
        </nav>

        <nav className="platformSubNav">
          {(["home", "discover", "characters", "rooms"] as const).map((p) => (
            <button
              className={page === p ? "active" : ""}
              onClick={() => {
                if (p === "rooms") openRoomWizard();
                else setPage(p);
              }}
              key={p}
            >
              {
                {
                  home: "⌂  Trang chủ",
                  discover: "⌕  Cộng đồng",
                  characters: "☺  Nhân vật của tôi",
                  create: "＋  Tạo nhân vật",
                  rooms: "＋  Tạo phòng chat",
                }[p]
              }
            </button>
          ))}
        </nav>

        <div className="sideTitle">Trò chuyện gần đây</div>

        {visibleRooms.map((r) => (
          <div className="recentRoom" key={r.id}>
            <button
              className="roomLink"
              onClick={() => {
                void openRoom(r).catch(() => {});
              }}
            >
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
        {page !== "chat" && !window.location.search.includes("workspace=1") && (
          <div className="appTopbar">
            {
              <>
                <button className="themeButton" onClick={toggleTheme}>
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
              </>
            }
          </div>
        )}

        {error && (
          <div className="error" onClick={() => setError("")}>
            {error} ×
          </div>
        )}

        {notice && (
          <div
            className="notice"
            role="status"
            aria-live="polite"
            onClick={() => setNotice("")}
          >
            {notice} ×
          </div>
        )}

        {["characters", "system", "discover"].includes(page) && (
          <RoleplayStoryHero
            characters={[...chars, ...presets, ...publicCharacters]}
            disabled={busy}
            reducedMotion={account.reduced_motion}
            musicControl={<BackgroundMusicButton {...backgroundMusic} />}
            onOpen={(character) => {
              if (chars.some((owned) => owned.id === character.id))
                void startCharacterChat(character);
              else if (presets.some((preset) => preset.id === character.id))
                void addPreset(character);
              else void startPublicCharacter(character);
            }}
          />
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
                onClick={() => openRoomWizard()}
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
                      introduction={introText(character.description)}
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

                        <strong data-no-translate="true" translate="no">
                          {character.name}
                        </strong>

                        <h3 data-no-translate="true" translate="no">
                          {character.display_name || character.name}
                        </h3>

                        <p data-no-translate="true" translate="no">
                          {introText(character.description)}
                        </p>

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
                        introduction={introText(character.description)}
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
              {visibleRooms
                .filter((r) => matchesSearch(r.name))
                .map((r) => (
                  <button
                    className="card"
                    key={r.id}
                    onClick={() => {
                      void openRoom(r).catch(() => {});
                    }}
                  >
                    {r.name}
                  </button>
                ))}
            </div>
          </>
        )}

        {page === "discover" && (
          <>
            <header className="collectionHeader">
              <div>
                <span className="eyebrow">CỘNG ĐỒNG</span>

                <h1>Khám phá nhân vật public</h1>
              </div>
            </header>

            {collectionTabs("discover")}

            <div className="rpFilters">
              {searchField}

              <label className="rpFilter">
                Loại
                <select
                  value={publicFilter}
                  onChange={(event) => setPublicFilter(event.target.value)}
                >
                  {publicCategories.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="rpFilter">
                Đánh giá
                <select
                  value={String(publicRatingFilter)}
                  onChange={(event) =>
                    setPublicRatingFilter(Number(event.target.value))
                  }
                >
                  <option value="0">Tất cả</option>

                  <option value="4.5">Từ 4,5★</option>

                  <option value="4">Từ 4★</option>

                  <option value="3">Từ 3★</option>
                </select>
              </label>

              {catalogView !== "team" && (
                <span className="chip rpCount">
                  {filteredPublicCharacters.length + (catalogView === "all" ? matchingPublicRooms.length : 0)} kết quả
                </span>
              )}
            </div>

            {catalogSections}
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

                    <h3 data-no-translate="true" translate="no">
                      {c.name}
                    </h3>

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

                    <p data-no-translate="true" translate="no">
                      {introText(c.description)}
                    </p>

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

                    {favoriteButton(c)}
                  </div>
                </article>
              ))}
            </div>

            {catalogView !== "team" && !filteredPublicCharacters.length &&
              !(catalogView === "all" && matchingPublicRooms.length) && (
              <div className="emptyState">Chưa có nhân vật public phù hợp.</div>
            )}
          </>
        )}

        {page === "characters" && (
          <>
            {collectionTabs("characters")}

            <div className="rpFilters">
              {searchField}

              <label className="rpFilter">
                Hiển thị
                <select
                  value={myCharacterFilter}
                  onChange={(event) => setMyCharacterFilter(event.target.value)}
                >
                  <option value="all">Tất cả</option>

                  <option value="private">Riêng tư</option>

                  <option value="public">Công khai</option>
                </select>
              </label>

              <label className="rpFilter">
                Loại
                <select
                  value={myCharacterTypeFilter}
                  onChange={(event) =>
                    setMyCharacterTypeFilter(event.target.value)
                  }
                >
                  <option value="all">Tất cả</option>

                  {ownedTypes.map((type) => (
                    <option value={type} key={type}>
                      {roleLabels[type as keyof typeof roleLabels] || type}
                    </option>
                  ))}
                </select>
              </label>

              {catalogView !== "team" && (
                <span className="chip rpCount">
                  {filteredOwned.length} nhân vật
                </span>
              )}
            </div>

            {catalogSections}
            <div className="grid myCharacterGrid">
              {filteredOwned.map((c) => (
                <article className="card myCharacterCard" key={c.id}>
                  <CharacterAvatar character={c} className="myCharacterCover" />

                  <div className="cardTitleRow">
                    <strong data-no-translate="true" translate="no">
                      {c.name}
                    </strong>

                    {c.simulation_label && (
                      <span className="chip warn">AI simulation</span>
                    )}
                  </div>

                  <small>
                    <span className="chip accent">
                      {c.is_public ? "Công khai" : "Riêng tư"}
                    </span>{" "}
                    {roleLabels[
                      catalogCharacterType(c) as keyof typeof roleLabels
                    ] || catalogCharacterType(c)}{" "}
                    · {c.usage_count || 0} người dùng
                  </small>

                  <div className="reactionBar">
                    {reactionEmojis.map((emoji) => (
                      <button
                        key={emoji}
                        onClick={() => act(() => reactCharacter(c.id, emoji))}
                      >
                        {emoji} {c.reactions?.[emoji] || ""}
                      </button>
                    ))}
                  </div>

                  <p data-no-translate="true" translate="no">
                    {introText(c.description)}
                  </p>

                  <div className="rpCardActions">
                    {favoriteButton(c)}

                    <button
                      className="btn primary sm"
                      disabled={busy}
                      onClick={() => void startCharacterChat(c)}
                    >
                      <Icon n="comment-alt" />
                      Trò chuyện
                    </button>

                    <button
                      className="btn sm"
                      onClick={() =>
                        void openRoleplayMemories({
                          kind: "character",
                          id: c.id,
                          label: c.name,
                        })
                      }
                    >
                      <Icon n="brain" />
                      Ký ức
                    </button>

                    <button
                      className="btn sm"
                      onClick={() =>
                        setCharacterInfo({ ids: [c.id], id: c.id })
                      }
                    >
                      <Icon n="info" />
                      Thông tin
                    </button>

                    <button
                      className="btn sm danger"
                      disabled={busy}
                      title={
                        c.is_public
                          ? "Xóa nhân vật công khai"
                          : "Xóa nhân vật riêng tư"
                      }
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
                      <Icon n="trash" />
                      Xóa
                    </button>
                  </div>
                </article>
              ))}
            </div>

            {catalogView !== "team" && !filteredOwned.length &&
              !(catalogView === "all" && matchingOwnedRooms.length) && (
              <div className="empty">
                {visibleCharacters.length
                  ? "Không có nhân vật nào khớp bộ lọc."
                  : "Bạn chưa có nhân vật nào. Thêm từ tab Nhân vật hệ thống hoặc mở Sáng tạo nhân vật."}
              </div>
            )}
          </>
        )}

        {page === "system" && (
          <>
            <header className="collectionHeader">
              <div>
                <span className="eyebrow">NHÂN VẬT HỆ THỐNG</span>

                <h1>Nhân vật do Avibi xây dựng</h1>
              </div>
            </header>

            {collectionTabs("system")}

            <div className="rpFilters">
              {searchField}

              <label className="rpFilter">
                Loại
                <select
                  value={systemTypeFilter}
                  onChange={(event) => setSystemTypeFilter(event.target.value)}
                >
                  <option value="all">Tất cả</option>

                  <option value="companion">Đồng hành</option>

                  <option value="study">Học tập</option>

                  <option value="work">Công việc</option>

                  <option value="entertainment">Giải trí</option>
                </select>
              </label>

              {catalogView !== "team" && (
                <span className="chip rpCount">
                  {filteredSystem.length} nhân vật
                </span>
              )}
            </div>

            {catalogSections}
            <div className="grid myCharacterGrid">
              {filteredSystem.map((p) => (
                <article className="card myCharacterCard" key={p.id}>
                  <CharacterAvatar character={p} className="myCharacterCover" />

                  <strong data-no-translate="true" translate="no">
                    {p.name}
                  </strong>

                  <small>
                    <span className="chip">
                      {p.category === "entertainment"
                        ? "Giải trí"
                        : roleLabels[p.support?.primary_role || "companion"]}
                    </span>{" "}
                    · {p.usage_count || 0} người dùng
                  </small>

                  <p data-no-translate="true" translate="no">
                    {introText(p.support?.introduction || p.description)}
                  </p>

                  {!!p.support?.strengths.length && (
                    <div className="strengths">
                      {p.support.strengths.map((item) => (
                        <span key={item}>{roleLabels[item]}</span>
                      ))}
                    </div>
                  )}

                  <div className="rpCardActions">
                    {favoriteButton(p)}

                    <button
                      className="btn primary sm"
                      disabled={busy}
                      onClick={() => void addPreset(p)}
                    >
                      <Icon n="comment-alt" />
                      Trò chuyện
                    </button>

                    <button
                      className="btn sm"
                      disabled={busy || hasPreset(p)}
                      onClick={() => void addPresetOnly(p)}
                    >
                      {hasPreset(p) ? (
                        <>
                          <Icon n="check" />
                          Đã thêm
                        </>
                      ) : (
                        <>
                          <Icon n="plus-small" />
                          Thêm vào nhân vật của tôi
                        </>
                      )}
                    </button>
                  </div>
                </article>
              ))}
            </div>

            {catalogView !== "team" && !filteredSystem.length && (
              <div className="empty">Không có nhân vật hệ thống phù hợp.</div>
            )}
          </>
        )}

        {page === "create" && (
          <>
            <header className="collectionHeader">
              <div>
                <span className="eyebrow">CHAT BOT AI</span>

                <h1>Sáng tạo nhân vật</h1>
              </div>
            </header>

            <div className="tabs rpCreateTabs" role="tablist">
              {[
                ["custom", "Tự sáng tạo"],
                ["story", "Tạo từ truyện"],
                ["room", "Tạo phòng chat"],
              ].map(([k, v]) => (
                <button
                  role="tab"
                  aria-selected={mode === k}
                  onClick={() => {
                    setMode(k);
                    if (k === "room") openRoomWizard();
                  }}
                  key={k}
                >
                  {v}
                </button>
              ))}
            </div>

            {mode === "room" && (
              <section className="formCard">
                <p>Chọn nhân vật từ bộ sưu tập để tạo phòng chat.</p>
                <button
                  className="btn primary"
                  onClick={() => openRoomWizard()}
                >
                  Tạo phòng chat
                </button>
              </section>
            )}
            {mode === "custom" && (
              <div className="createGrid">
                <section className="formCard">
                  <div className="avatarPick">
                    <div className="avatarPickPreview">
                      {avatarFile ? (
                        <img
                          src={URL.createObjectURL(avatarFile)}
                          alt="Avatar preview"
                        />
                      ) : (
                        <Icon n="user" size={24} />
                      )}
                    </div>

                    <div className="stack" style={{ gap: 4 }}>
                      <label className="btn sm">
                        <Icon n="upload" />
                        {avatarFile ? "Đổi ảnh" : "Tải avatar"}

                        <input
                          className="sr"
                          type="file"
                          accept="image/png,image/jpeg,image/webp,image/gif"
                          onChange={(e) =>
                            setAvatarFile(e.target.files?.[0] || null)
                          }
                        />
                      </label>

                      <small className="faint">
                        Tùy chọn. Có ảnh sẽ tạo bộ 6 ảnh biểu cảm.
                      </small>
                    </div>
                  </div>

                  <label className="field">
                    <span>Tên nhân vật</span>

                    <input
                      className="input"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Ví dụ: Linh"
                    />
                  </label>

                  <label className="field">
                    <span>Mô tả tính cách</span>

                    <textarea
                      className="input"
                      rows={5}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Linh hơi lạnh lúc đầu, hài hước khi thân, thích âm nhạc..."
                    />

                    <small
                      className="tnum"
                      style={
                        description.length > 6000
                          ? { color: "var(--warn)" }
                          : undefined
                      }
                    >
                      {description.length.toLocaleString("vi-VN")} ký tự
                      {description.length > 6000
                        ? " · Trên 6000 ký tự: AI sẽ tóm tắt có cấu trúc trước khi tạo"
                        : ""}
                    </small>
                  </label>

                  <label className="check">
                    <input
                      type="checkbox"
                      checked={existingMediaCharacter}
                      onChange={(e) =>
                        setExistingMediaCharacter(e.target.checked)
                      }
                    />
                    Đây là nhân vật trong phim hoặc hoạt hình?
                  </label>

                  {existingMediaCharacter && (
                    <div className="form-grid">
                      <label className="field">
                        <span>Tên nhân vật</span>

                        <input
                          className="input"
                          value={mediaCharacterName}
                          onChange={(e) =>
                            setMediaCharacterName(e.target.value)
                          }
                          placeholder="Ví dụ: Tony Stark, Gojo Satoru..."
                        />
                      </label>

                      <label className="field">
                        <span>Tên phim / hoạt hình</span>

                        <input
                          className="input"
                          value={mediaTitle}
                          onChange={(e) => setMediaTitle(e.target.value)}
                          placeholder="Ví dụ: Iron Man, Jujutsu Kaisen..."
                        />
                      </label>

                      <small className="faint full">
                        AI sẽ tham khảo nguồn công khai về nhân vật này; mô tả
                        của bạn vẫn được ưu tiên.
                      </small>
                    </div>
                  )}

                  <div className="form-grid">
                    <label className="field">
                      <span>Vai trò</span>

                      <input
                        className="input"
                        value={customRole}
                        onChange={(e) => setCustomRole(e.target.value)}
                        placeholder="Ví dụ: Người bạn"
                      />
                    </label>

                    <label className="field">
                      <span>Loại nhân vật</span>

                      <select
                        className="input"
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

                  <div className="field">
                    <span>
                      Tags{" "}
                      <small className="faint">({selectedTags.length}/8)</small>
                    </span>

                    <div className="tagBox">
                      {selectedTags.map((tag) => (
                        <span className="chip acc" key={tag}>
                          #{tag}
                          <button
                            type="button"
                            onClick={() => toggleTag(tag)}
                            aria-label={`Bỏ tag ${tag}`}
                          >
                            ×
                          </button>
                        </span>
                      ))}

                      <input
                        value={tagSearch}
                        disabled={selectedTags.length >= 8}
                        onChange={(e) => setTagSearch(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && tagSearch.trim()) {
                            e.preventDefault();
                            toggleTag(tagSearch.trim());
                            setTagSearch("");
                          }
                        }}
                        placeholder={
                          selectedTags.length >= 8
                            ? "Đã đủ 8 tag"
                            : "Gõ rồi nhấn Enter"
                        }
                      />
                    </div>

                    <div className="pills">
                      {suggestedTags
                        .filter(
                          (tag) =>
                            !selectedTags.includes(tag) &&
                            tag.toLowerCase().includes(tagSearch.toLowerCase()),
                        )
                        .map((tag) => (
                          <button
                            type="button"
                            key={tag}
                            disabled={selectedTags.length >= 8}
                            onClick={() => toggleTag(tag)}
                          >
                            + {tag}
                          </button>
                        ))}
                    </div>
                  </div>
                </section>

                <section className="formCard">
                  <label className="row switchRow">
                    <span>
                      <b>Công khai nhân vật</b>
                      <br />
                      <small className="muted">
                        Người khác có thể tìm thấy và thêm nhân vật này
                      </small>
                    </span>

                    <input
                      type="checkbox"
                      className="switch"
                      checked={makePublic}
                      onChange={(e) => setMakePublic(e.target.checked)}
                    />
                  </label>

                  <label className="field">
                    <span>Bối cảnh trò chuyện</span>

                    <textarea
                      className="input"
                      value={customScenario}
                      onChange={(e) => setCustomScenario(e.target.value)}
                      placeholder="Ví dụ: Quán cà phê nhỏ đầu hẻm, chiều mưa."
                    />
                  </label>

                  <label className="field">
                    <span>Lời chào đầu tiên</span>

                    <textarea
                      className="input"
                      value={customGreeting}
                      onChange={(e) => setCustomGreeting(e.target.value)}
                      placeholder="Câu đầu tiên nhân vật nói"
                    />
                  </label>

                  <label className="field">
                    <span>Ví dụ cách nói</span>

                    <textarea
                      className="input"
                      rows={4}
                      value={customExamples}
                      onChange={(e) => setCustomExamples(e.target.value)}
                      placeholder="Mỗi dòng một câu, tối đa 8"
                    />
                  </label>

                  <button
                    className="btn pri createSubmit"
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
                    <Icon n="sparkles" />
                    Tạo bằng AI
                  </button>
                </section>
              </div>
            )}

            {mode === "story" && (
              <section className="formCard storyCard">
                <div className="row storySteps" aria-label="Các bước">
                  {["Tải truyện", "Tìm nhân vật", "Chọn & tạo"].map(
                    (label, index) => (
                      <span key={label} className="row" style={{ gap: 6 }}>
                        {index > 0 && <Icon n="angle-small-right" />}

                        <span
                          className={`chip${(storyDocument ? 2 : busy ? 1 : 0) >= index ? " acc" : ""}`}
                        >
                          {index + 1}. {label}
                        </span>
                      </span>
                    ),
                  )}
                </div>

                {!storyDocument ? (
                  <>
                    <div className="field">
                      <span>File truyện</span>

                      <label className="btn storyFileBtn">
                        <Icon n="upload" />
                        {storyFile
                          ? storyFile.name
                          : "Chọn file .txt .md .pdf .docx .pptx"}

                        <input
                          className="sr"
                          type="file"
                          accept=".txt,.md,.pdf,.docx,.pptx"
                          onChange={(event) =>
                            setStoryFile(event.target.files?.[0] || null)
                          }
                        />
                      </label>
                    </div>

                    <div className="row faint storyOr">
                      <span />
                      hoặc
                      <span />
                    </div>

                    <label className="field">
                      <span>Dán link</span>

                      <input
                        className="input"
                        type="url"
                        value={storyUrl}
                        onChange={(event) => setStoryUrl(event.target.value)}
                        placeholder="https://…"
                      />
                    </label>

                    <button
                      className="btn pri createSubmit"
                      disabled={busy || (!storyFile && !storyUrl.trim())}
                      onClick={() =>
                        act(
                          prepareStorySource,
                          true,
                          "Đã đọc truyện. Chọn nhân vật muốn tạo.",
                        )
                      }
                    >
                      <Icon n="search" />
                      Tải lên và tìm nhân vật
                    </button>

                    <p className="faint" style={{ fontSize: 12, margin: 0 }}>
                      Hệ thống đọc nội dung, tìm nhân vật trong truyện, rồi tạo
                      tính cách và cách nói dựa trên các đoạn có nhân vật đó.
                    </p>
                  </>
                ) : (
                  <>
                    <p style={{ margin: 0 }}>
                      <b>Tìm được {storyCandidates.length} nhân vật</b> trong{" "}
                      <span className="mono">{storyDocument.filename}</span>
                    </p>

                    {storyCandidates.length ? (
                      <div className="storyFound">
                        {storyCandidates.map((candidate) => (
                          <label
                            key={candidate.name}
                            className={
                              storyCharacterName === candidate.name
                                ? "selected"
                                : ""
                            }
                          >
                            <input
                              type="radio"
                              name="story-candidate"
                              checked={storyCharacterName === candidate.name}
                              onChange={() =>
                                setStoryCharacterName(candidate.name)
                              }
                            />

                            <span>
                              <b data-no-translate="true" translate="no">
                                {candidate.name}
                              </b>
                              <br />

                              <span
                                className="muted"
                                style={{ fontSize: 13 }}
                                data-no-translate="true"
                                translate="no"
                              >
                                {candidate.description}
                              </span>

                              {!!candidate.source_evidence.length && (
                                <q>
                                  {candidate.source_evidence
                                    .slice(0, 2)
                                    .join(" · ")}
                                </q>
                              )}
                            </span>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <p className="muted" style={{ margin: 0 }}>
                        Chưa tự tìm thấy nhân vật. Hãy nhập tên nhân vật xuất
                        hiện trong truyện.
                      </p>
                    )}

                    <label className="field">
                      <span>Hoặc tự nhập tên nhân vật</span>

                      <input
                        className="input"
                        value={storyCharacterName}
                        onChange={(event) =>
                          setStoryCharacterName(event.target.value)
                        }
                        placeholder="Tên nhân vật"
                      />
                    </label>

                    <div className="row">
                      <button
                        className="btn"
                        disabled={busy}
                        onClick={() => {
                          setStoryDocument(null);
                          setStoryCandidates([]);
                          setStoryCharacterName("");
                        }}
                      >
                        Chọn truyện khác
                      </button>

                      <button
                        className="btn pri"
                        disabled={busy || !storyCharacterName.trim()}
                        onClick={() =>
                          act(
                            createStoryCharacter,
                            true,
                            "Đã tạo nhân vật từ truyện.",
                          )
                        }
                      >
                        <Icon n="sparkles" />
                        Tạo nhân vật từ truyện
                      </button>
                    </div>
                  </>
                )}
              </section>
            )}
          </>
        )}

        {page === "chat" && room && (
          <div
            className={`chatWorkspace ${chatToolsCollapsed ? "toolsCollapsed" : ""}`}
          >
            <div className="chat">
              <header
                key={`emotion-header-${typingIds.length ? "thinking" : activeExpression}`}
                className={`chatEmotionHeader emotion-${typingIds.length ? "thinking" : activeExpression} ${roomChars.length === 1 ? "singleCharacter" : "groupChatHeader"}`}
              >
                {roomChars.length === 1 && (
                  <EmotionPortrait
                    characterId={roomChars[0].id}
                    emotion={typingIds.length ? "thinking" : activeExpression}
                    name={roomChars[0].name}
                  />
                )}

                <h1 data-no-translate="true" translate="no">
                  {room.name}
                </h1>

                <p data-no-translate="true" translate="no">
                  {roomChars.map((c) => c.name).join(" · ")}
                </p>
              </header>

              <div className="roleplayAmbient">
                <div className="messages" ref={messagesBox}>
                  {messages.map((m, messageIndex) => {
                    const author =
                      roomChars.find((c) => c.id === m.character_id) ||
                      chars.find((c) => c.id === m.character_id) ||
                      presets.find((c) => c.id === m.character_id) ||
                      publicCharacters.find((c) => c.id === m.character_id);
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
                          (m.sender_type === "user"
                            ? "mineBlock"
                            : m.sender_type === "character"
                              ? "characterBlock"
                              : "")
                        }
                      >
                        {m.sender_type === "character" && author && (
                          <CharacterAvatar
                            character={author}
                            className="chatMessageAvatar"
                          />
                        )}

                        {m.sender_type === "document" && m.attachment ? (
                          <div
                            className={`documentMessage ${m.attachment.status}`}
                          >
                            <div className="documentIcon">
                              <Icon n="document" />
                            </div>

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
                              "bubble " +
                              (m.sender_type === "user" ? "mine" : "")
                            }
                          >
                            {m.sender_type === "character" &&
                              canSpeak(m) &&
                              !m.id.startsWith("local-") && (
                                <button
                                  type="button"
                                  className={`roleplaySpeakButton ${speakingId === m.id ? "playing" : ""}`}
                                  onClick={() => void playRoleplayMessage(m.id)}
                                  aria-label={`${speakingId === m.id || speechLoadingId === m.id ? "Dừng" : "Nghe"} giọng ${author?.name || room.name}`}
                                  aria-pressed={speakingId === m.id}
                                  title={
                                    speakingId === m.id
                                      ? "Dừng phát"
                                      : "Phát bằng TTS"
                                  }
                                >
                                  {speechLoadingId === m.id
                                    ? "◌ Đang tạo"
                                    : speakingId === m.id
                                      ? "■ Dừng"
                                      : "▶ Nghe"}
                                </button>
                              )}

                            <small>
                              {m.sender_type === "user" ? (
                                "Bạn"
                              ) : (
                                <span data-no-translate="true" translate="no">
                                  {author?.name}
                                </span>
                              )}
                            </small>

                            <div data-no-translate="true" translate="no">
                              {renderRoleplayText(
                                m.text,
                                m.sender_type === "character",
                              )}
                            </div>

                            {m.interrupted && (
                              <p className="chatInterrupted">
                                Câu trả lời bị gián đoạn. Hãy thử gửi lại.
                              </p>
                            )}

                            {m.sender_type === "character" &&
                              !m.id.startsWith("local-") && (
                                <button
                                  className="regenerate"
                                  disabled={busy}
                                  onClick={() => regenerateMessage(m)}
                                >
                                  <Icon n="rotate-right" /> Trả lời khác
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

                        {isLatestCharacter && !!m.suggestions?.length && (roomChars.length < 2 || !busy) && (
                          <div className={roomChars.length > 1 ? "suggestions groupSuggestionRow" : "suggestions"}>
                            {m.suggestions.slice(0,3).map((suggestion, index) => (
                              <button
                                key={index}
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
                    <div
                      className="typingBubble"
                      key={"typing-" + id}
                      role="status"
                      aria-label={`${chars.find((c) => c.id === id)?.name || "Nhân vật"} đang nhập`}
                    >
                      {chars.find((c) => c.id === id) && (
                        <CharacterAvatar
                          character={chars.find((c) => c.id === id)!}
                          className="chatTypingAvatar"
                        />
                      )}

                      <div className="typingDots">
                        <i />

                        <i />

                        <i />
                      </div>
                    </div>
                  ))}

                  <div ref={messagesEnd} />
                </div>
              </div>

              <div className="composer">
                <div className="composerBox">
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
                  <AutoGrowTextarea
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
                  <div className="composerBar">
                    <EmojiPicker
                      onSelect={(emoji) =>
                        setText((current) => current + emoji)
                      }
                      disabled={busy}
                    />
                    <span className="composerHint">
                      Enter để gửi · Shift+Enter xuống dòng
                    </span>
                    <button
                      className="composerSend"
                      disabled={busy || !text.trim()}
                      onClick={() => send()}
                      aria-label="Gửi"
                      title="Gửi (Enter)"
                    >
                      <Icon n="arrow-small-up" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <aside className="characterTools">
              <button
                className="iconbtn collapseTools"
                onClick={() => setChatToolsCollapsed((value) => !value)}
              >
                <Icon
                  n={
                    chatToolsCollapsed
                      ? "angle-small-left"
                      : "angle-small-right"
                  }
                />
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
                        <strong data-no-translate="true" translate="no">
                          {roomChars[0].name}
                        </strong>

                        <small data-no-translate="true" translate="no">
                          {introText(
                            roomChars[0].support?.introduction ||
                              roomChars[0].description,
                          )}
                        </small>

                        <span>
                          ◉ {roomChars[0].usage_count || 0} người dùng
                        </span>
                      </div>
                    </div>
                  )}

                  {roomChars.length === 1 && room && (
                    <CharacterFeelings
                      characterId={roomChars[0].id}
                      roomId={room.id}
                      revision={messages.filter(message => message.sender_type === "character").at(-1)?.id || ""}
                      busy={busy}
                    />
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

                  <div className="toolMenu">
                    <button
                      onClick={() => openRoomWizard(roomChars.map((c) => c.id))}
                    >
                      <span>
                        <Icon n="users-alt" />
                      </span>

                      <b>Tạo phòng chat khác</b>

                      <i>
                        <Icon n="angle-small-right" />
                      </i>
                    </button>

                    <button
                      onClick={() => {
                        if (roomChars.length > 1 && room)
                          void openRoleplayMemories({
                            kind: "room",
                            id: room.id,
                            label: room.name,
                          });
                        else if (roomChars[0])
                          void openRoleplayMemories({
                            kind: "character",
                            id: roomChars[0].id,
                            label: roomChars[0].name,
                          });
                      }}
                    >
                      <span>
                        <Icon n="brain" />
                      </span>

                      <b>Ký ức</b>

                      <i>
                        <Icon n="angle-small-right" />
                      </i>
                    </button>

                    <button
                      onClick={() =>
                        roomChars[0] &&
                        setCharacterInfo({
                          ids: roomChars.map((c) => c.id),
                          id: roomChars[0].id,
                        })
                      }
                    >
                      <span>
                        <Icon n="info" />
                      </span>

                      <b>Thông tin nhân vật</b>

                      <i>
                        <Icon n="angle-small-right" />
                      </i>
                    </button>
                    <div
                      className="rpCharacterMusicControl"
                      data-background-music-control
                    >
                      <BackgroundMusicButton {...backgroundMusic} />
                      <button
                        type="button"
                        disabled={
                          (!reactionSounds.ready && !actionSounds.ready) ||
                          (!reactionSounds.available && !actionSounds.available)
                        }
                        onClick={() => {
                          if (reactionSounds.enabled) actionSounds.stop();
                          reactionSounds.toggle();
                        }}
                        aria-pressed={reactionSounds.enabled}
                        data-reaction-control
                      >
                        <span>
                          <Icon n="volume" />
                        </span>
                        <b>
                          {!reactionSounds.available && !actionSounds.available
                            ? "Chưa có âm phản ứng"
                            : reactionSounds.enabled
                              ? "Tắt âm phản ứng"
                              : "Bật âm phản ứng"}
                        </b>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}
