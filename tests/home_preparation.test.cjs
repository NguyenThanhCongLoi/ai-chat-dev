const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript");
function fixture({fail=false,configFail=false}={}){
 const log=[];let finish;
 const waiting=new Promise(resolve=>finish=resolve),exports={};
 const modules={
 "../roleplay/api":{API:"",authHeaders:()=>({}),api:async path=>{
 log.push(path);if(configFail&&path==="/v1/assistant/profiles")throw Error("configuration");
 if(path==="/v1/characters")return [{id:"selene"}];
 if(path==="/v1/roleplay/background-music")return {tracks:[{id:"music",url:"/song"}]};
 return {};
 }},
 "../roleplay/reactionCache":{prepareCharacterReactions:async(user,id)=>{log.push("reaction:"+user+":"+id);}},
 "../worlds/worldIntroMedia":{prepareWorldMetadata:async()=>{log.push("world:metadata");}},
 "../worlds/WorldApp":{},"../roleplay/RolePlayApp":{},
 };
 const source=fs.readFileSync("frontend/src/assistant/prepareCompanionHome.ts","utf8");
 const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 vm.runInNewContext(js,{exports,require:name=>{if(!(name in modules))throw Error(name);return modules[name];},document:{fonts:{ready:Promise.resolve()}},AbortSignal,sessionStorage:{setItem:()=>{}},fetch:async()=>{log.push("music:download");await waiting;if(fail)throw Error("network");return {ok:true,arrayBuffer:async()=>new ArrayBuffer(1)};}});
 return {log,finish,prepare:exports.prepareCompanionHome,warm:exports.prepareWorldInBackground};
}
test("slow audio does not hold login; only one character is warmed",async()=>{
 const f=fixture();await f.prepare("alice");
 await new Promise(r=>setImmediate(r));
 assert.ok(f.log.includes("reaction:alice:selene"));
 assert.ok(f.log.includes("music:download"));
 assert.ok(!f.log.some(v=>v.startsWith("world:")));
 f.finish();
});
test("failed optional music does not lock home",async()=>{
 const f=fixture({fail:true});await f.prepare("alice");f.finish();
 await new Promise(r=>setImmediate(r));
});
test("required configuration failures retain retry gate",async()=>{
 const f=fixture({configFail:true});
 await assert.rejects(f.prepare("alice"),/configuration/);
 assert.ok(!f.log.includes("music:download"));
});
test("background World warmup requests metadata only",async()=>{
 const f=fixture();f.warm();await new Promise(r=>setImmediate(r));
 assert.deepEqual(f.log,["world:metadata"]);
});
