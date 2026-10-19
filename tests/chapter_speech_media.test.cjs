const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript");
function fixture(fail=false,unprepared=false){
 let missing=unprepared;
 const exports={},calls=[];let decoded=false;
 class Audio{readyState=0;pause(){}load(){setImmediate(()=>{this.readyState=4;decoded=true;this.oncanplay?.();});}}
 class Mixer{dispose(){}}
 const source=ts.transpileModule(fs.readFileSync("frontend/src/worlds/chapterSpeechMedia.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const http={};vm.runInNewContext(ts.transpileModule(fs.readFileSync("frontend/src/worlds/worldHttp.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:http,localStorage:{getItem:()=>"en"}});
 vm.runInNewContext(source,{exports,require:path=>path.includes("worldHttp")?http:({MusicAudio:Mixer}),localStorage:{getItem:()=>"alice"},Audio,URL,AbortSignal,setTimeout,clearTimeout,fetch:async(url,options)=>{
 calls.push({url,options});
 if(url.endsWith("/chapter-audio"))return {ok:true,text:async()=>JSON.stringify({enabled:true,version:"voice-1",clips:[{id:"line",ready:!missing,version:"v"}]})};
 return {ok:!fail,status:fail?502:200,blob:async()=>new Blob(["audio"])};
 }});
 return {exports,calls,decoded:()=>decoded,markReady:()=>{missing=false;}};
}
test("fixed audio is decoded before ready and reused without another speech request",async()=>{
 const f=fixture(),run={id:"run",chapter_id:"selene_01",content_language:"en"};
 let ready=false;const work=f.exports.prepareChapterSpeech(run,()=>{}).then(()=>ready=true);
 assert.equal(ready,false);await work;assert.ok(f.decoded());
 const clip=f.exports.preparedChapterClip(run,{audio_key:"line"});assert.ok(clip&&clip.element.readyState>=3);
 await f.exports.prepareChapterSpeech(run,()=>{});
 assert.equal(f.calls.filter(c=>c.options?.method==="POST").length,1);
 assert.equal(f.exports.preparedChapterClip(run,{audio_key:"line"}).element,clip.element);
});
test("failed fixed audio prevents a successful readiness result",async()=>{
 const f=fixture(true);
 await assert.rejects(f.exports.prepareChapterSpeech({id:"r",chapter_id:"selene_01",content_language:"en"},()=>{}),/not ready/);
});
test("unsupported TTS languages do not download chapter voices",async()=>{
 const f=fixture();await f.exports.prepareChapterSpeech({id:"r",content_language:"ja"},()=>{});
 assert.equal(f.calls.length,0);
});

test("missing CMS audio is explained without requesting an unavailable clip; retry uses newly prepared audio",async()=>{
 const f=fixture(false,true),run={id:"r",chapter_id:"selene_01",content_language:"vi"};
 await assert.rejects(f.exports.prepareChapterSpeech(run,()=>{}),e=>e.reason==="unprepared");
 assert.equal(f.calls.filter(c=>c.options?.method==="POST").length,0);
 f.markReady();
 await f.exports.prepareChapterSpeech(run,()=>{});
 assert.equal(f.calls.filter(c=>c.options?.method==="POST").length,1);
 assert.ok(f.exports.preparedChapterClip(run,{audio_key:"line"}));
});
