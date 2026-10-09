// Route music through Web Audio: iOS does not support changing media.volume.
export class MusicAudio {
  private context: AudioContext | null = null;
  private source: MediaElementAudioSourceNode | null = null;
  private gain: GainNode | null = null;
  private level = .3;
  constructor(private audio: HTMLAudioElement) {
    audio.crossOrigin = "anonymous"; // Must be set before assigning src.
  }
  setVolume(value: number) {
    this.level = Math.max(0, Math.min(1, value));
    if (this.gain && this.context)
      this.gain.gain.setTargetAtTime(this.level, this.context.currentTime, .02);
    else this.audio.volume = this.level;
  }
  play() {
    if (!this.context) {
      const Constructor = window.AudioContext ||
        (window as unknown as {webkitAudioContext?: typeof AudioContext}).webkitAudioContext;
      if (Constructor) {
        const context = new Constructor();
        try {
          const gain = context.createGain();
          const source = context.createMediaElementSource(this.audio);
          source.connect(gain); gain.connect(context.destination);
          this.context = context; this.gain = gain; this.source = source;
          this.audio.volume = 1;
          gain.gain.setValueAtTime(this.level, context.currentTime);
        } catch {
          void context.close().catch(() => {});
        }
      }
    }
    // Invoke resume and play synchronously in the gesture, without awaiting fetch.
    if (this.context && this.context.state !== "running")
      void this.context.resume().catch(() => {});
    return this.audio.play();
  }
  dispose() {
    this.source?.disconnect(); this.gain?.disconnect();
    if (this.context) void this.context.close().catch(() => {});
    this.source = null; this.gain = null; this.context = null;
  }
}
