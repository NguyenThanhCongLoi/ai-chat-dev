/** characters view. Hooks, requests and playback remain owned by RolePlayApp. */
import type * as React from "react";
import { Icon } from "../../ui";
import { api } from "../api";
import { CharacterAvatar, reactionEmojis } from "../CharacterCards";
import { roleLabels } from "../presentation";
import type { Room } from "../types";

export type CharactersViewProps = {
  collectionTabs: (
    current: "system" | "characters" | "discover",
  ) => React.JSX.Element;
  searchField: React.JSX.Element;
  myCharacterFilter: string;
  setMyCharacterFilter: React.Dispatch<React.SetStateAction<string>>;
  myCharacterTypeFilter: string;
  setMyCharacterTypeFilter: React.Dispatch<React.SetStateAction<string>>;
  ownedTypes: string[];
  catalogView: string;
  filteredOwned: import("../types").Character[];
  catalogSections: React.JSX.Element;
  catalogCharacterType: (character: import("../types").Character) => string;
  act: (
    f: () => Promise<void>,
    preparesResources?: boolean,
    successMessage?: string,
  ) => Promise<void>;
  reactCharacter: (characterId: string, reaction: string) => Promise<void>;
  introText: (value: string) => string;
  favoriteButton: (c: import("../types").Character) => React.JSX.Element;
  busy: boolean;
  startCharacterChat: (
    character: import("../types").Character,
  ) => Promise<void>;
  openRoleplayMemories: (target: {
    kind: "character" | "room";
    id: string;
    label: string;
  }) => Promise<void>;
  setCharacterInfo: React.Dispatch<
    React.SetStateAction<{ ids: string[]; id: string } | null>
  >;
  setChars: React.Dispatch<
    React.SetStateAction<import("../types").Character[]>
  >;
  setRooms: React.Dispatch<React.SetStateAction<Room[]>>;
  matchingOwnedRooms: Room[];
  visibleCharacters: import("../types").Character[];
};

export function renderCharactersView(props: CharactersViewProps) {
  const {
    collectionTabs,
    searchField,
    myCharacterFilter,
    setMyCharacterFilter,
    myCharacterTypeFilter,
    setMyCharacterTypeFilter,
    ownedTypes,
    catalogView,
    filteredOwned,
    catalogSections,
    catalogCharacterType,
    act,
    reactCharacter,
    introText,
    favoriteButton,
    busy,
    startCharacterChat,
    openRoleplayMemories,
    setCharacterInfo,
    setChars,
    setRooms,
    matchingOwnedRooms,
    visibleCharacters,
  } = props;
  return (
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
            onChange={(event) => setMyCharacterTypeFilter(event.target.value)}
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
          <span className="chip rpCount">{filteredOwned.length} nhân vật</span>
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
              {roleLabels[catalogCharacterType(c) as keyof typeof roleLabels] ||
                catalogCharacterType(c)}{" "}
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
                onClick={() => setCharacterInfo({ ids: [c.id], id: c.id })}
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

      {catalogView !== "team" &&
        !filteredOwned.length &&
        !(catalogView === "all" && matchingOwnedRooms.length) && (
          <div className="empty">
            {visibleCharacters.length
              ? "Không có nhân vật nào khớp bộ lọc."
              : "Bạn chưa có nhân vật nào. Thêm từ tab Nhân vật hệ thống hoặc mở Sáng tạo nhân vật."}
          </div>
        )}
    </>
  );
}
