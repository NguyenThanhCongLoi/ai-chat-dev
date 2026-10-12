/** system view. Hooks, requests and playback remain owned by RolePlayApp. */
import type * as React from "react";
import { Icon } from "../../ui";
import { CharacterAvatar } from "../CharacterCards";
import { roleLabels } from "../presentation";

export type SystemViewProps = {
  collectionTabs: (
    current: "system" | "characters" | "discover",
  ) => React.JSX.Element;
  searchField: React.JSX.Element;
  systemTypeFilter: string;
  setSystemTypeFilter: React.Dispatch<React.SetStateAction<string>>;
  catalogView: string;
  filteredSystem: import("../types").Character[];
  catalogSections: React.JSX.Element;
  introText: (value: string) => string;
  favoriteButton: (c: import("../types").Character) => React.JSX.Element;
  busy: boolean;
  addPreset: (p: import("../types").Character) => Promise<void>;
  hasPreset: (preset: import("../types").Character) => boolean;
  addPresetOnly: (preset: import("../types").Character) => Promise<void>;
};

export function renderSystemView(props: SystemViewProps) {
  const {
    collectionTabs,
    searchField,
    systemTypeFilter,
    setSystemTypeFilter,
    catalogView,
    filteredSystem,
    catalogSections,
    introText,
    favoriteButton,
    busy,
    addPreset,
    hasPreset,
    addPresetOnly,
  } = props;
  return (
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
          <span className="chip rpCount">{filteredSystem.length} nhân vật</span>
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
  );
}
