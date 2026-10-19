/** The stage follows authored scene direction, never chat playback selection. */
type CaptionEvent={id:string;type:string;source?:string;presentation?:string;chapter_id?:string;scene_id?:string};
export function stageCaption<T extends CaptionEvent>(run:{reviewing?:boolean;chapter_id:string;location:string;events:T[];locations?:{id:string;scene_ids?:string[]}[]}){
 if(run.reviewing)return undefined;
 const sceneIds=run.locations?.find(p=>p.id===run.location)?.scene_ids||[run.location];
 return run.events.slice().reverse().find(e=>e.source==="authored"&&e.presentation!=="archive"&&e.chapter_id===run.chapter_id&&!!e.scene_id&&sceneIds.includes(e.scene_id)&&["NARRATION","CHARACTER_SPEECH","CHARACTER_THOUGHT"].includes(e.type));
}
