const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript");
test("home and chat frames share prepared clips but changing account clears them",async()=>{
 const host={},calls=[];
 class Audio{readyState=4;pause(){}load(){}removeAttribute(){}}
 function frame(){
  const exports={};
  const js=ts.transpileModule(fs.readFileSync("frontend/src/roleplay/reactionCache.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(js,{exports,require:()=>({API:"",authHeaders:()=>({}),responseError:async()=>""}),window:{top:host,setTimeout,clearTimeout},Audio,AbortController,DOMException,URL,fetch:async url=>{
   calls.push(url);return {ok:true,json:async()=>({clips:[{id:"clip",emotion:"neutral",url:"/audio",volume:1}]}),blob:async()=>new Blob(["audio"])};
  }});
  return exports;
 }
 const home=frame(),chat=frame();
 const prepared=await home.prepareCharacterReactions("alice","selene");
 assert.equal(prepared.length,1);assert.equal(calls.length,2);
 const reused=await chat.prepareCharacterReactions("alice","selene");
 assert.equal(reused[0].player,prepared[0].player);assert.equal(calls.length,2);
 await chat.prepareCharacterReactions("bob","selene");
 assert.equal(home.cachedReactions("alice","selene"),undefined);
 assert.equal(calls.length,4);
 chat.clearReactionCache();
});
