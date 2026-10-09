/* Thành phần giao diện dùng chung cho Avibi Platform (theo "Avibi Platform Prototype"). */
import { useId, useLayoutEffect, useRef, type CSSProperties, type ReactNode, type TextareaHTMLAttributes } from "react";
import { EYES, ILLUSTRATIONS, MODE_META, MOUTH, metaOf, type AssistantModeId, type Emotion } from "./persona";

export { MODE_META, type AssistantModeId, type Emotion };

/** Icon từ bộ UIcons Regular Rounded của Flaticon. `n` là tên sau tiền tố fi-rr-. */
export function Icon({ n, size, className = "", title }: { n: string; size?: number; className?: string; title?: string }) {
  return (
    <i
      className={`fi-rr-${n} vi${className ? ` ${className}` : ""}`}
      style={size ? { fontSize: size } : undefined}
      aria-hidden={title ? undefined : true}
      title={title}
    />
  );
}

/** Ô nhập chat tự giãn theo nội dung, cao tối đa `maxHeight` (px) rồi mới cuộn. */
export function AutoGrowTextarea({ maxHeight = 138, value, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement> & { value: string; maxHeight?: number }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    const border = el.offsetHeight - el.clientHeight;
    const next = Math.min(el.scrollHeight + border, maxHeight);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight + border > maxHeight ? "auto" : "hidden";
  }, [value, maxHeight]);
  return <textarea ref={ref} rows={1} value={value} {...props} style={{ ...props.style, maxHeight }} />;
}

/* *x*, **x**, ***x*** — dấu * phải sát chữ và không dính liền chữ/số bên ngoài,
   nên "2*3*4" hay "* gạch đầu dòng" không bị hiểu nhầm là in nghiêng. */
const STAR_SPAN = /(?<![\p{L}\p{N}*])(\*{1,3})(?![\s*])([^*\n]+?)(?<!\s)\1(?![\p{L}\p{N}*])/gu;

/**
 * Định dạng text trả về từ trợ lý / nhân vật theo dấu *.
 * - assistant: *x* nghiêng, **x** đậm, ***x*** đậm nghiêng.
 * - roleplay: *x* là hành động (nghiêng, chữ phụ); **x** là đoạn hành động
 *   đứng riêng một dòng (giữ cách hiển thị cũ); ***x*** đậm nghiêng.
 * Dòng bắt đầu bằng "* " hoặc "- " được đổi thành gạch đầu dòng "•".
 */
export function formatStarText(text: string, mode: "assistant" | "roleplay"): ReactNode[] {
  const source = text.replace(/^([ \t]*)[*-][ \t]+/gm, "$1• ");
  const nodes: ReactNode[] = [];
  let last = 0;
  let afterBlock = false;
  const pushText = (value: string) => {
    const content = afterBlock ? value.replace(/^\n/, "") : value;
    afterBlock = false;
    if (content) nodes.push(content);
  };
  for (const match of source.matchAll(STAR_SPAN)) {
    pushText(source.slice(last, match.index));
    const [, stars, body] = match;
    const key = nodes.length;
    if (stars.length === 3) nodes.push(<strong key={key}><em>{body}</em></strong>);
    else if (stars.length === 2 && mode === "roleplay") {
      nodes.push(<strong className="roleplayActionBeat" key={key}>{body}</strong>);
      afterBlock = true;
    } else if (stars.length === 2) nodes.push(<strong key={key}>{body}</strong>);
    else nodes.push(<em className={mode === "roleplay" ? "roleplayAction" : undefined} key={key}>{body}</em>);
    last = match.index + match[0].length;
  }
  pushText(source.slice(last));
  return nodes;
}

/** Gương mặt minh họa của persona; biểu cảm thay đổi theo cảm xúc. */
export function PersonaFace({ hue, hair, emotion = "happy", size = 48, label }: { hue: number; hair?: string; emotion?: Emotion; size?: number; label?: string }) {
  const blush = emotion === "shy" || emotion === "happy" ? emotion === "shy" ? 0.75 : 0.4 : 0;
  return (
    <svg className="personaFace" width={size} height={size} viewBox="0 0 100 100" role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
      <rect width="100" height="100" fill={`hsl(${hue} 55% 82%)`} />
      <circle cx="82" cy="18" r="22" fill={`hsl(${(hue + 40) % 360} 60% 88%)`} />
      <path d="M14 104c4-20 18-28 36-28s32 8 36 28z" fill={`hsl(${hue} 50% 46%)`} />
      <ellipse cx="50" cy="60" rx="24" ry="26" style={{ fill: "var(--skin)" }} />
      <path d={hair || MODE_META.assistant_general.hair} fill={`hsl(${hue} 30% 24%)`} />
      {blush > 0 && <><ellipse cx="33" cy="66" rx="5.5" ry="3" fill="#E98A8A" opacity={blush} /><ellipse cx="67" cy="66" rx="5.5" ry="3" fill="#E98A8A" opacity={blush} /></>}
      <g fill="#2b2420" stroke="#2b2420" strokeLinecap="round" dangerouslySetInnerHTML={{ __html: EYES[emotion] }} />
      <g fill="none" stroke="#7a3b35" strokeLinecap="round" dangerouslySetInnerHTML={{ __html: MOUTH[emotion] }} />
    </svg>
  );
}

/** Avatar của trợ lý: gương mặt persona theo màu và kiểu tóc của từng trợ lý. */
export function ModeAvatar({ mode, size = 28, emotion = "happy" }: { mode: string; size?: number; emotion?: Emotion }) {
  const meta = metaOf(mode);
  return (
    <span className="modeAvatar" style={{ width: size, height: size }}>
      <PersonaFace hue={meta.hue} hair={meta.hair} emotion={emotion} size={size} />
    </span>
  );
}

/** Ảnh minh họa cho thẻ trợ lý: nền gradient theo màu trợ lý và tranh vẽ riêng. */
export function ModeIllustration({ mode }: { mode: string }) {
  const meta = metaOf(mode);
  const gradientId = `illu-${useId().replace(/:/g, "")}`;
  const art = ILLUSTRATIONS[mode as AssistantModeId];
  const style: CSSProperties = { display: "block", width: "100%", height: "100%" };
  if (!art)
    return (
      <span className="modeIllustration" style={{ background: `linear-gradient(150deg, hsl(${meta.hue} 58% 62%), hsl(${(meta.hue + 35) % 360} 55% 46%))` }} aria-hidden="true">
        <span className="modeIllustrationOrb" />
        <span className="modeIllustrationIcon" style={{ color: `hsl(${meta.hue} 50% 38%)` }}><Icon n={meta.icon} /></span>
      </span>
    );
  return (
    <span className="modeIllustration" aria-hidden="true">
      <svg viewBox="0 0 128 88" preserveAspectRatio="xMidYMid slice" style={style}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={`hsl(${meta.hue} 60% 62%)`} />
            <stop offset="1" stopColor={`hsl(${(meta.hue + 35) % 360} 55% 48%)`} />
          </linearGradient>
        </defs>
        <rect width="128" height="88" fill={`url(#${gradientId})`} />
        <circle cx="118" cy="84" r="34" fill="#fff" opacity=".12" />
        <circle cx="6" cy="6" r="22" fill="#fff" opacity=".1" />
        <g dangerouslySetInnerHTML={{ __html: art }} />
      </svg>
    </span>
  );
}
