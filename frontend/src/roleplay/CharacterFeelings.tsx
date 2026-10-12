import { useEffect, useState } from "react";
import { API, authHeaders } from "./api";
import { storedLanguage } from "../i18n";

type Feelings = {
  familiarity: number;
  trust: number;
  affection: number;
  conflict: number;
  emotion: string;
  emotion_intensity: number;
};
const labels: Record<string, string[]> = {
  vi: ["Thân thiết", "Tin tưởng", "Thiện cảm", "Căng thẳng"],
  en: ["Closeness", "Trust", "Affection", "Tension"],
  zh: ["亲密度", "信任", "好感", "紧张"],
  ja: ["親密さ", "信頼", "好感", "緊張"],
  ko: ["친밀도", "신뢰", "호감", "긴장"],
  my: ["ရင်းနှီးမှု", "ယုံကြည်မှု", "နှစ်သက်မှု", "တင်းမာမှု"],
  km: ["ភាពស្និទ្ធស្នាល", "ទំនុកចិត្ត", "ការពេញចិត្ត", "ភាពតានតឹង"],
};
const metrics = [
  ["familiarity", "🥰", "close"],
  ["trust", "🤝", "trust"],
  ["affection", "💗", "affection"],
  ["conflict", "😠", "tension"],
] as const;
const expressions: Record<string, string> = {
  thinking: "🤔",
  neutral: "😌",
  happy: "😊",
  sad: "😔",
  angry: "😠",
  surprised: "😲",
  shy: "☺️",
  curious: "🤔",
  annoyed: "😒",
  slightly_annoyed: "😒",
  sulking: "😒",
  hurt: "😢",
  tired: "😴",
  anxious: "😟",
};
const emotionNames: Record<string, string[]> = {
  vi: [
    "Bình thường",
    "Vui vẻ",
    "Buồn",
    "Giận",
    "Ngạc nhiên",
    "Ngại ngùng",
    "Suy nghĩ",
  ],
  en: ["Neutral", "Happy", "Sad", "Angry", "Surprised", "Shy", "Thinking"],
  zh: ["平静", "开心", "难过", "生气", "惊讶", "害羞", "思考"],
  ja: ["平常", "喜び", "悲しみ", "怒り", "驚き", "照れ", "考え中"],
  ko: ["평온", "기쁨", "슬픔", "화남", "놀람", "수줍음", "생각 중"],
  my: [
    "ပုံမှန်",
    "ပျော်ရွှင်",
    "ဝမ်းနည်း",
    "စိတ်ဆိုး",
    "အံ့ဩ",
    "ရှက်ရွံ့",
    "စဉ်းစားနေ",
  ],
  km: ["ធម្មតា", "រីករាយ", "សោកសៅ", "ខឹង", "ភ្ញាក់ផ្អើល", "អៀន", "កំពុងគិត"],
};
function emotionIndex(value: string) {
  if (["happy", "laughing", "playful", "winking"].includes(value)) return 1;
  if (["sad", "crying", "hurt", "sulking", "tired"].includes(value)) return 2;
  if (["angry", "annoyed", "slightly_annoyed"].includes(value)) return 3;
  if (["surprised", "anxious"].includes(value)) return 4;
  if (value === "shy") return 5;
  if (["thinking", "curious"].includes(value)) return 6;
  return 0;
}
function percentage(value: unknown) {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.round(Math.max(0, Math.min(1, value)) * 100)
    : null;
}
export function CharacterFeelings({
  characterId,
  roomId,
  revision,
  busy,
}: {
  characterId: string;
  roomId: string;
  revision: string;
  busy: boolean;
}) {
  const [data, setData] = useState<{
    characterId: string;
    roomId: string;
    value: Feelings;
  } | null>(null);
  useEffect(() => {
    if (busy) return;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    void fetch(
      API +
        "/v1/characters/" +
        encodeURIComponent(characterId) +
        "/relationship",
      {
        headers: authHeaders(),
        cache: "no-store",
        signal: controller.signal,
      },
    )
      .then(async (response) => {
        if (!response.ok) return;
        const value: Feelings = await response.json();
        if (!controller.signal.aborted) setData({ characterId, roomId, value });
      })
      .catch(() => {
        /* Optional state must not block chat. */
      })
      .finally(() => clearTimeout(timer));
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [characterId, roomId, revision, busy]);
  const current =
    data?.characterId === characterId && data.roomId === roomId
      ? data.value
      : null;
  const language = storedLanguage();
  const names = labels[language] || labels.en;
  const expressionName = (emotionNames[language] || emotionNames.en)[
    emotionIndex(current?.emotion || "neutral")
  ];
  const intensity = percentage(current?.emotion_intensity);
  return (
    <div className="characterFeelings" data-no-translate="true" translate="no">
      {metrics.map(([key, icon, color], index) => {
        const raw = current?.[key];
        const percent = percentage(raw);
        const text =
          names[index] + ": " + (percent === null ? "—" : percent + "%");
        return (
          <div
            key={key}
            className={"characterFeeling feeling-" + color}
            tabIndex={0}
            title={text}
            aria-label={text}
          >
            <span className="feelingEmoji" aria-hidden="true">
              {icon}
            </span>
            <span className="feelingName">{names[index]}</span>
            <strong className="feelingPercent">
              {percent === null ? "—" : percent + "%"}
            </strong>
            <span
              className="feelingTrack"
              role="meter"
              aria-label={names[index]}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent ?? undefined}
            >
              <span style={{ width: (percent ?? 0) + "%" }} />
            </span>
          </div>
        );
      })}
      <div
        className="characterFeeling feelingExpression"
        title={expressionName}
        aria-label={expressionName}
      >
        <span className="feelingEmoji" aria-hidden="true">
          {current ? expressions[current.emotion] || "😌" : "◌"}
        </span>
        <span className="feelingName">{expressionName}</span>
        <strong className="feelingPercent">
          {intensity === null ? "—" : intensity + "%"}
        </strong>
        <span
          className="feelingTrack"
          role="meter"
          aria-label={expressionName}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={intensity ?? undefined}
        >
          <span style={{ width: (intensity ?? 0) + "%" }} />
        </span>
      </div>
    </div>
  );
}
