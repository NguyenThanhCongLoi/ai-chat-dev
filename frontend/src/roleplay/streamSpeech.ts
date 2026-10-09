type SpeechEvent = {
  type?: string;
  audio?: string;
  format?: string;
  sample_rate?: number;
  error?: { message?: string } | string;
};

/** One gain and peak protection path for both PCM and cached media playback. */
export function createVoiceGain(context: BaseAudioContext) {
  const gain = context.createGain();
  const limiter = context.createDynamicsCompressor();
  limiter.threshold.value = -2;
  limiter.knee.value = 0;
  limiter.ratio.value = 20;
  limiter.attack.value = .001;
  limiter.release.value = .08;
  // Gentle saturation near full scale also bounds sudden transient peaks.
  const ceiling = context.createWaveShaper();
  const curve = new Float32Array(4097);
  for (let i = 0; i < curve.length; i++) {
    const x = i * 2 / (curve.length - 1) - 1;
    const magnitude = Math.abs(x);
    curve[i] = Math.sign(x) * (magnitude <= .95 ? magnitude : .95 + .05 * Math.tanh((magnitude - .95) / .05));
  }
  ceiling.curve = curve;
  gain.connect(limiter);
  limiter.connect(ceiling);
  ceiling.connect(context.destination);
  return {
    input: gain,
    setVolume(value: number) {
      const volume = Number.isFinite(value) ? Math.max(0, Math.min(2, value)) : .8;
      gain.gain.setTargetAtTime(volume, context.currentTime, .015);
    },
    disconnect() { gain.disconnect(); limiter.disconnect(); ceiling.disconnect(); },
  };
}

export class PcmStreamPlayer {
  private context = new AudioContext();
  private gain = createVoiceGain(this.context);
  private mediaSource: MediaElementAudioSourceNode | null = null;
  private sources = new Set<AudioBufferSourceNode>();
  private nextTime = 0;
  private done = false;
  private stopped = false;
  private finishResolve: (() => void) | null = null;

  constructor() {
    this.setVolume(.8);
  }
  setVolume(value:number) {
    this.gain.setVolume(value);
  }

  connectMedia(audio: HTMLAudioElement) {
    if (this.stopped) return;
    this.mediaSource?.disconnect();
    audio.volume = 1;
    this.mediaSource = this.context.createMediaElementSource(audio);
    this.mediaSource.connect(this.gain.input);
    this.activate();
  }

  activate() {
    void this.context.resume().catch(() => {});
  }

  async push(base64: string, sampleRate: number) {
    if (this.stopped) return;
    if (this.context.state !== "running") {
      await Promise.race([
        this.context.resume(),
        new Promise<never>((_, reject) => window.setTimeout(() => reject(new DOMException("Playback blocked", "NotAllowedError")), 1500)),
      ]);
      if ((this.context.state as string) !== "running") throw new DOMException("Playback blocked", "NotAllowedError");
    }
    if (this.stopped) return;
    if (!Number.isInteger(sampleRate) || sampleRate < 8000 || sampleRate > 96000)
      throw new Error("Sample rate TTS không hợp lệ.");
    const raw = atob(base64);
    if (!raw.length || raw.length % 2) throw new Error("Chunk PCM16 không hợp lệ.");
    const audio = this.context.createBuffer(1, raw.length / 2, sampleRate);
    const samples = audio.getChannelData(0);
    for (let i = 0; i < samples.length; i++) {
      const value = raw.charCodeAt(i * 2) | (raw.charCodeAt(i * 2 + 1) << 8);
      samples[i] = (value >= 0x8000 ? value - 0x10000 : value) / 0x8000;
    }
    const source = this.context.createBufferSource();
    source.buffer = audio;
    source.connect(this.gain.input);
    source.onended = () => {
      this.sources.delete(source);
      source.disconnect();
      if (this.done && !this.sources.size) this.finishResolve?.();
    };
    this.sources.add(source);
    this.nextTime = Math.max(this.nextTime, this.context.currentTime + 0.03);
    source.start(this.nextTime);
    this.nextTime += audio.duration;
    this.activate();
  }

  finish(): Promise<void> {
    this.done = true;
    if (!this.sources.size || this.stopped) return Promise.resolve();
    return new Promise((resolve) => { this.finishResolve = resolve; });
  }

  stop() {
    if (this.stopped) return;
    this.stopped = true;
    for (const source of this.sources) {
      try { source.stop(); } catch {}
      source.disconnect();
    }
    this.sources.clear();
    this.mediaSource?.disconnect();
    this.mediaSource = null;
    this.gain.disconnect();
    this.finishResolve?.();
    void this.context.close().catch(() => {});
  }
}

export async function playSseSpeech(
  response: Response,
  signal: AbortSignal,
  player: PcmStreamPlayer,
  onFirstChunk: () => void,
) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Không đọc được stream TTS.");
  const decoder = new TextDecoder();
  let pending = "";
  let receivedAudio = false;
  let receivedDone = false;
  try {
    while (true) {
      const { value, done } = await reader.read();
      pending = (pending + decoder.decode(value, { stream: !done })).replace(/\r\n/g, "\n");
      let boundary: number;
      while ((boundary = pending.indexOf("\n\n")) >= 0) {
        const block = pending.slice(0, boundary);
        pending = pending.slice(boundary + 2);
        const data = block.split("\n").filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart()).join("\n");
        if (!data) continue;
        const event = JSON.parse(data) as SpeechEvent;
        if (event.error) throw new Error(typeof event.error === "string" ? event.error : event.error.message || "TTS stream lỗi.");
        if (event.type === "speech.audio.delta") {
          if (event.format !== "pcm" || !event.audio) throw new Error("TTS gateway không trả về PCM.");
          await player.push(event.audio, Number(event.sample_rate));
          if (!receivedAudio) { receivedAudio = true; onFirstChunk(); }
        } else if (event.type === "speech.audio.done") {
          if (!receivedAudio) throw new Error("TTS stream kết thúc mà không có audio.");
          receivedDone = true;
          break;
        }
      }
      if (receivedDone || done) break;
    }
    if (!receivedDone) throw new Error("TTS stream kết thúc trước speech.audio.done.");
    await player.finish();
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  } finally {
    void reader.cancel().catch(() => {});
  }
}
