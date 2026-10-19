import {worldUi} from "./worldUi";
import {storedLanguage} from "../i18n";
import {useEffect,useState} from "react";
import type {Puzzle} from "./adventureTypes";
export function AdventurePuzzle({puzzle,busy,onSolve,language=storedLanguage()}:{language?:string;puzzle:Puzzle;busy:boolean;onSolve:(value:string)=>void}){
 const [answer,setAnswer]=useState<string[]>([]);
 useEffect(()=>setAnswer([]),[puzzle.id]);
 const t=(vi:string,en:string)=>worldUi(vi,en,language);
 const single=["symbol_match","evidence_deduction"].includes(puzzle.type);
 return <section className="maPuzzle" aria-label={puzzle.title}><h3>{puzzle.title}</h3>
 {puzzle.solved?<p>✓</p>:!puzzle.ready?<p>{t("Khám phá và thu thập đủ dấu vết trước","Gather the evidence first")}</p>:<>
 <div className="maTokens">{puzzle.options.map(o=><button key={o.id} type="button" aria-pressed={answer.includes(o.id)} disabled={busy} onClick={()=>setAnswer(old=>single?[o.id]:old.includes(o.id)?old.filter(i=>i!==o.id):[...old,o.id])}>{o.label}{!single&&answer.includes(o.id)?<b> {answer.indexOf(o.id)+1}</b>:null}</button>)}</div>
 <button type="button" disabled={busy||!answer.length} onClick={()=>onSolve(JSON.stringify({id:puzzle.id,answer:single?answer[0]:answer}))}>✓ {t("Kiểm tra","Check")}</button><button type="button" aria-label={t("Chọn lại","Reset selection")} onClick={()=>setAnswer([])}>↺</button></>}
 </section>;
}
