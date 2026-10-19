const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript");
function load(path,extra={}){
 const exports={};
 const source=ts.transpileModule(fs.readFileSync(path,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 vm.runInNewContext(source,{exports,require:()=>({}),...extra});return exports;
}
test("progression, map changes, and completion reuse the same preparation",()=>{
 const {chapterPreparationKey}=load("frontend/src/worlds/useChapterResources.ts");
 const run={id:"alice",attempt_number:1,chapter_id:"selene_01",config_revision:2,speech_revision:"voice-v1",content_language:"vi"};
 const key=chapterPreparationKey(run);
 for(const phase of ["explore","gate_ready","gate_cinematic","memory","complete"]){
  assert.equal(chapterPreparationKey({...run,phase,location:"another-map",ending:{id:"new"},reviewing:true}),key);
 }
 for(const change of [{chapter_id:"selene_02"},{speech_revision:"voice-v2"},{content_language:"en"},{attempt_number:2}]){
  assert.notEqual(chapterPreparationKey({...run,...change}),key);
 }
});
test("prepared chapter includes an event movie before its trigger and no videos in map review",()=>{
 const {chapterResourcePlan}=load("frontend/src/worlds/useChapterResources.ts",{navigator:{},matchMedia:()=>({matches:false})});
 const run={chapter_id:"selene_01",intro_seen:true,chapter_media:["trap","background"],visual_events:{},assets:{trap:{url:"trap.webm",type:"VIDEO"},background:{url:"map.webp",type:"IMAGE"}}};
 assert.ok(chapterResourcePlan(run).some(t=>t.url==="trap.webm"));
 assert.ok(!chapterResourcePlan({...run,reviewing:true}).some(t=>t.type==="video"));
});
test("ready images retain a decoded blob for direct reuse, without another download",async()=>{
 let fetched=0,decoded=0;
 class Image{set src(value){this.value=value;setImmediate(()=>this.onload());}async decode(){decoded++;}}
 const media=load("frontend/src/worlds/chapterImageMedia.ts",{Image,URL,AbortSignal,fetch:async()=>{fetched++;return{ok:true,blob:async()=>new Blob(["image"])};}});
 await media.prepareChapterImage("selene.webp");
 assert.equal(decoded,1);assert.match(media.preparedImageSource("selene.webp"),/^blob:/);
 await media.prepareChapterImage("selene.webp");
 assert.equal(fetched,1);assert.equal(decoded,1);
});
