import { ElfCompanion } from "../ElfCompanion";
import { hasElfCompanion } from "../companionState";
/** chat view. Hooks, requests and playback remain owned by RolePlayApp. */
import type * as React from "react";
import { EmojiPicker } from "../../EmojiPicker";
import { AutoGrowTextarea, Icon } from "../../ui";
import { BackgroundMusicButton } from "../BackgroundMusicButton";
import { CharacterAvatar } from "../CharacterCards";
import { CharacterFeelings } from "../CharacterFeelings";
import { EmotionPortrait } from "../EmotionPortrait";
import { renderRoleplayText } from "../presentation";
import type { Room } from "../types";
import { canSpeak } from "../voicePreferences";

export type ChatViewProps = {
  companionVisible: boolean;
  setCompanionVisible: React.Dispatch<React.SetStateAction<boolean>>;
  companionIsTalking: boolean;
  chatToolsCollapsed: boolean;
  typingIds: string[];
  activeExpression: NonNullable<
    | "neutral"
    | "happy"
    | "sad"
    | "angry"
    | "surprised"
    | "shy"
    | "thinking"
    | undefined
  >;
  roomChars: import("../types").Character[];
  room: NonNullable<Room>;
  messagesBox: React.RefObject<HTMLDivElement | null>;
  messages: import("../types").Message[];
  chars: import("../types").Character[];
  presets: import("../types").Character[];
  publicCharacters: import("../types").Character[];
  speakingId: string | null;
  playRoleplayMessage: (messageId: string) => void;
  speechLoadingId: string | null;
  busy: boolean;
  regenerateMessage: (message: import("../types").Message) => Promise<void>;
  send: (suggestedText?: string | undefined) => Promise<void>;
  messagesEnd: React.RefObject<HTMLDivElement | null>;
  text: string;
  setText: React.Dispatch<React.SetStateAction<string>>;
  setChatToolsCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  introText: (value: string) => string;
  act: (
    f: () => Promise<void>,
    preparesResources?: boolean,
    successMessage?: string,
  ) => Promise<void>;
  reactCharacter: (characterId: string, reaction: string) => Promise<void>;
  openRoomWizard: (preselected?: string[]) => void;
  openRoleplayMemories: (target: {
    kind: "character" | "room";
    id: string;
    label: string;
  }) => Promise<void>;
  setCharacterInfo: React.Dispatch<
    React.SetStateAction<{ ids: string[]; id: string } | null>
  >;
  backgroundMusic: {
    enabled: boolean;
    playing: boolean;
    loading: boolean;
    available: boolean;
    error: boolean;
    volume: number;
    changeVolume: (value: number) => void;
    toggle: () => void;
  };
  reactionSounds: {
    enabled: boolean;
    ready: boolean;
    available: boolean;
    toggle: () => void;
    react: (
      messageId: string,
      characterId: string,
      emotion: string,
      language?: string | undefined,
      voiceId?: string | undefined,
    ) => Promise<void>;
    opening: (
      characterId: string,
      language?: string | undefined,
      voiceId?: string | undefined,
    ) => Promise<void>;
    stop: () => void;
  };
  actionSounds: {
    feed: (messageId: string, delta: string) => void;
    finish: (messageId: string, text: string) => void;
    stop: () => void;
    available: boolean;
    ready: boolean;
  };
};

export function renderChatView(props: ChatViewProps) {
  const {
    companionVisible,
    setCompanionVisible,
    companionIsTalking,
    chatToolsCollapsed,
    typingIds,
    activeExpression,
    roomChars,
    room,
    messagesBox,
    messages,
    chars,
    presets,
    publicCharacters,
    speakingId,
    playRoleplayMessage,
    speechLoadingId,
    busy,
    regenerateMessage,
    send,
    messagesEnd,
    text,
    setText,
    setChatToolsCollapsed,
    introText,
    act,
    reactCharacter,
    openRoomWizard,
    openRoleplayMemories,
    setCharacterInfo,
    backgroundMusic,
    reactionSounds,
    actionSounds,
  } = props;
  const companionAvailable = !chatToolsCollapsed && roomChars.length === 1 && hasElfCompanion(roomChars[0]);
  const companionShown = companionAvailable && companionVisible;
  return (
    <div
      className={`chatWorkspace ${chatToolsCollapsed ? "toolsCollapsed" : ""} ${companionShown ? "companionExpanded" : ""}`}
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
                    <div className={`documentMessage ${m.attachment.status}`}>
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
                        "bubble " + (m.sender_type === "user" ? "mine" : "")
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

                  {isLatestCharacter &&
                    !!m.suggestions?.length &&
                    (roomChars.length < 2 || !busy) && (
                      <div
                        className={
                          roomChars.length > 1
                            ? "suggestions groupSuggestionRow"
                            : "suggestions"
                        }
                      >
                        {m.suggestions.slice(0, 3).map((suggestion, index) => (
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
                onSelect={(emoji) => setText((current) => current + emoji)}
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

      <aside className={`characterTools ${companionAvailable ? "companionAvailable" : ""} ${companionShown ? "companionFull" : ""}`}>
        <button
          className="iconbtn collapseTools"
          onClick={() => setChatToolsCollapsed((value) => !value)}
        >
          <Icon
            n={chatToolsCollapsed ? "angle-small-left" : "angle-small-right"}
          />
        </button>

        {companionAvailable && (
          <button className="iconbtn companionToggle" type="button"
            title={companionVisible ? "Ẩn companion" : "Hiện companion"}
            aria-label={companionVisible ? "Ẩn companion" : "Hiện companion"}
            aria-pressed={companionVisible}
            onClick={() => setCompanionVisible(value => !value)}>
            <Icon n={companionVisible ? "eye-crossed" : "eye"} />
          </button>
        )}
        {companionShown ? (
          <ElfCompanion name={roomChars[0].name} talking={companionIsTalking} />
        ) : !chatToolsCollapsed && (
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

                  <span>◉ {roomChars[0].usage_count || 0} người dùng</span>
                </div>
              </div>
            )}

            {roomChars.length === 1 && room && (
              <CharacterFeelings
                characterId={roomChars[0].id}
                roomId={room.id}
                revision={
                  messages
                    .filter((message) => message.sender_type === "character")
                    .at(-1)?.id || ""
                }
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
  );
}
