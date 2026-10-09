import type { Character } from "./types";

export const reactionEmojis = ["❤️", "😂", "🔥", "👍", "😮"] as const;
export const reactionTotal = (character: Character) =>
  Object.values(character.reactions || {}).reduce(
    (sum, count) => sum + count,
    0,
  );
const API = import.meta.env.VITE_API_URL || "";
export const assetUrl = (value?: string | null): string | undefined =>
  value
    ? /^(https?:|data:|blob:)/.test(value)
      ? value
      : API + value
    : undefined;
export function MarketCard({
  character,
  introduction,
  onOpen,
}: {
  character: Character;
  introduction?: string;
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
        <b data-no-translate="true" translate="no">{character.name}</b>
        <small>bởi {character.creator?.name ? <span data-no-translate="true" translate="no">{character.creator.name}</span> : "Người dùng"}</small>
        <p data-no-translate="true" translate="no">{introduction ?? character.description}</p>
        <em>
          ★ {character.rating || "Mới"} · ◉ {character.usage_count || 0} lượt
          dùng
        </em>
        <ReactionSummary character={character} />
      </span>
    </button>
  );
}
export function ReactionSummary({ character }: { character: Character }) {
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
export function CharacterAvatar({
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
export function CommunityShowcase({
  character,
  introduction,
  onOpen,
}: {
  character: Character;
  introduction?: string;
  onOpen: () => void;
}) {
  return (
    <button className="card characterIntro showcaseCard" onClick={onOpen}>
      <CharacterAvatar character={character} className="showcaseImage" />
      <div className="showcaseCopy">
        <span className="roleBadge companion">
          {character.character_type || "Cộng đồng"}
        </span>
        <strong data-no-translate="true" translate="no">{character.name}</strong>
        <h3>bởi {character.creator?.name ? <span data-no-translate="true" translate="no">{character.creator.name}</span> : "Người dùng"}</h3>
        <p data-no-translate="true" translate="no">{introduction ?? character.description}</p>
        <span className="showcaseMeta">
          ★ {character.rating || "Mới"} · ◉ {character.usage_count || 0} lượt
          dùng <b>Xem →</b>
        </span>
        <ReactionSummary character={character} />
      </div>
    </button>
  );
}
