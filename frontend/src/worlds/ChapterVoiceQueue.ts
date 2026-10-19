/** A single serial lane for narrator and character speech. Media owns completion. */
export class ChapterVoiceQueue<T extends {id:string}> {
 private items:T[]=[];
 private seen=new Set<string>();
 private draining=false;
 private epoch=0;
 private play:(item:T)=>Promise<void>;
 private interrupt:()=>void;
 private activity:(busy:boolean)=>void;
 constructor(play:(item:T)=>Promise<void>,interrupt:()=>void,activity:(busy:boolean)=>void=()=>{}){this.play=play;this.interrupt=interrupt;this.activity=activity;}
 enqueue(items:T[],replay=false){
  for(const item of items){
   if(!replay&&this.seen.has(item.id))continue;
   this.seen.add(item.id);this.items.push(item);
  }
  while(this.seen.size>512)this.seen.delete(this.seen.values().next().value!);
  void this.drain();
 }
 cancel(){this.epoch++;this.items=[];this.interrupt();}
 reset(){this.cancel();this.seen.clear();}
 private async drain(){
  if(this.draining)return;
  this.draining=true;this.activity(true);const epoch=this.epoch;
  try{
   while(epoch===this.epoch&&this.items.length){
    const item=this.items.shift()!;
    try{await this.play(item);}catch{/* A failed clip must not deadlock the lane. */}
   }
  }finally{this.draining=false;if(this.items.length)void this.drain();else this.activity(false);}
 }
}

/** Chapter narration is opt-in; the separate home intro keeps its own playback. */
export function autoVoiceEvents<T extends {type:string;voice_role?:string|null}>(events:T[],mode:"all"|"narrator"|"characters"|"silent"):T[]{
 return events.filter(e=>(mode==="all"||mode==="narrator")&&e.type==="NARRATION"&&e.voice_role==="NARRATOR"||(mode==="all"||mode==="characters")&&e.type==="CHARACTER_SPEECH"&&e.voice_role==="CHARACTER");
}
