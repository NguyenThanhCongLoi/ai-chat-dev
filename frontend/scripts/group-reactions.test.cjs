const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
function fixture(){
 const players={a:{plays:0,currentTime:0,play(){this.plays++;return Promise.resolve()},pause(){}},
                b:{plays:0,currentTime:0,play(){this.plays++;return Promise.resolve()},pause(){}}};
 const effects=[];
 function compile(file,requireFn){
  const exports={};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{
   exports,require:requireFn,setTimeout,clearTimeout,Date,
   document:{visibilityState:"visible",addEventListener(){},removeEventListener(){}},
   localStorage:{getItem(){return "on"},setItem(){}},window:{frameElement:null,clearTimeout,setTimeout},
  });return exports;
 }
 const playback=compile("src/roleplay/reactionPlayback.ts");
 const api=compile("src/roleplay/useReactionSounds.ts",name=>{
  if(name==="react")return {useRef:value=>({current:value}),useState:value=>[value,()=>{}],useEffect:fn=>effects.push(fn)};
  if(name==="./reactionPlayback")return playback;
  if(name==="./reactionCache")return {
   cachedReactions:(_user,id)=>[{id:"clip-"+id,emotion:"happy",target:"vi",voice_id:"voice-"+id,volume:.5,player:players[id]}],
   clearReactionCache(){},prepareCharacterReactions(_user,id){return Promise.resolve([{id:"clip-"+id,emotion:"happy",target:"vi",voice_id:"voice-"+id,volume:.5,player:players[id]}])}
  };
  throw Error(name);
 });
 const hook=api.useReactionSounds("room","user",["a","b"]);
 const cleanup=effects.map(fn=>fn());
 return {hook,players,cleanup:()=>cleanup.forEach(fn=>fn?.())};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test("each group speaker plays their clip in sequence without dialogue autoplay",async()=>{
 const {hook,players,cleanup}=fixture();
 try{
  const first=hook.react("reply-a","a","happy","vi","voice-a");
  assert.equal(hook.react("reply-a","a","happy","vi","voice-a"),first);
  const second=hook.react("reply-b","b","happy","vi","voice-b");
  await tick();assert.equal(players.a.plays,1);assert.equal(players.b.plays,0);
  players.a.onended();await first;await tick();
  assert.equal(players.b.plays,1);
  players.b.onended();await second;
 }finally{cleanup()}
});
test("mute cancels active group clip and prevents queued speaker clip",async()=>{
 const {hook,players,cleanup}=fixture();
 try{
  const first=hook.react("reply-a","a","happy","vi","voice-a");
  const second=hook.react("reply-b","b","happy","vi","voice-b");
  await tick();hook.toggle();await Promise.all([first,second]);
  assert.equal(players.a.plays,1);assert.equal(players.b.plays,0);
 }finally{cleanup()}
});


test("new user turn discards old queued group beats",async()=>{
 const {hook,players,cleanup}=fixture();
 try{
  const first=hook.react("old-a","a","happy","vi","voice-a");
  const queued=hook.react("old-b","b","happy","vi","voice-b");
  await tick();hook.stop();await Promise.all([first,queued]);
  assert.equal(players.a.plays,1);assert.equal(players.b.plays,0);
  const fresh=hook.react("new-b","b","happy","vi","voice-b");
  await tick();assert.equal(players.b.plays,1);
  players.b.onended();await fresh;
 }finally{cleanup()}
});
