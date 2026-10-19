import {preparedImageSource} from "./chapterImageMedia";
import {worldUi} from "./worldUi";
import {useState} from "react";
import type {AdventureRun} from "./adventureTypes";
export function AdventureArchive({run}:{run:AdventureRun}){
 const [category,setCategory]=useState("CORE MEMORIES");
 const t=(vi:string,en:string)=>worldUi(vi,en,run.content_language);
 const labels:Record<string,string>={"CORE MEMORIES":t("Ký ức chính","Core memories"),ARTIFACTS:t("Vật phẩm","Artifacts"),ECHOES:t("Tiếng vọng","Echoes"),LORE:t("Kiến thức","Lore"),"???":"???"};
 return <section className="maArchive"><nav>{Object.keys(run.archive).map(k=><button key={k} aria-pressed={category===k} onClick={()=>setCategory(k)}>{labels[k]} · {run.archive[k].length}</button>)}</nav>
 <div className="maArchiveGrid">{run.archive[category]?.map(item=><article key={item.id}>{item.asset&&run.assets[item.asset]&&(item.crop?<div className="maInventoryCrop"><img src={preparedImageSource(run.assets[item.asset].url)} alt="" style={{left:-item.crop[0]/item.crop[2]*100+"%",top:-item.crop[1]/item.crop[3]*100+"%",width:100/item.crop[2]+"%",height:100/item.crop[3]+"%"}}/></div>:<img src={preparedImageSource(run.assets[item.asset].url)} alt="" loading="lazy"/>)}<h3>{item.title}</h3>{item.text&&<p>{item.text}</p>}</article>)}</div></section>;
}
