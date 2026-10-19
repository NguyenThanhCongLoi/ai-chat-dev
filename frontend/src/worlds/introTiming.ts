export type TimedCue={start:number;end:number};
export function introVoiceRate(duration:number,cue:TimedCue){
 const room=cue.end-cue.start-.15;
 if(!Number.isFinite(duration)||duration<=0||room<=0)throw Error("Invalid intro audio duration");
 const rate=Math.max(1,duration/room);
 if(rate>1.25)throw Error("Intro voice is longer than its cue; adjust the script or CMS timing before playback");
 return rate;
}
export function introAudioDuration(blob:Blob){
 return new Promise<number>((resolve,reject)=>{
  const url=URL.createObjectURL(blob),audio=new Audio();
  const done=(value?:number)=>{clearTimeout(timer);audio.onloadedmetadata=audio.onerror=null;audio.removeAttribute("src");audio.load();URL.revokeObjectURL(url);value===undefined?reject(Error("Cannot decode intro audio")):resolve(value);};
  const timer=setTimeout(()=>done(),12000);
  audio.preload="metadata";audio.onloadedmetadata=()=>done(audio.duration);audio.onerror=()=>done();audio.src=url;audio.load();
 });
}
