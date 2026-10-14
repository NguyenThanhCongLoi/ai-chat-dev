import {useEffect,useRef,useState} from "react";
import type {Mode} from "./types";
import "./divination.css";
export type TarotCard = {id:string;name:string;image:string;position:number;reversed:boolean};
export function DivinationChooser({onChoose,onClose,tr}:{onChoose:(mode:Mode)=>void;onClose:()=>void;tr:(text:string)=>string}) {
  const [revealed,setRevealed]=useState(false),[selected,setSelected]=useState<Mode|null>(null);
  const timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
  const dialog=useRef<HTMLDivElement>(null);
  useEffect(()=>{const id=setTimeout(()=>setRevealed(true),500);dialog.current?.querySelector<HTMLButtonElement>("button")?.focus();return()=>{clearTimeout(id);clearTimeout(timer.current);};},[]);
  useEffect(()=>{const key=(event:KeyboardEvent)=>{
    if(event.key==="Escape"&&!selected)onClose();
    if(event.key==="Tab"){const buttons=Array.from(dialog.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")||[]);const first=buttons[0],last=buttons[buttons.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}
  };document.addEventListener("keydown",key);return()=>document.removeEventListener("keydown",key);},[onClose,selected]);
  const choices=[{mode:"assistant_tarot" as Mode,label:"Tarot",image:"tarot.jpg"},{mode:"assistant_tuvi" as Mode,label:"Tử vi",image:"tu_vi.jpg"}];
  return <div className="divinationVeil" ref={dialog} role="dialog" aria-modal="true" aria-label={tr("Chọn Tarot hoặc Tử vi")}>
    <button className="divinationClose" onClick={onClose} disabled={!!selected} aria-label={tr("Đóng")}>×</button>
    <div className="divinationIntro"><span>✧</span><h2>{tr("Một khoảng lặng để khám phá")}</h2><p>{tr("Chọn lá bài để bước vào không gian của bạn.")}</p></div>
    <div className="divinationChoices">{choices.map(choice=><button key={choice.mode} className={"divinationChoice"+(revealed?" revealed":"")+(selected===choice.mode?" chosen":"")+(selected&&selected!==choice.mode?" withdrawn":"")} disabled={!revealed||!!selected} onClick={()=>{setSelected(choice.mode);timer.current=setTimeout(()=>onChoose(choice.mode),700);}}>
      <span className="divinationFlip"><span className="divinationBack" aria-hidden="true">✦</span><span className="divinationFace"><img src={"/character-images/tarot_tuvi/"+choice.image} alt={tr(choice.label)}/></span></span><strong>{tr(choice.label)}</strong>
    </button>)}</div>
  </div>;
}
const shownReadings = new Set<string>();
export function TarotSpread({cards,readingId,tr}:{cards:TarotCard[];readingId:string;tr:(text:string)=>string}) {
  const animate = useRef(!shownReadings.has(readingId)).current;
  useEffect(()=>{shownReadings.add(readingId);if(shownReadings.size>512)shownReadings.delete(shownReadings.values().next().value!);},[readingId]);
  return <section className={"tarotSpread"+(!animate?" revealedBefore":"")} aria-label={tr("Các lá bài được rút")} data-reading-id={readingId}>
    <p>{tr("Các lá bài được rút")}</p><div className="tarotDraws">{cards.map((card,i)=><figure className="tarotDraw" key={card.id}>
      <div className="tarotDrawFlip" style={{animationDelay:(i*.18)+"s"}}><div className="divinationBack" aria-hidden="true">✦</div><div className="divinationFace"><img src={card.image} alt={card.name} className={card.reversed?"reversed":""}/></div></div>
      <figcaption><b>{card.position}. {card.name}</b><small>{tr(card.reversed?"Ngược":"Xuôi")}</small></figcaption>
    </figure>)}</div>
  </section>;
}
