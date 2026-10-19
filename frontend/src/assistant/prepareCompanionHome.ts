import {api,API,authHeaders} from "../roleplay/api";
import {prepareCharacterReactions} from "../roleplay/reactionCache";
import {prepareWorldMetadata} from "../worlds/worldIntroMedia";

let audioOwner="",audioEpoch=0;
/** Only service configuration holds the login gate. Media never holds the home screen. */
export async function prepareCompanionHome(userId:string){
 await Promise.all([
  api("/v1/assistant/profiles"),
  api("/v1/assistant/models?mode=assistant_general"),
 ]);
 // Fonts and large downloads must not extend the login wait.
 void warmOrdinaryAudio(userId).catch(()=>{});
}
async function warmOrdinaryAudio(userId:string){
 if(audioOwner===userId)return;
 audioOwner=userId;const epoch=++audioEpoch;
 const sameOwner=()=>epoch===audioEpoch;
 await Promise.allSettled([
  api<{id:string}[]>("/v1/characters").then(async characters=>{
   // One likely character, rather than every character and every voice.
   if(sameOwner()&&characters[0])await prepareCharacterReactions(userId,characters[0].id);
  }),
  api<{tracks:{id:string;url:string}[]}>("/v1/roleplay/background-music").then(async music=>{
   const track=music.tracks[0];if(!track||!sameOwner())return;
   const r=await fetch(API+track.url,{headers:authHeaders(),signal:AbortSignal.timeout(30000)});
   if(!r.ok)throw Error("Music preparation failed");
   await r.arrayBuffer();
   if(sameOwner())try{sessionStorage.setItem("prepared_music_ids",JSON.stringify([track.id]));}catch{}
  }),
 ]);
}
export function prepareWorldInBackground(){
 void import("../worlds/WorldApp").then(()=>prepareWorldMetadata()).catch(()=>{/* World entry has its own retry gate. */});
}
