import { useEffect, useState } from "react";
import type { Message } from "./types";
import { API, authHeaders } from "./api";

export const expressionPortraitCache = new Map<string, string>();
const expressionPortraitRequests = new Map<string, Promise<string>>();
const EXPRESSION_CACHE_VERSION = "4";
const expressionPortraitKey = (characterId: string, emotion: string) =>
  `${EXPRESSION_CACHE_VERSION}:${characterId}:${emotion}`;
export async function loadExpressionPortrait(
  characterId: string,
  emotion: NonNullable<Message["emotion"]>,
): Promise<string> {
  const key = expressionPortraitKey(characterId, emotion);
  const cached = expressionPortraitCache.get(key);
  if (cached) return cached;
  const pending = expressionPortraitRequests.get(key);
  if (pending) return pending;
  const request = (async () => {
    const response = await fetch(
      `${API}/v1/characters/${characterId}/expression/${emotion}?v=${EXPRESSION_CACHE_VERSION}`,
      { headers: authHeaders() },
    );
    if (!response.ok) throw new Error(String(response.status));
    const url = URL.createObjectURL(await response.blob());
    expressionPortraitCache.set(key, url);
    return url;
  })().finally(() => expressionPortraitRequests.delete(key));
  expressionPortraitRequests.set(key, request);
  return request;
}
export function EmotionPortrait({
  characterId,
  emotion,
  name,
}: {
  characterId: string;
  emotion: NonNullable<Message["emotion"]>;
  name: string;
}) {
  const key = expressionPortraitKey(characterId, emotion);
  const [src, setSrc] = useState<string | undefined>(() =>
    expressionPortraitCache.get(key),
  );
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const url = await loadExpressionPortrait(characterId, emotion);
        if (!cancelled) setSrc(url);
      } catch {
        // The message pipeline retries by keeping the typing state visible.
      }
    };
    const cached = expressionPortraitCache.get(key);
    if (cached) setSrc(cached);
    load();
    return () => {
      cancelled = true;
    };
  }, [characterId, emotion, key]);
  const readySrc = expressionPortraitCache.get(key) || src;
  return (
    <div className="emotionPortraitWrap">
      {readySrc && (
        <img
          className="emotionPortrait"
          src={readySrc}
          alt={`Chân dung biểu cảm ${name}`}
        />
      )}
    </div>
  );
}
