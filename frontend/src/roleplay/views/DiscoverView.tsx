/** discover view. Hooks, requests and playback remain owned by RolePlayApp. */
import type * as React from "react";
import { api } from "../api";
import { assetUrl } from "../CharacterCards";
import type { Character, Room } from "../types";

export type DiscoverViewProps = {
  collectionTabs: (
    current: "system" | "characters" | "discover",
  ) => React.JSX.Element;
  searchField: React.JSX.Element;
  publicFilter: string;
  setPublicFilter: React.Dispatch<React.SetStateAction<string>>;
  publicCategories: readonly [
    readonly ["all", "Tất cả"],
    readonly ["companion", "Đồng hành"],
    readonly ["study", "Học tập"],
    readonly ["work", "Công việc"],
    readonly ["entertainment", "Giải trí"],
    readonly ["roleplay", "Role play"],
  ];
  publicRatingFilter: number;
  setPublicRatingFilter: React.Dispatch<React.SetStateAction<number>>;
  catalogView: string;
  filteredPublicCharacters: import("../types").Character[];
  matchingPublicRooms: Room[];
  catalogSections: React.JSX.Element;
  act: (
    f: () => Promise<void>,
    preparesResources?: boolean,
    successMessage?: string,
  ) => Promise<void>;
  setNotice: React.Dispatch<React.SetStateAction<string>>;
  refresh: () => Promise<void>;
  introText: (value: string) => string;
  setChars: React.Dispatch<
    React.SetStateAction<import("../types").Character[]>
  >;
  setPage: React.Dispatch<
    React.SetStateAction<
      | "system"
      | "characters"
      | "discover"
      | "home"
      | "create"
      | "rooms"
      | "chat"
      | "memories"
      | "experiences"
    >
  >;
  favoriteButton: (c: import("../types").Character) => React.JSX.Element;
};

export function renderDiscoverView(props: DiscoverViewProps) {
  const {
    collectionTabs,
    searchField,
    publicFilter,
    setPublicFilter,
    publicCategories,
    publicRatingFilter,
    setPublicRatingFilter,
    catalogView,
    filteredPublicCharacters,
    matchingPublicRooms,
    catalogSections,
    act,
    setNotice,
    refresh,
    introText,
    setChars,
    setPage,
    favoriteButton,
  } = props;
  return (
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
            {filteredPublicCharacters.length +
              (catalogView === "all" ? matchingPublicRooms.length : 0)}{" "}
            kết quả
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
                        await api(`/v1/characters/${c.id}/reaction`, "PUT", {
                          reaction: emoji,
                        });
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

      {catalogView !== "team" &&
        !filteredPublicCharacters.length &&
        !(catalogView === "all" && matchingPublicRooms.length) && (
          <div className="emptyState">Chưa có nhân vật public phù hợp.</div>
        )}
    </>
  );
}
