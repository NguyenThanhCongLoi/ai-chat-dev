import {friendlyLanguageLoadingText} from "./friendlyUiCopy";
import { useEffect, useRef, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import {
  subscribeUiLanguageLoading,
  uiLanguageLoadingSnapshot,
} from "./uiLocales";
import { RolePlayLoadingCat } from "./roleplay/RolePlayLoadingCat";

export function UiLanguageLoading() {
  const state = useSyncExternalStore(
    subscribeUiLanguageLoading,
    uiLanguageLoadingSnapshot,
  );
  const panel = useRef<HTMLDivElement>(null);
  const blocked = state.busy || Boolean(state.error);
  useEffect(() => {
    if (!blocked) return;
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    return () => {
      if (previous?.isConnected) previous.focus();
    };
  }, [blocked]);
  if (!blocked) return null;
  return createPortal(
    <div
      className="uiLanguageLoading"
      role="dialog"
      aria-modal="true"
      aria-labelledby="uiLanguageLoadTitle"
    >
      <div className="uiLanguageLoadingCard" ref={panel} tabIndex={-1}>
        {!state.error && <RolePlayLoadingCat />}
        <b id="uiLanguageLoadTitle" data-no-translate="true" translate="no">
          {state.error
            ? "Translation incomplete"
            : friendlyLanguageLoadingText(state.language)}
        </b>
        <small>{state.language}</small>
        {state.error && <p role="alert">{state.error}</p>}
        <div className="uiLanguageLoadingActions">
          {state.error && (
            <button type="button" onClick={state.retry}>
              Retry
            </button>
          )}
          <button type="button" onClick={state.cancel}>
            Vietnamese (vi)
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
