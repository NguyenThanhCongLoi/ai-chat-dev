import { useLayoutEffect, useRef, useState } from "react";
import "./roleplay-loading-cat.css";

const ACTIONS = ["walk", "run", "butterfly"] as const;
type Action = (typeof ACTIONS)[number];
const CLIPS = {
  walk: { frames: 12, frameMs: 160 },
  run: { frames: 10, frameMs: 120 },
  butterfly: { frames: 14, frameMs: 220 },
};
const WIDTH = 240;
const HEIGHT = 180;
const ROTATION_KEY = "avibi_loading_cat_next";
let nextAction = 0;
const sheets = new Map<Action, Promise<HTMLImageElement>>();

function loadSheet(action: Action) {
  let pending = sheets.get(action);
  if (!pending) {
    pending = new Promise<HTMLImageElement>((resolve, reject) => {
      const image = new Image();
      image.onload = () => image.decode().then(() => resolve(image), reject);
      image.onerror = () => reject(new Error(`Cannot load cat ${action}`));
      image.src = `/assets/loading-cat-${action}-sprite.webp`;
    });
    sheets.set(action, pending);
    void pending.catch(() => sheets.delete(action));
  }
  return pending;
}

function takeNextAction(): Action {
  try {
    // Platform and same-origin workspace frames share one sequence.
    const storage = window.top!.sessionStorage;
    const stored = Number(storage.getItem(ROTATION_KEY));
    const index = Number.isSafeInteger(stored) && stored >= 0 ? stored : 0;
    storage.setItem(ROTATION_KEY, String((index + 1) % ACTIONS.length));
    return ACTIONS[index % ACTIONS.length];
  } catch {
    return ACTIONS[nextAction++ % ACTIONS.length];
  }
}

export function RolePlayLoadingCat({ size = "normal" }: { size?: "normal" | "compact" | "inline" }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const actionRef = useRef<Action | null>(null);
  const [action, setAction] = useState<Action>("walk");

  useLayoutEffect(() => {
    // Allocate after commit; StrictMode effect replay reuses the clip.
    const selected = actionRef.current ?? (actionRef.current = takeNextAction());
    setAction(selected);
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = WIDTH * ratio;
    canvas.height = HEIGHT * ratio;
    context.scale(ratio, ratio);
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";

    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const clip = CLIPS[selected];
    let disposed = false;
    let request = 0;
    let elapsed = 0;
    let lastTime = 0;
    let sheet: HTMLImageElement | undefined;

    function draw(now: number) {
      if (disposed || !sheet || !context) return;
      if (lastTime) elapsed += Math.min(now - lastTime, 80);
      lastTime = now;
      const position = motion.matches ? 0 : elapsed / clip.frameMs;
      const frame = Math.floor(position) % clip.frames;
      // Briefly blend poses, including the loop boundary.
      const transition = Math.max(0, ((position % 1) - 0.7) / 0.3);
      const blend = transition * transition * (3 - 2 * transition);
      context.clearRect(0, 0, WIDTH, HEIGHT);
      context.globalAlpha = 1 - blend;
      context.drawImage(sheet, frame * WIDTH, 0, WIDTH, HEIGHT, 0, 0, WIDTH, HEIGHT);
      if (blend) {
        context.globalCompositeOperation = "lighter";
        context.globalAlpha = blend;
        context.drawImage(sheet, ((frame + 1) % clip.frames) * WIDTH, 0, WIDTH, HEIGHT, 0, 0, WIDTH, HEIGHT);
      }
      context.globalAlpha = 1;
      context.globalCompositeOperation = "source-over";
      if (!motion.matches && !document.hidden) request = requestAnimationFrame(draw);
    }

    function resume() {
      cancelAnimationFrame(request);
      lastTime = 0;
      if (!document.hidden) draw(performance.now());
    }
    document.addEventListener("visibilitychange", resume);
    motion.addEventListener("change", resume);
    for (const item of ACTIONS) void loadSheet(item).catch(() => {});
    void loadSheet(selected).then((image) => {
      if (disposed) return;
      sheet = image;
      resume();
    }).catch(() => {});

    return () => {
      disposed = true;
      cancelAnimationFrame(request);
      document.removeEventListener("visibilitychange", resume);
      motion.removeEventListener("change", resume);
    };
  }, []);

  return <span className={`roleplayLoadingCat roleplayLoadingCat--${size}`} data-motion={action} aria-hidden="true">
    <canvas ref={canvasRef} />
  </span>;
}
