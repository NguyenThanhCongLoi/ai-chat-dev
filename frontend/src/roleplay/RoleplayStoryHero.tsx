import { useEffect, useLayoutEffect, useRef, useState, type ReactNode, type CSSProperties } from "react";
import { Icon } from "../ui";
import type { Character } from "./types";
import { assetUrl } from "./CharacterCards";

type Props = {
  characters: Character[];
  disabled?: boolean;
  reducedMotion?: boolean;
  musicControl?: ReactNode;
  onOpen: (character: Character) => void;
};

// Existing catalog order for now. The caller can supply trending order later.
export function RoleplayStoryHero({ characters, disabled, reducedMotion = false, musicControl, onOpen }: Props) {
  const [selected, setSelected] = useState(0);
  const [failedImages, setFailedImages] = useState<Set<string>>(() => new Set());
  const previousSlots = useRef(new Map<string, number>());
  const [visible, setVisible] = useState(() => document.visibilityState !== "hidden");
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotion = () => setPrefersReducedMotion(media.matches);
    const updateVisibility = () => setVisible(document.visibilityState !== "hidden");
    media.addEventListener("change", updateMotion);
    document.addEventListener("visibilitychange", updateVisibility);
    return () => {
      media.removeEventListener("change", updateMotion);
      document.removeEventListener("visibilitychange", updateVisibility);
    };
  }, []);
  const seen = new Set<string>();
  const portraits = characters.filter((character) => {
    const url = assetUrl(character.avatar_url);
    // Characters without a real portrait receive an emoji fallback in the
    // catalog. Those fallback images do not belong in the introduction.
    if (!url || /(?:^|\/)default_icons\//i.test(url) || failedImages.has(url) || seen.has(url)) return false;
    seen.add(url);
    return true;
  });
  const total = portraits.length;
  const current = total ? selected % total : 0;
  const slots = total >= 5 ? [-2, -1, 0, 1, 2]
    : total === 4 ? [-1, 0, 1, 2]
    : total === 3 ? [-1, 0, 1]
    : total === 2 ? [0, 1] : total === 1 ? [0] : [];
  useLayoutEffect(() => {
    previousSlots.current = new Map(slots.map((slot) => [portraits[(current + slot + total) % total].id, slot]));
  });
  useEffect(() => {
    if (total < 2 || !visible || disabled || reducedMotion || prefersReducedMotion) return;
    const timer = window.setTimeout(() => setSelected((current + 1) % total), 5000);
    return () => window.clearTimeout(timer);
  }, [total, current, visible, disabled, reducedMotion, prefersReducedMotion]);

  function move(direction: number) {
    if (total) setSelected((current + direction + total) % total);
  }
  return (
    <section className="rpStoryHero" aria-labelledby="rpStoryTitle">
      <div className="rpStoryCopy">
        <span className="eyebrow">CHAT BOT AI</span>
        <h1 id="rpStoryTitle">
          <span>Bước vào câu chuyện.</span>
          <span>Sống cùng nhân vật.</span>
        </h1>
        {musicControl}

      </div>
      {total > 0 && <div className="rpStoryShowcase">
        <span className="rpStorySparkle first" aria-hidden="true">✦</span>
        <span className="rpStorySparkle second" aria-hidden="true">✧</span>
        <span className="rpStorySparkle third" aria-hidden="true">✦</span>
        <button type="button" className="rpStoryArrow previous" onClick={() => move(-1)}
          disabled={total < 2} aria-label="Nhân vật trước">‹</button>
        <div className="rpStoryPortraits">
          {slots.map((slot) => {
            const character = portraits[(current + slot + total) % total];
            const style = {
              "--hero-slot": slot,
              "--hero-depth": Math.abs(slot),
              zIndex: 5 - Math.abs(slot),
            } as CSSProperties;
            const recycled = Math.abs((previousSlots.current.get(character.id) ?? slot) - slot) > 2;
            return <div className={"rpStoryPortrait " + (slot === 0 ? "featured " : "") + (recycled ? "recycled" : "")}
              key={character.id} style={style}>
              <button type="button" className="rpStoryGlass" disabled={disabled}
                onClick={() => slot === 0 ? onOpen(character) : move(slot)}>
                <img src={assetUrl(character.avatar_url)} alt="" decoding="async"
                  onError={() => {
                    const url = assetUrl(character.avatar_url);
                    if (url) setFailedImages((failed) => new Set([...failed, url]));
                  }} />
                <span className="rpStoryCaption">
                  <strong data-no-translate="true" translate="no">{character.display_name || character.name}</strong>
                  <small>
                    <span aria-hidden="true"><Icon n="comment-alt" /></span>
                    <span data-no-translate="true" translate="no">{character.usage_count || 0}</span>
                    <span>người dùng</span>
                  </small>
                </span>
              </button>
              <div className="rpStoryReflection" aria-hidden="true">
                <img src={assetUrl(character.avatar_url)} alt="" decoding="async" />
              </div>
            </div>;
          })}
        </div>
        <button type="button" className="rpStoryArrow next" onClick={() => move(1)}
          disabled={total < 2} aria-label="Nhân vật tiếp theo">›</button>
      </div>}
    </section>
  );
}
