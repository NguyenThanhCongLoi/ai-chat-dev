import {API,authHeaders,responseError} from "./api";
export type ReactionClip={id:string;target:string;emotion:string;volume:number;url:string;voice_id?:string};
export type PreparedReaction=ReactionClip&{objectUrl:string;player:HTMLAudioElement};
type Entry={clips:PreparedReaction[];checkedAt:number};
type SharedCache={entries:Map<string,Entry>;pending:Map<string,Promise<PreparedReaction[]>>;controllers:Set<AbortController>;owner?:string;epoch:number};
const fresh=():SharedCache=>({entries:new Map(),pending:new Map(),controllers:new Set(),epoch:0});
// Platform and same-origin chat frames reuse the actual prepared audio players.
// Nothing is persisted to disk; selecting another account clears the whole pool.
const shared=(()=>{
 try{
  const host=(window.top||window) as Window&{__companionReactions?:SharedCache};
  return host.__companionReactions??(host.__companionReactions=fresh());
 }catch{return fresh();}
})();
const {entries,pending,controllers}=shared;
function dispose(clip:PreparedReaction){
  clip.player.pause();clip.player.onended=clip.player.onerror=clip.player.oncanplay=null;
  clip.player.removeAttribute("src");clip.player.load();URL.revokeObjectURL(clip.objectUrl);
}
export function clearReactionCache(){
  ++shared.epoch;for(const controller of controllers)controller.abort(new DOMException("Reaction preparation cancelled","AbortError"));controllers.clear();
  for(const entry of entries.values())entry.clips.forEach(dispose);
  entries.clear();pending.clear();shared.owner=undefined;
}
function selectOwner(userId:string){if(shared.owner!==userId){clearReactionCache();shared.owner=userId;}}
export function cachedReactions(userId:string,characterId:string){
  return shared.owner===userId?entries.get(characterId)?.clips:undefined;
}
export function isReactionPreparationCancelled(error:unknown){
  return Boolean(error&&typeof error==="object"&&"name" in error&&error.name==="AbortError");
}
async function readyPlayer(player:HTMLAudioElement,signal:AbortSignal){
  if(player.readyState>=3)return;
  await new Promise<void>((resolve,reject)=>{
    const timer=window.setTimeout(()=>done(new Error("Reaction audio preparation timed out")),8000);
    const aborted=()=>done(signal.reason);
    const done=(error?:Error)=>{
      window.clearTimeout(timer);signal.removeEventListener("abort",aborted);player.oncanplay=player.onerror=null;
      if(error)reject(error);else resolve();
    };
    if(signal.aborted){done(signal.reason);return;}
    signal.addEventListener("abort",aborted,{once:true});
    player.oncanplay=()=>done();
    player.onerror=()=>done(new Error("Could not prepare reaction audio"));
    player.load();
  });
}
export function prepareCharacterReactions(userId:string,characterId:string,refresh=false):Promise<PreparedReaction[]>{
  selectOwner(userId);
  const cached=entries.get(characterId);
  if(!refresh&&cached&&Date.now()-cached.checkedAt<30000)return Promise.resolve(cached.clips);
  const inFlight=pending.get(characterId);if(inFlight)return inFlight;
  const generation=shared.epoch;
  const controller=new AbortController();controllers.add(controller);
  const headers=authHeaders();
  const work=(async()=>{
    const prepared:PreparedReaction[]=[];
    const created:PreparedReaction[]=[];
    try{
      async function request<T>(url:string,read:(response:Response)=>Promise<T>){
        // Each download has its own budget; it is not shared by the whole clip set.
        const timeout=window.setTimeout(()=>controller.abort(new Error("Reaction audio download timed out. Please retry opening the room.")),25000);
        try{
          const response=await fetch(url,{headers,signal:controller.signal});
          if(!response.ok)throw new Error(await responseError(response));
          return await read(response);
        }catch(error){if(controller.signal.aborted)throw controller.signal.reason;throw error;}
        finally{window.clearTimeout(timeout);}
      }
      const data=await request<{clips:ReactionClip[]}>(API+"/v1/characters/"+encodeURIComponent(characterId)+"/reactions",response=>response.json());
      const old=new Map(cached?.clips.map(clip=>[clip.id,clip])||[]);
      const ordered=[...data.clips].sort((a,b)=>Number(b.emotion==="neutral")-Number(a.emotion==="neutral")).slice(0,24);
      let cursor=0,failure:unknown;
      async function worker(){
        while(cursor<ordered.length&&!controller.signal.aborted){
          const clip=ordered[cursor++];
          try{
            const reuse=old.get(clip.id);
            if(reuse){prepared.push({...reuse,...clip});continue;}
            const blob=await request(API+clip.url,response=>response.blob());
            if(controller.signal.aborted)throw controller.signal.reason;
            const objectUrl=URL.createObjectURL(blob);
            const player=new Audio(objectUrl);player.preload="auto";
            const item={...clip,objectUrl,player};created.push(item);
            await readyPlayer(player,controller.signal);prepared.push(item);
          }catch(error){
            failure??=error;
            if(!controller.signal.aborted)controller.abort(error);
          }
        }
      }
      await Promise.all(Array.from({length:Math.min(2,ordered.length)},()=>worker()));
      if(failure)throw failure;
      if(generation!==shared.epoch||controller.signal.aborted)throw controller.signal.reason||new DOMException("Reaction preparation cancelled","AbortError");
      const ids=new Set(prepared.map(clip=>clip.id));
      for(const clip of cached?.clips||[])if(!ids.has(clip.id))dispose(clip);
      entries.delete(characterId);entries.set(characterId,{clips:prepared,checkedAt:Date.now()});
      // Retain prepared media across room visits; bound the per-account cache.
      while(entries.size>16){
        const key=entries.keys().next().value!;
        entries.get(key)?.clips.forEach(dispose);entries.delete(key);
      }
      return prepared;
    }catch(error){created.forEach(dispose);throw error;}
    finally{controllers.delete(controller);if(generation===shared.epoch)pending.delete(characterId);}
  })();
  pending.set(characterId,work);return work;
}
export async function prepareRoomReactions(userId:string,ids:string[]){
  for(const id of [...new Set(ids)].slice(0,8))await prepareCharacterReactions(userId,id);
}
export function warmReactionClips(userId:string,ids:string[]){
  // Prewarm recent characters on the catalog page without holding up that page.
  for(const id of [...new Set(ids)].slice(0,1))void prepareCharacterReactions(userId,id).catch(()=>{});
}
