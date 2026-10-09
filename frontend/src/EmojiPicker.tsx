import { useEffect, useRef, useState } from "react";

const EMOJIS = [0x1f600, 0x1f604, 0x1f602, 0x1f60a, 0x1f60d, 0x1f970, 0x1f618, 0x1f609, 0x1f60e, 0x1f914, 0x1f97a, 0x1f62d, 0x1f624, 0x1f633, 0x1f643, 0x1f634, 0x2764, 0x1f9e1, 0x1f49b, 0x1f49a, 0x1f499, 0x1f49c, 0x1f495, 0x2728, 0x1f44d, 0x1f44f, 0x1f64c, 0x1f64f, 0x1f44b, 0x1f91d, 0x1f525, 0x1f389].map((point) => String.fromCodePoint(point));

export function EmojiPicker({ onSelect, disabled = false }: {
  onSelect: (emoji: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="chatEmojiPicker" ref={root}>
      <button
        type="button"
        className="chatEmojiToggle"
        disabled={disabled}
        aria-label="Emoji"
        aria-expanded={open}
        title="Emoji"
        onClick={() => setOpen((value) => !value)}
      >
        <span aria-hidden="true">{"\u263A"}</span>
      </button>
      {open && (
        <div className="chatEmojiPanel" role="group" aria-label="Emoji">
          {EMOJIS.map((emoji) => (
            <button
              type="button"
              key={emoji}
              aria-label={emoji}
              title={emoji}
              onClick={() => {
                onSelect(emoji);
                setOpen(false);
              }}
            >
              {emoji}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
