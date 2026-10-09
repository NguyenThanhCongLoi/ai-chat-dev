
/** Client send -> first content delta and suggestion receipt, reported after persistence. */
export function reportFirstChunk(base: string, headers: Record<string, string>, messageId: string, milliseconds: number | undefined, suggestionMilliseconds?: number) {
  if (!messageId || (milliseconds === undefined && suggestionMilliseconds === undefined)) return;
  void fetch(base + "/v1/messages/" + encodeURIComponent(messageId) + "/timing", {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ client_first_chunk_ms: milliseconds === undefined ? undefined : Math.round(milliseconds), client_suggestion_ms: suggestionMilliseconds === undefined ? undefined : Math.round(suggestionMilliseconds) }),
    keepalive: true,
  }).catch(() => {});
}
