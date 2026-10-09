/** Keep the current/next song in memory so playback does not depend on new range requests. */
export class MusicTrackCache {
  private entries = new Map<string, Promise<string>>();
  private urls = new Map<string, string>();
  private controllers = new Set<AbortController>();
  private disposed = false;
  ready(url: string): string | undefined {
    return this.urls.get(url);
  }
  async get(url: string): Promise<string> {
    if (this.disposed) return url;
    const existing = this.entries.get(url);
    if (existing) {
      this.entries.delete(url); this.entries.set(url, existing);
      return existing;
    }
    const controller = new AbortController();
    this.controllers.add(controller);
    const timer = setTimeout(() => controller.abort(), 60000);
    const work = (async () => {
      try {
        const response = await fetch(url, {signal: controller.signal, cache: "default"});
        if (!response.ok) throw new Error("Music download failed");
        // Large songs keep native streaming rather than consuming unbounded RAM.
        if (Number(response.headers.get("content-length")) > 24 * 1024 * 1024) {
          await response.body?.cancel();
          return url;
        }
        const blob = await response.blob();
        if (this.disposed || !this.entries.has(url) || blob.size > 24 * 1024 * 1024) return url;
        const objectUrl = URL.createObjectURL(blob);
        this.urls.set(url, objectUrl);
        return objectUrl;
      } catch {
        // Preloading is optional: fall back to the original playable URL.
        this.entries.delete(url);
        return url;
      } finally {
        clearTimeout(timer); this.controllers.delete(controller);
      }
    })();
    this.entries.set(url, work);
    while (this.entries.size > 2) {
      const oldest = this.entries.keys().next().value!;
      this.entries.delete(oldest);
      const objectUrl = this.urls.get(oldest);
      if (objectUrl) { URL.revokeObjectURL(objectUrl); this.urls.delete(oldest); }
    }
    return work;
  }
  dispose() {
    this.disposed = true;
    for (const controller of this.controllers) controller.abort();
    for (const objectUrl of this.urls.values()) URL.revokeObjectURL(objectUrl);
    this.controllers.clear(); this.urls.clear(); this.entries.clear();
  }
}
