const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript");
function fixture(){
 const contexts=[];
 class Context{
 state="running";currentTime=0;destination={};
 constructor(){this.closed=0;contexts.push(this);}
 createGain(){return {connect(){},disconnect(){},gain:{setValueAtTime(){},setTargetAtTime(){}}};}
 createMediaElementSource(){return {connect(){},disconnect(){}};}
 resume(){return Promise.resolve();}
 close(){this.closed++;this.state="closed";return Promise.resolve();}
 }
 const exports={};vm.runInNewContext(ts.transpileModule(fs.readFileSync("frontend/src/roleplay/musicAudio.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports,window:{AudioContext:Context}});
 return {MusicAudio:exports.MusicAudio,Context,contexts};
}
test("prepared World clips share a context without closing one another",async()=>{
 const f=fixture(),shared=new f.Context(),sound=()=>({volume:1,play:()=>Promise.resolve()});
 const first=new f.MusicAudio(sound(),()=>shared),second=new f.MusicAudio(sound(),()=>shared);
 await first.play();await second.play();first.dispose();
 assert.equal(f.contexts.length,1);assert.equal(shared.closed,0);
 await second.play();second.dispose();assert.equal(shared.closed,0);
});
test("ordinary chat music retains its existing private-context lifecycle",async()=>{
 const f=fixture(),music=new f.MusicAudio({volume:1,play:()=>Promise.resolve()});
 await music.play();music.dispose();assert.equal(f.contexts.length,1);assert.equal(f.contexts[0].closed,1);
});
