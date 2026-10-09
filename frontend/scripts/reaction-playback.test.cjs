const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
const api={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/reactionPlayback.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:api,setTimeout,clearTimeout});
function player(){return {paused:false,play(){return Promise.resolve();},pause(){this.paused=true;}};}
test("dialogue waits until reaction ends",async()=>{
 const audio=player();let dialogue=false;
 const run=api.playReactionClip(audio);
 const voice=run.finished.then(()=>{dialogue=true;});
 await Promise.resolve();assert.equal(dialogue,false);
 audio.onended();await voice;assert.equal(dialogue,true);assert.equal(audio.paused,true);
});
test("muting or leaving releases the pending dialogue gate",async()=>{
 const audio=player(),run=api.playReactionClip(audio);run.cancel();await run.finished;
 assert.equal(audio.paused,true);assert.equal(audio.onended,null);
});
test("failed reaction does not prevent dialogue playback",async()=>{
 const audio=player();audio.play=()=>Promise.reject(Error("blocked"));
 await api.playReactionClip(audio).finished;assert.equal(audio.paused,true);
});
test("reaction deadline prevents stalled audio from blocking dialogue",async()=>{
 const audio=player();await api.playReactionClip(audio,15).finished;
 assert.equal(audio.paused,true);
});
