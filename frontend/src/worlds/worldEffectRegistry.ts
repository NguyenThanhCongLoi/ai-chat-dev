import type {ChapterRun,WorldEvent} from "./moonfallTypes";
export const WORLD_EFFECTS=["RUNE_GLOW","MAGIC_PULSE","CLUE_SPARK","THOUGHT_BUBBLE","MANGA_REACTION","MEMORY_GLOW","MAP_NODE_PULSE","LOCATION_UNLOCK","CHARACTER_REALIZATION","SOFT_FLASH","CAMERA_SHAKE"] as const;
export type EffectType=typeof WORLD_EFFECTS[number];
export type EffectCue={id:string;type:EffectType;target:string;duration:number;reducedMotion:"static"|"fade"};
const defaults:Record<string,EffectType[]>={
 MAGIC_ACTIVATED:["RUNE_GLOW","MAGIC_PULSE"],CHARACTER_THOUGHT:["THOUGHT_BUBBLE"],
 CHARACTER_REALIZATION:["MANGA_REACTION"],CLUE_DISCOVERED:["CLUE_SPARK"],
 MEMORY_TRIGGER:["MEMORY_GLOW"],MEMORY_RECONSTRUCTION:["MEMORY_GLOW"],MEMORY_UNLOCKED:["MEMORY_GLOW"],
 LOCATION_ENTER:["MAP_NODE_PULSE"],LOCATION_UNLOCKED:["LOCATION_UNLOCK"],SECRET_REVEALED:["SOFT_FLASH"],CHAPTER_COMPLETE:["MEMORY_GLOW"]
};
const aliases:Record<string,EffectType>={rune:"RUNE_GLOW",pulse:"MAGIC_PULSE",reconstruct:"MEMORY_GLOW",fade:"SOFT_FLASH"};
/** Presentation only; CMS durations are seconds. No story state writes. */
export function resolveWorldEffects(event:WorldEvent,run:ChapterRun):EffectCue[]{
 if(event.type==="USER"||event.visual_event==="WORLD_INTRO")return [];
 const config=run.visual_events[event.visual_event];if(!config)return [];
 const custom=config.vfx;
 const objectTarget=(event as WorldEvent&{target_id?:string}).target_id;
 const types=custom==="none"?[]:custom?(WORLD_EFFECTS.includes(custom as EffectType)?[custom as EffectType]:aliases[custom]?[aliases[custom]]:defaults[event.visual_event]||[]):defaults[event.visual_event]||[];
 return types.map((type,index):EffectCue=>({id:event.id+":"+index,type,
  target:type==="RUNE_GLOW"?(objectTarget||"scene"):type==="CLUE_SPARK"?(objectTarget||"scene"):type==="THOUGHT_BUBBLE"?"character":
   ["MANGA_REACTION","CHARACTER_REALIZATION"].includes(type)?"character":
   ["MAP_NODE_PULSE","LOCATION_UNLOCK"].includes(type)?"map:"+run.location:type==="MEMORY_GLOW"?"memory":"scene",
  duration:Math.min(8000,Math.max(0,config.duration*1000)),reducedMotion:config.reduced_motion==='fade'?'fade':'static'
 })).filter(c=>c.duration>0);
}
