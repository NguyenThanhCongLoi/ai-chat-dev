import {readWorldJson} from "./worldHttp";
/** A bounded pool keeps the actual intro media element warm across home/World views.
 * Public media only; never fetch or cache private story state here.
 */
import {prepareIntroNarration} from "./introNarrationMedia";
type Presentation={intro:{id:string;url:string}[]};
let catalog:Promise<Presentation>|undefined;
let firstUrl="";
const prepared=new Map<string,Promise<string>>();
const objectSources=new Map<string,string>();
export function preparedVideoSource(url:string){return objectSources.get(url)||"";}
const videoProgress=new Map<string,number>(),progressListeners=new Map<string,Set<(value:number)=>void>>();
function reportVideo(url:string,value:number){videoProgress.set(url,value);for(const listener of progressListeners.get(url)||[])listener(value);}
export function prepareIntroVideo(url:string,onProgress?:(value:number)=>void){
 let listeners=progressListeners.get(url);if(!listeners){listeners=new Set();progressListeners.set(url,listeners);}
 if(onProgress){listeners.add(onProgress);onProgress(videoProgress.get(url)||0);}
 let pending=prepared.get(url);
 if(!pending){
  pending=fetch(url,{signal:AbortSignal.timeout(120000)}).then(async r=>{
   if(!r.ok)throw Error("Video unavailable");
   let blob:Blob;
   const total=Number(r.headers.get("content-length"));
   if(r.body&&total>0){
    const reader=r.body.getReader(),chunks:BlobPart[]=[];let received=0;
    while(true){const {done,value}=await reader.read();if(done)break;chunks.push(value);received+=value.byteLength;reportVideo(url,Math.min(.99,received/total));}
    blob=new Blob(chunks,{type:r.headers.get("content-type")||"video/webm"});
   }else blob=await r.blob();
   if(!blob.size)throw Error("Empty intro");
   const source=URL.createObjectURL(blob);objectSources.set(url,source);reportVideo(url,1);return source;
  }).catch(e=>{prepared.delete(url);reportVideo(url,0);throw e;});
  prepared.set(url,pending);
 }
 if(!onProgress)return pending;
 return pending.finally(()=>listeners!.delete(onProgress));
}

const players=new Map<string,HTMLVideoElement>();
function limited(){return matchMedia("(prefers-reduced-motion: reduce)").matches||!!(navigator as Navigator & {connection?:{saveData?:boolean}}).connection?.saveData;}
export function introVolume(){try{const n=Number(localStorage.getItem("world_intro_volume")??".45");return Number.isFinite(n)?Math.max(0,Math.min(1,n)):.45;}catch{return .45;}}
export function introPlayer(url:string,preload:"auto"|"metadata"="auto"){
 let player=players.get(url);
 if(!player){
  // Keep at most the current and next likely clip.
  if(players.size>=2){const unused=[...players].find(([,p])=>p.hidden&&p.paused);if(unused){unused[1].removeAttribute("src");unused[1].load();unused[1].remove();players.delete(unused[0]);}}
  player=document.createElement("video");player.playsInline=true;player.preload=limited()?"metadata":preload;player.volume=introVolume();player.hidden=true;player.src=url;
  player.dataset.worldIntro="true";document.body.append(player);players.set(url,player);
 }else if(!limited()&&preload==="auto")player.preload="auto";
 return player;
}
export function parkIntro(player:HTMLVideoElement){player.pause();player.hidden=true;document.body.append(player);}
/** Lightweight speculation: metadata only, no video/audio downloads. */
export function prepareWorldMetadata(){
 catalog??=fetch("/v1/moonfall/hub/presentation",{signal:AbortSignal.timeout(15000)}).then(r=>{if(!r.ok)throw Error("Intro unavailable");return readWorldJson(r) as Promise<Presentation>;}).catch(e=>{catalog=undefined;throw e;});
 return catalog;
}
export function prepareWorldIntro(){
 if(!limited())void prepareIntroNarration().catch(()=>{});
 const pending=prepareWorldMetadata();
 void pending.then(c=>{if(c.intro[0]){firstUrl=c.intro[0].url;introPlayer(firstUrl);if(!limited())void prepareIntroVideo(firstUrl).catch(()=>{});}}).catch(()=>{});
 return pending;
}
export function playPreparedIntro(){prepareWorldIntro();}

export function pauseIntroMedia(){for(const p of players.values())p.pause();}

/** Home entry gate: resolves only after the current intro's downloads complete. */
export async function prepareWorldEntryResources(progress:(value:number)=>void=()=>{}){
 progress(0);
 const response=await fetch("/v1/worlds/config",{cache:"no-store",signal:AbortSignal.timeout(15000)});
 if(!response.ok)throw Error("World configuration unavailable");
 const flags=await readWorldJson(response);
 if(!flags.enabled){progress(1);return;}
 const c=await prepareWorldIntro();progress(.05);
 // Atlas art is also downloaded before the hub becomes interactive.
 const hub=await fetch("/v1/moonfall/hub",{headers:{"Authorization":"Bearer "+(localStorage.getItem("auth_token")||"")},signal:AbortSignal.timeout(25000)});
 if(!hub.ok)throw Error("Atlas unavailable");
 const atlas=await readWorldJson(hub);
 await Promise.all([atlas.background,...atlas.characters.map((c:{avatar_url:string})=>c.avatar_url)].filter(Boolean).map((url:string)=>new Promise<void>((resolve,reject)=>{
  const image=new Image(),timer=setTimeout(()=>reject(Error("Atlas image timeout")),25000);
  image.onload=()=>{clearTimeout(timer);void image.decode().then(resolve,reject);};
  image.onerror=()=>{clearTimeout(timer);resolve();};image.src=url;
 })));
 const clips=c.intro.map(()=>0);let narration=0;
 const update=()=>progress(.05+.95*(.8*(clips.length?clips.reduce((a,b)=>a+b,0)/clips.length:1)+.2*narration));
 await Promise.all([
  ...c.intro.map((clip,index)=>prepareIntroVideo(clip.url,value=>{clips[index]=value;update();})),
  prepareIntroNarration(true,value=>{narration=value;update();}),
 ]);
 progress(1);
}
