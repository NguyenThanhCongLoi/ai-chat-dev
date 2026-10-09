import {useId,useState} from "react";
import { Icon } from "../ui";
import {storedLanguage,translateUiText} from "../i18n";

type Props = { enabled:boolean; playing: boolean; loading: boolean; available: boolean; error: boolean; errorDetail?: string; volume:number; changeVolume:(value:number)=>void; toggle: () => void };
export function BackgroundMusicButton({ enabled,playing,loading,available,error,errorDetail,volume,changeVolume,toggle }: Props) {
  const [open,setOpen]=useState(false);
  const id=useId();
  const muted=!enabled||volume===0;
  const t=(value:string)=>translateUiText(value,storedLanguage());
  const label=loading?"Đang tải nhạc…":error?"Không tải được nhạc nền":!available?"Chưa có nhạc nền":"Âm lượng nhạc";
  const muteLabel=t(muted||!playing?"Bật nhạc nền":"Tắt nhạc nền");
  return <div className="rpMusicControl" data-background-music-control>
    <div className="rpMusicControlRow">
      <button type="button" className="rpMusicMute" data-music-toggle onClick={toggle}
        disabled={loading||!available} title={muteLabel} aria-label={muteLabel} aria-pressed={!muted&&playing}>
        <span aria-hidden="true"><Icon n="volume" /></span>
        {muted&&<span className="rpMusicMuteSlash" aria-hidden="true">/</span>}
      </button>
      <button type="button" className="rpBackgroundMusicButton" title={errorDetail}
        onClick={()=>setOpen(value=>!value)} disabled={loading||!available}
        aria-expanded={open} aria-controls={id}>
        <span>{t(label)}</span><span className="rpMusicPercent" translate="no">{Math.round(volume*100)}%</span>
      </button>
    </div>
    {open&&<div className="rpMusicVolumePanel" id={id}>
      <input type="range" min="0" max="100" step="1" value={Math.round(volume*100)}
        aria-label={t("Âm lượng nhạc")} onInput={event=>changeVolume(Number(event.currentTarget.value)/100)}
        onChange={event=>changeVolume(Number(event.currentTarget.value)/100)} />
      <output translate="no">{Math.round(volume*100)}%</output>
    </div>}
  </div>;
}
