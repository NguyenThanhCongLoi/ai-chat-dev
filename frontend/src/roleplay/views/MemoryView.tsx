/** memory view. Hooks, requests and playback remain owned by RolePlayApp. */
import type * as React from "react";
import { Icon } from "../../ui";
import { api } from "../api";

export type MemoryViewProps = {
  setMemoryPopupOpen: React.Dispatch<React.SetStateAction<boolean>>;
  memoryTarget: NonNullable<{
    kind: "character" | "room";
    id: string;
    label: string;
  }>;
  memoryDraft: string;
  setMemoryDraft: React.Dispatch<React.SetStateAction<string>>;
  busy: boolean;
  act: (
    f: () => Promise<void>,
    preparesResources?: boolean,
    successMessage?: string,
  ) => Promise<void>;
  addRoleplayMemory: () => Promise<void>;
  memories: { id: string; content: string; pinned: boolean }[];
  setMemories: React.Dispatch<
    React.SetStateAction<{ id: string; content: string; pinned: boolean }[]>
  >;
  setNotice: React.Dispatch<React.SetStateAction<string>>;
};

export function renderMemoryView(props: MemoryViewProps) {
  const {
    setMemoryPopupOpen,
    memoryTarget,
    memoryDraft,
    setMemoryDraft,
    busy,
    act,
    addRoleplayMemory,
    memories,
    setMemories,
    setNotice,
  } = props;
  return (
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
              Ký ức · {memoryTarget.kind === "room" ? "phòng nhóm" : "nhân vật"}
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
              Chưa có ký ức nào. Thêm điều bạn muốn {memoryTarget.label} ghi nhớ
              ở ô phía trên.
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
                        x.id === m.id ? { ...x, content: e.target.value } : x,
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
                              x.id === m.id ? { ...x, pinned: !x.pinned } : x,
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
  );
}
