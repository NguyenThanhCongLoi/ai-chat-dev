export const musicVolumeKey="roleplay_background_music_volume";
export function normalizedMusicVolume(value:number) {
  return Number.isFinite(value)?Math.max(0,Math.min(1,value)):.3;
}
export function savedMusicVolume(storage:Pick<Storage,"getItem">) {
  try {
    const raw=storage.getItem(musicVolumeKey);
    return raw===null||!raw.trim()? .3 : normalizedMusicVolume(Number(raw));
  } catch {return .3;}
}
export function saveMusicVolume(storage:Pick<Storage,"setItem">,value:number) {
  const volume=normalizedMusicVolume(value);
  try {storage.setItem(musicVolumeKey,String(volume));} catch {}
  return volume;
}
