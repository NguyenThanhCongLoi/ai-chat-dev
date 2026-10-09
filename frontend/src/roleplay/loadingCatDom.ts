import { createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { RolePlayLoadingCat } from "./RolePlayLoadingCat";

const mounted = new Map<HTMLElement, Root>();
const observer = new MutationObserver(() => {
  for (const [holder, root] of mounted) {
    if (!holder.isConnected) {
      mounted.delete(holder);
      queueMicrotask(() => root.unmount());
    }
  }
  if (!mounted.size) observer.disconnect();
});

/** Reuse the loader in CMS screens and dispose it when their DOM is replaced. */
export function mountLoadingCat(host: Element, size: "normal" | "compact" | "inline" = "normal") {
  const holder = document.createElement("span");
  host.prepend(holder);
  const root = createRoot(holder);
  mounted.set(holder, root);
  observer.observe(document.body, { childList: true, subtree: true });
  root.render(createElement(RolePlayLoadingCat, { size }));
}
