const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
function setup(options={}){
 const players=[],requests=[],revoked=[],timers=new Map();
 function schedule(fn,ms){const id=setTimeout(fn,ms);timers.set(id,{fn,ms});return id;}
 function cancel(id){clearTimeout(id);timers.delete(id);}
 let rows=[{id:"a",target:"shared",emotion:"neutral",volume:.6,url:"/a.wav"}];
 class Audio{
  constructor(src){this.src=src;this.readyState=0;this.paused=true;players.push(this);}
  load(){}pause(){this.paused=true;}removeAttribute(){this.src="";}
 }
 const exports={};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/reactionCache.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{
  exports,require:()=>({API:"",authHeaders:()=>({Authorization:"test"}),responseError:async()=> "Failed"}),
  Audio,AbortController,DOMException,Date,Map,Set,Error,Promise,window:{setTimeout:schedule,clearTimeout:cancel},
  URL:{createObjectURL:()=> "blob:"+players.length,revokeObjectURL:url=>revoked.push(url)},
  fetch:async (url,init)=>{requests.push(url);
   if(options.stall)return await new Promise((resolve,reject)=>{init.signal.addEventListener("abort",()=>reject(init.signal.reason),{once:true});});
   return {ok:true,json:async()=>({clips:rows}),blob:async()=>({})};}
 });
 return{api:exports,players,requests,revoked,timers,setRows:value=>rows=value};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test("room preparation waits for canplay and reuses prepared audio on reentry",async()=>{
 const env=setup();let done=false;
 const pending=env.api.prepareRoomReactions("u",["c"]).then(()=>{done=true;});
 await tick();assert.equal(done,false);assert.equal(env.players.length,1);
 env.players[0].readyState=3;env.players[0].oncanplay();await pending;
 const first=env.api.cachedReactions("u","c")[0];
 await env.api.prepareRoomReactions("u",["c"]);
 assert.equal(env.players.length,1);
 assert.equal(env.api.cachedReactions("u","c")[0].player,first.player);
 assert.equal(env.requests.filter(url=>url==="/a.wav").length,1);
 env.api.clearReactionCache();
});
test("fresh metadata removes deleted clips and account switch releases media",async()=>{
 const env=setup();const work=env.api.prepareRoomReactions("u",["c"]);
 await tick();env.players[0].oncanplay();await work;
 env.setRows([]);await env.api.prepareRoomReactions("u",["c"]);
 assert.equal(env.api.cachedReactions("u","c").length,0);
 assert.equal(env.revoked.length,1);
 await env.api.prepareRoomReactions("other",["c"]);
 assert.equal(env.api.cachedReactions("u","c"),undefined);
 env.api.clearReactionCache();
});
test("audio preparation failure can retry without poisoning the cache",async()=>{
 const env=setup();const work=env.api.prepareRoomReactions("u",["c"]);
 const rejected=assert.rejects(work,/prepare reaction/);
 await tick();env.players[0].onerror();await rejected;
 assert.equal(env.api.cachedReactions("u","c"),undefined);
 const retry=env.api.prepareRoomReactions("u",["c"]);
 await tick();env.players[1].oncanplay();await retry;
 assert.equal(env.api.cachedReactions("u","c").length,1);
 env.api.clearReactionCache();
});

test("downloads use four preparation slots without a shared whole-set timeout",async()=>{
 const env=setup();
 env.setRows(Array.from({length:6},(_,id)=>({id:String(id),target:"shared",emotion:"neutral",volume:.6,url:"/"+id+".wav"})));
 const pending=env.api.prepareRoomReactions("u",["c"]);
 await tick();assert.equal(env.players.length,4);
 for(const player of env.players){player.readyState=3;player.oncanplay();}
 await tick();assert.equal(env.players.length,6);
 for(const player of env.players.slice(4)){player.readyState=3;player.oncanplay();}
 await pending;
 assert.equal(env.api.cachedReactions("u","c").length,6);
 assert.equal(env.timers.size,0);env.api.clearReactionCache();
});
test("a download timeout reports the cause rather than a raw AbortError",async()=>{
 const env=setup({stall:true});
 const pending=env.api.prepareRoomReactions("u",["c"]);
 const rejected=assert.rejects(pending,error=>!env.api.isReactionPreparationCancelled(error)&&/download timed out/.test(error.message));
 await tick();
 const timeout=Array.from(env.timers.values()).find(timer=>timer.ms===25000);
 assert.ok(timeout);timeout.fn();await rejected;
 assert.equal(env.timers.size,0);env.api.clearReactionCache();
});
test("session cancellation is distinguished from a failed download",async()=>{
 const env=setup({stall:true});
 const pending=env.api.prepareRoomReactions("u",["c"]);
 const rejected=assert.rejects(pending,error=>env.api.isReactionPreparationCancelled(error));
 await tick();env.api.clearReactionCache();await rejected;
 assert.equal(env.timers.size,0);
});
