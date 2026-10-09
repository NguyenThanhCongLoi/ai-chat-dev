const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
function load(path,extra={}){const exports={};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports,require:()=>({}),...extra});return exports;}
test("unsupported or unknown content hides Listen regardless of UI language",()=>{
 const {canSpeak}=load("src/roleplay/voicePreferences.ts");
 assert.equal(canSpeak({text:"Hello",speech_supported:true}),true);
 assert.equal(canSpeak({text:"Hello",speech_supported:false}),false);
 assert.equal(canSpeak({text:"你好"}),false);
 assert.equal(canSpeak({text:"xyz"}),false);
 assert.equal(canSpeak({text:"Hello",speech_supported:true,interrupted:true}),false);
});
test("PCM and cached audio share protected gain up to 200%",()=>{
 const changes=[],connections=[];let media;let closed=false;
 function node(){return {connect(value){connections.push(value);},disconnect(){}};}
 class Context{
  currentTime=2;destination={};
  createGain(){return {...node(),gain:{setTargetAtTime(...args){changes.push(args);}}};}
  createDynamicsCompressor(){return {...node(),threshold:{},knee:{},ratio:{},attack:{},release:{}};}
  createWaveShaper(){return {...node(),curve:null};}
  createMediaElementSource(audio){media=audio;return node();}
  resume(){return Promise.resolve();}
  close(){closed=true;return Promise.resolve();}
 }
 const {PcmStreamPlayer}=load("src/roleplay/streamSpeech.ts",{AudioContext:Context});
 const player=new PcmStreamPlayer();assert.equal(connections.length,3);
 player.setVolume(.3);assert.deepEqual(changes.at(-1),[.3,2,.015]);
 player.setVolume(1.5);assert.equal(changes.at(-1)[0],1.5);
 player.setVolume(5);assert.equal(changes.at(-1)[0],2);
 player.setVolume(-5);assert.equal(changes.at(-1)[0],0);
 player.setVolume(NaN);assert.equal(changes.at(-1)[0],.8);
 const audio={volume:.8};player.connectMedia(audio);
 assert.equal(media,audio);assert.equal(audio.volume,1);assert.equal(connections.length,4);
 player.stop();assert.equal(closed,true);
});

test("autoplay uses fresh stream metadata before React commits the draft",()=>{
 const {playbackMessage,canSpeak}=load("src/roleplay/voicePreferences.ts");
 const draft={id:"m",text:"*looks up*",speech_supported:false};
 const stream={id:"m",text:"Hello!",speech_supported:true};
 assert.equal(playbackMessage("m",true,[draft],stream,null),stream);
 assert.equal(canSpeak(playbackMessage("m",true,[draft],stream,null)),true);
 assert.equal(playbackMessage("m",false,[draft],stream,null),draft);
 const interrupted={...draft,interrupted:true};
 assert.equal(playbackMessage("m",true,[interrupted],stream,null),interrupted);
 assert.equal(canSpeak(playbackMessage("m",true,[interrupted],stream,null)),false);
});


test("group speech never autoplays, single rooms still autoplay",()=>{
 const {shouldAutoplaySpeech,canSpeak}=load("src/roleplay/voicePreferences.ts");
 assert.equal(shouldAutoplaySpeech(1),true);
 for(const count of [0,2,3,4,5,6])assert.equal(shouldAutoplaySpeech(count),false);
 assert.equal(canSpeak({text:"Hello",speech_supported:true}),true);
});
