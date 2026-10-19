import {preparedImageSource} from "./chapterImageMedia";
import type {AdventureRun} from "./adventureTypes";
type Props={run:AdventureRun;blocked:boolean;onInspect:(id:string,action?:string)=>void;inspectLabel:string};
export default function EmbeddedScene({run,blocked,onInspect,inspectLabel}:Props){
 const scene=run.embedded_scene;
 if(!scene)return null;
 const objects=run.objects.filter(o=>o.mode==="embedded"&&!o.removed);
 function activate(o:typeof objects[number]){
  if(!blocked&&o.interactive!==false&&(!o.discovered||o.interaction_action==="open_gate"))onInspect(o.id,o.interaction_action);
 }
 return <>
  {scene.cleanups.map(p=><img key={p.asset} className="maCleanPatch" data-cleared-item={p.visible?p.asset:undefined} src={preparedImageSource(run.assets[p.asset]?.url||"")} alt="" style={{opacity:p.visible?1:0,left:p.x*100+"%",top:p.y*100+"%",width:p.width*100+"%",height:p.height*100+"%"}}/>)}
  {scene.covers?.filter(c=>c.visible).map(c=><div key={c.id} className="maSceneCover" data-covered-item={c.id} style={{left:c.x*100+"%",top:c.y*100+"%",width:c.width*100+"%",height:c.height*100+"%"}} aria-hidden="true"><img src={preparedImageSource(run.assets[c.asset]?.url||"")} alt=""/></div>)}
  <svg className="maEmbeddedHotspots" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-label={inspectLabel}>
   {objects.filter(o=>!o.optional&&!blocked&&o.interactive!==false&&(!o.discovered||o.interaction_action==="open_gate")).map(o=><circle key={"light-"+o.id} className="maItemLight" data-hint-for={o.id} cx={(o.x+o.width/2)*1000} cy={(o.y+o.height/2)*1000} r="6" aria-hidden="true"/>)}
   {objects.map(o=><polygon key={o.id} role="button" tabIndex={blocked||o.interactive===false?-1:0} points={o.polygon!.map(p=>p[0]*1000+","+p[1]*1000).join(" ")}
     data-world-target={o.id} data-prop-mode="embedded" data-discovered={o.discovered} aria-label={inspectLabel+o.title} aria-disabled={blocked||o.interactive===false||o.discovered&&o.interaction_action!=="open_gate"}
     onClick={()=>activate(o)} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();activate(o);}}}>
    <title>{inspectLabel+o.title}</title></polygon>)}
  </svg>

 </>;
}
