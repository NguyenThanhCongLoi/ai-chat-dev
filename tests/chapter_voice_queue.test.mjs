import test from "node:test";
import assert from "node:assert/strict";
import {ChapterVoiceQueue,autoVoiceEvents} from "../frontend/src/worlds/ChapterVoiceQueue.ts";
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test("new narrator events wait until character speech ends",async()=>{
 const log=[];let finish;
 const lane=new ChapterVoiceQueue(async e=>{log.push("start:"+e.id);await new Promise(r=>finish=r);log.push("end:"+e.id);},()=>finish?.());
 lane.enqueue([{id:"narrator"},{id:"character"}]);
 lane.enqueue([{id:"narrator"}]); // Another producer must not duplicate the opening.
 assert.deepEqual(log,["start:narrator"]);
 finish();await tick();
 assert.deepEqual(log,["start:narrator","end:narrator","start:character"]);
 lane.enqueue([{id:"next-narrator"}]);
 assert.equal(log.at(-1),"start:character");
 finish();await tick();
 assert.deepEqual(log.slice(-2),["end:character","start:next-narrator"]);
 finish();await tick();
});
test("explicit stop clears queued speech; a new request starts after cleanup",async()=>{
 const log=[];let finish;
 const lane=new ChapterVoiceQueue(async e=>{log.push(e.id);await new Promise(r=>finish=r);},()=>finish?.());
 lane.enqueue([{id:"old"},{id:"must-not-play"}]);
 lane.cancel();lane.enqueue([{id:"new"}]);await tick();
 assert.deepEqual(log,["old","new"]);finish();await tick();
});
test("failed audio does not block later speakers; replay is explicit",async()=>{
 const log=[];
 const lane=new ChapterVoiceQueue(async e=>{log.push(e.id);if(e.id==="broken")throw Error("decode");},()=>{});
 lane.enqueue([{id:"broken"},{id:"next"}]);await tick();
 lane.enqueue([{id:"next"}]);await tick();assert.deepEqual(log,["broken","next"]);
 lane.enqueue([{id:"next"}],true);await tick();assert.deepEqual(log,["broken","next","next"]);
});

test("chapters auto-read characters only; narrator remains explicitly playable",()=>{
 const events=[{id:"n",type:"NARRATION",voice_role:"NARRATOR"},{id:"c",type:"CHARACTER_SPEECH",voice_role:"CHARACTER"},{id:"t",type:"CHARACTER_THOUGHT"}];
 assert.deepEqual(autoVoiceEvents(events,"characters").map(e=>e.id),["c"]);
 assert.deepEqual(autoVoiceEvents(events,"silent"),[]);
 assert.deepEqual(autoVoiceEvents(events,"narrator").map(e=>e.id),["n"]);
 assert.deepEqual(autoVoiceEvents(events,"all").map(e=>e.id),["n","c"]);
});

test("completion waits for the entire dialogue queue, including the final clip",async()=>{
 const status=[];let finish;
 const lane=new ChapterVoiceQueue(async()=>new Promise(r=>finish=r),()=>finish?.(),busy=>status.push(busy));
 lane.enqueue([{id:"first"},{id:"last"}]);
 assert.deepEqual(status,[true]);
 finish();await tick();assert.deepEqual(status,[true]);
 finish();await tick();assert.deepEqual(status,[true,false]);
});
