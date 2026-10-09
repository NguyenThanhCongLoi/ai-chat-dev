const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
function fixture(){
 const events=[],parameter={setValueAtTime:(v)=>events.push(["initial",v]),setTargetAtTime:(v)=>events.push(["volume",v])};
 class Context{
  state="suspended";currentTime=0;destination={};
  createGain(){return {gain:parameter,connect(){},disconnect(){}};}
  createMediaElementSource(audio){assert.equal(audio.crossOrigin,"anonymous");events.push(["source"]);return {connect(){},disconnect(){}};}
  resume(){events.push(["resume"]);this.state="running";return Promise.resolve();}
  close(){events.push(["close"]);return Promise.resolve();}
 }
 const exports={};vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/musicAudio.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports,window:{AudioContext:Context}});
 const audio={volume:1,crossOrigin:"",play(){events.push(["play"]);return Promise.resolve();}};
 return {music:new exports.MusicAudio(audio),audio,events};
}
test("mobile volume uses gain rather than unsupported media.volume; graph is reused",async()=>{
 const {music,audio,events}=fixture();
 music.setVolume(.6);await music.play();
 assert.equal(audio.volume,1);assert.deepEqual(events.slice(0,4),[["source"],["initial",.6],["resume"],["play"]]);
 music.setVolume(.15);assert.deepEqual(events.at(-1),["volume",.15]);assert.equal(audio.volume,1);
 music.setVolume(0);assert.deepEqual(events.at(-1),["volume",0]);
 await music.play();assert.equal(events.filter(e=>e[0]==="source").length,1);
 music.dispose();assert.deepEqual(events.at(-1),["close"]);
});
test("music gain clamps volume and voice ducking restores the selected level",async()=>{
 const {music,events}=fixture();await music.play();
 music.setVolume(.8*.25);assert.deepEqual(events.at(-1),["volume",.2]);
 music.setVolume(.8);assert.deepEqual(events.at(-1),["volume",.8]);
 music.setVolume(5);assert.deepEqual(events.at(-1),["volume",1]);
 music.setVolume(-1);assert.deepEqual(events.at(-1),["volume",0]);music.dispose();
});
