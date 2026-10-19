/** create view. Hooks, requests and playback remain owned by RolePlayApp. */
import type * as React from "react";
import { Icon } from "../../ui";
import { api } from "../api";
import { suggestedTags } from "../presentation";
import type { Character, StoryCandidate } from "../types";

export type CreateViewProps = {
  mode: string;
  setMode: React.Dispatch<React.SetStateAction<string>>;
  openRoomWizard: (preselected?: string[]) => void;
  avatarFile: File | null;
  setAvatarFile: React.Dispatch<React.SetStateAction<File | null>>;
  name: string;
  setName: React.Dispatch<React.SetStateAction<string>>;
  description: string;
  setDescription: React.Dispatch<React.SetStateAction<string>>;
  existingMediaCharacter: boolean;
  setExistingMediaCharacter: React.Dispatch<React.SetStateAction<boolean>>;
  mediaCharacterName: string;
  setMediaCharacterName: React.Dispatch<React.SetStateAction<string>>;
  mediaTitle: string;
  setMediaTitle: React.Dispatch<React.SetStateAction<string>>;
  customRole: string;
  setCustomRole: React.Dispatch<React.SetStateAction<string>>;
  characterType: string;
  setCharacterType: React.Dispatch<React.SetStateAction<string>>;
  selectedTags: string[];
  toggleTag: (tag: string) => void;
  tagSearch: string;
  setTagSearch: React.Dispatch<React.SetStateAction<string>>;
  makePublic: boolean;
  setMakePublic: React.Dispatch<React.SetStateAction<boolean>>;
  customScenario: string;
  setCustomScenario: React.Dispatch<React.SetStateAction<string>>;
  customGreeting: string;
  setCustomGreeting: React.Dispatch<React.SetStateAction<string>>;
  customExamples: string;
  setCustomExamples: React.Dispatch<React.SetStateAction<string>>;
  busy: boolean;
  act: (
    f: () => Promise<void>,
    preparesResources?: boolean,
    successMessage?: string,
  ) => Promise<void>;
  finishCreatedCharacter: (
    character: import("../types").Character,
  ) => Promise<void>;
  storyDocument: { id: string; filename: string } | null;
  storyFile: File | null;
  setStoryFile: React.Dispatch<React.SetStateAction<File | null>>;
  storyUrl: string;
  setStoryUrl: React.Dispatch<React.SetStateAction<string>>;
  prepareStorySource: () => Promise<void>;
  storyCandidates: StoryCandidate[];
  storyCharacterName: string;
  setStoryCharacterName: React.Dispatch<React.SetStateAction<string>>;
  setStoryDocument: React.Dispatch<
    React.SetStateAction<{ id: string; filename: string } | null>
  >;
  setStoryCandidates: React.Dispatch<React.SetStateAction<StoryCandidate[]>>;
  createStoryCharacter: () => Promise<void>;
};

export function renderCreateView(props: CreateViewProps) {
  const {
    mode,
    setMode,
    openRoomWizard,
    avatarFile,
    setAvatarFile,
    name,
    setName,
    description,
    setDescription,
    existingMediaCharacter,
    setExistingMediaCharacter,
    mediaCharacterName,
    setMediaCharacterName,
    mediaTitle,
    setMediaTitle,
    customRole,
    setCustomRole,
    characterType,
    setCharacterType,
    selectedTags,
    toggleTag,
    tagSearch,
    setTagSearch,
    makePublic,
    setMakePublic,
    customScenario,
    setCustomScenario,
    customGreeting,
    setCustomGreeting,
    customExamples,
    setCustomExamples,
    busy,
    act,
    finishCreatedCharacter,
    storyDocument,
    storyFile,
    setStoryFile,
    storyUrl,
    setStoryUrl,
    prepareStorySource,
    storyCandidates,
    storyCharacterName,
    setStoryCharacterName,
    setStoryDocument,
    setStoryCandidates,
    createStoryCharacter,
  } = props;
  return (
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
          <button className="btn primary" onClick={() => openRoomWizard()}>
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
                    onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
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
                onChange={(e) => setExistingMediaCharacter(e.target.checked)}
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
                    onChange={(e) => setMediaCharacterName(e.target.value)}
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
                  AI sẽ tham khảo nguồn công khai về nhân vật này; mô tả của bạn
                  vẫn được ưu tiên.
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
                Tags <small className="faint">({selectedTags.length}/8)</small>
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
            <p>Nhân vật được lưu riêng tư. Hiện chỉ nhân vật hệ thống được công khai.</p>
              <label className="row switchRow" style={{display:"none"}} aria-hidden="true">
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
                Hệ thống đọc nội dung, tìm nhân vật trong truyện, rồi tạo tính
                cách và cách nói dựa trên các đoạn có nhân vật đó.
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
                        storyCharacterName === candidate.name ? "selected" : ""
                      }
                    >
                      <input
                        type="radio"
                        name="story-candidate"
                        checked={storyCharacterName === candidate.name}
                        onChange={() => setStoryCharacterName(candidate.name)}
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
                            {candidate.source_evidence.slice(0, 2).join(" · ")}
                          </q>
                        )}
                      </span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="muted" style={{ margin: 0 }}>
                  Chưa tự tìm thấy nhân vật. Hãy nhập tên nhân vật xuất hiện
                  trong truyện.
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
  );
}
