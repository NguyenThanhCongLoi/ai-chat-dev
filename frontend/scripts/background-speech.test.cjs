const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
const api={};vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/backgroundSpeech.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:api,TextDecoder,Error,Promise,Blob,atob,DOMException});
const delta='data: {"type":"speech.audio.delta","format":"pcm","audio":"AAA=","sample_rate":24000}\n\n';
const done='data: {"type":"speech.audio.done"}\n\n';
function response(parts){return new Response(new ReadableStream({start(controller){for(const part of parts)controller.enqueue(new TextEncoder().encode(part));controller.close();}}),{headers:{"Content-Type":"text/event-stream"}});}
test("silent stream handles split events, requires done, and never uses audio player",async()=>{
 await api.consumePreparedSpeech(response([delta.slice(0,12),delta.slice(12),done]));
 await assert.rejects(api.consumePreparedSpeech(response([delta])),/chưa hoàn tất/);
 await assert.rejects(api.consumePreparedSpeech(response(['data: {"error":{"message":"failed"}}\n\n'])),/failed/);
});
test("preparation deduplicates pending jobs and playback can wait for exactly the same stream",async()=>{
 const jobs=new api.BackgroundSpeech();let calls=0,complete;
 const result=new Promise(resolve=>complete=resolve);
 const first=jobs.prepare("m","version",()=>{calls++;return result;});
 const again=jobs.prepare("m","version",()=>{calls++;return result;});
 assert.equal(first,again);assert.equal(jobs.pending("m"),first);
 let ready=false;void jobs.pending("m").then(()=>ready=true);
 await Promise.resolve();assert.equal(calls,1);assert.equal(ready,false);
 complete(response([delta,done]));await first;assert.equal(ready,true);
 assert.equal(jobs.prepare("m","version",()=>{throw Error("duplicate call");}),first);
 await jobs.prepare("m","edited",async()=>{calls++;return response([delta,done]);});assert.equal(calls,2);
});
test("failed preparation allows a later manual retry",async()=>{
 const jobs=new api.BackgroundSpeech();
 await assert.rejects(jobs.prepare("m","v",async()=>new Response("",{status:503})));
 assert.equal(jobs.pending("m"),undefined);
 await jobs.prepare("m","v",async()=>response([delta,done]));
});

test("Listen reuses completed local audio without another request",async()=>{
 const jobs=new api.BackgroundSpeech();let calls=0;
 await jobs.prepare("m","v",async()=>{calls++;return response([delta,done]);});
 const result=await jobs.play("m",new AbortController().signal,{},()=>{});
 assert.ok(result.blob);assert.equal(result.blob.type,"audio/wav");
 assert.equal(result.blob.size,46);assert.equal(calls,1);
});
test("Listen plays received chunks while preparation is unfinished",async()=>{
 const jobs=new api.BackgroundSpeech();let stream;const pushes=[];let first=0,completed=false;
 const request=new Response(new ReadableStream({start(controller){stream=controller;}}),{headers:{"Content-Type":"text/event-stream"}});
 const pending=jobs.prepare("m","v",async()=>request);
 stream.enqueue(new TextEncoder().encode(delta));
 await new Promise(resolve=>setTimeout(resolve,0));
 const playback=jobs.play("m",new AbortController().signal,{async push(audio,rate){pushes.push([audio,rate]);},async finish(){}},()=>first++);
 void pending.then(()=>completed=true);
 await new Promise(resolve=>setTimeout(resolve,0));
 assert.equal(pushes.length,1);assert.equal(first,1);assert.equal(completed,false);
 stream.enqueue(new TextEncoder().encode(delta+done));stream.close();
 const result=await playback;assert.equal(result.played,true);assert.equal(pushes.length,2);
});
