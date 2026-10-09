import { useEffect, useRef, useState } from "react";
import { API, api } from "./api";
import { MusicAudio } from "./musicAudio";
import { MusicTrackCache } from "./musicTrackCache";
import {savedMusicVolume,saveMusicVolume} from "./musicVolume";

type Track = { id: string; title: string; url: string };
const preferenceKey = "roleplay_background_music";
function shuffled(tracks: Track[], previous?: string): Track[] {
  const result = [...tracks];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  if (result.length > 1 && result[0].id === previous)
    [result[0], result[1]] = [result[1], result[0]];
  return result;
}

export function useBackgroundMusic(allowed: boolean, foregroundVoice: boolean, chatScope: string | null = null) {
  const [enabled, setEnabled] = useState(() => localStorage.getItem(preferenceKey) !== "off");
  // Chat mute is local to the visit; home keeps its saved preference.
  useEffect(() => {
    setEnabled(chatScope !== null || localStorage.getItem(preferenceKey) !== "off");
  }, [chatScope]);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [volume, setVolume] = useState(() => savedMusicVolume(localStorage));
  const lastAudibleVolume = useRef(volume > 0 ? volume : .3);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const musicRef = useRef<MusicAudio | null>(null);
  const queue = useRef<Track[]>([]);
  const last = useRef<string | undefined>(undefined);
  const available = tracks.length > 0;
  const [visible, setVisible] = useState(() => document.visibilityState !== "hidden" &&
    (!window.frameElement || window.frameElement.getAttribute("aria-hidden") !== "true"));
  const active = useRef(false);
  active.current = enabled && allowed && visible;
  useEffect(() => {
    const frame = window.frameElement;
    const update = () => setVisible(document.visibilityState !== "hidden" &&
      (!frame || frame.getAttribute("aria-hidden") !== "true"));
    const observer = new MutationObserver(update);
    if (frame) observer.observe(frame, {attributes: true, attributeFilter: ["aria-hidden"]});
    update();
    document.addEventListener("visibilitychange", update);
    return () => { observer.disconnect(); document.removeEventListener("visibilitychange", update); };
  }, []);
  useEffect(() => {
    if (!allowed) return;
    const controller = new AbortController();
    setLoading(true);
    api<{ tracks: Track[]; volume?: number }>("/v1/roleplay/background-music")
      .then((result) => {
        if (!controller.signal.aborted) { setTracks(result.tracks); setError(false); }
      })
      .catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [allowed]);
  useEffect(() => {
    if (!allowed || !available) return;
    const audio = new Audio();
    audio.preload = "auto";
    const music = new MusicAudio(audio);
    music.setVolume(foregroundVoice ? volume * .25 : volume);
    musicRef.current = music;
    audioRef.current = audio;
    const cache = new MusicTrackCache();
    let disposed = false;
    const refill = () => {
      if (!queue.current.length) queue.current = shuffled(tracks, last.current);
    };
    const next = () => {
      refill();
      const track = queue.current.shift()!;
      last.current = track.id;
      return API + track.url;
    };
    const preloadNext = () => {
      refill();
      void cache.get(API + queue.current[0].url);
    };
    let consecutiveErrors = 0;
    const playNext = () => {
      if (!active.current) return;
      const url = next();
      // A slow speculative download must not hold the playlist for up to 60s.
      audio.src = cache.ready(url) ?? url;
      if (!disposed && active.current)
        void music.play().catch(() => setPlaying(false));
    };
    audio.onended = playNext; // The shuffled playlist repeats indefinitely.
    audio.onplay = () => { setPlaying(true); setError(false); };
    audio.onplaying = () => { consecutiveErrors = 0; preloadNext(); };
    audio.onpause = () => setPlaying(false);
    audio.onerror = () => {
      if (!active.current) return;
      consecutiveErrors++;
      if (consecutiveErrors >= tracks.length) { audio.pause(); setPlaying(false); setError(true); }
      else playNext();
    };
    audio.src = next();
    return () => {
      disposed = true; cache.dispose();
      audio.onended = audio.onplay = audio.onplaying = audio.onpause = audio.onerror = null;
      audio.pause(); music.dispose(); audio.removeAttribute("src"); audio.load();
      audioRef.current = null; musicRef.current = null; queue.current = []; setPlaying(false);
    };
  }, [allowed, tracks, available]);
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (enabled && allowed && visible) void musicRef.current?.play().catch(() => setPlaying(false));
    else audio.pause();
  }, [enabled, allowed, visible, tracks]);
  useEffect(() => {
    musicRef.current?.setVolume(foregroundVoice ? volume * .25 : volume);
  }, [foregroundVoice, tracks, volume]);
  useEffect(() => {
    const resume = (event: Event) => {
      if ((event.target as Element)?.closest?.("[data-music-toggle]")) return;
      if (active.current && audioRef.current)
        void musicRef.current?.play().catch(() => setPlaying(false));
    };
    document.addEventListener("pointerdown", resume);
    document.addEventListener("keydown", resume);
    return () => { document.removeEventListener("pointerdown", resume); document.removeEventListener("keydown", resume); };
  }, []);
  function changeVolume(value:number) {
    const next=saveMusicVolume(localStorage,value);
    setVolume(next);
    if(next>0)lastAudibleVolume.current=next;
    const audio=audioRef.current;
    musicRef.current?.setVolume(foregroundVoice?next*.25:next);
    if(next>0) {
      setEnabled(true);
      if(chatScope===null)localStorage.setItem(preferenceKey,"on");
      if(audio&&allowed&&visible)void musicRef.current?.play().catch(()=>setPlaying(false));
    }
  }
  function toggle() {
    const audio = audioRef.current;
    if (enabled && playing && volume > 0) {
      setEnabled(false); if (chatScope === null) localStorage.setItem(preferenceKey, "off"); audio?.pause();
    } else {
      if(volume===0)changeVolume(lastAudibleVolume.current);
      setEnabled(true); if (chatScope === null) localStorage.setItem(preferenceKey, "on");
      if (audio && visible) void musicRef.current?.play().catch(() => { setPlaying(false); setError(true); });
    }
  }
  return { enabled, playing, loading, available, error, volume, changeVolume, toggle };
}
