import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),esbuild=require('../frontend/node_modules/esbuild');
const compiled=esbuild.buildSync({entryPoints:['frontend/src/worlds/chapterSequence.ts'],bundle:true,platform:'node',format:'cjs',write:false}).outputFiles[0].text;
const module={exports:{}};new Function('module','exports',compiled)(module,module.exports);
const {chapterSequence,concealedSequenceEvents}=module.exports;
import {ChapterVoiceQueue} from '../frontend/src/worlds/ChapterVoiceQueue.ts';
const events=[
 {id:'warning',beat_id:'trap',type:'CHARACTER_SPEECH',auto_voice:true,presentation:'main',visual_event:'CHARACTER_ENTER'},
 {id:'movie',beat_id:'trap',type:'SYSTEM',visual_event:'ARROW_TRAP'},
 {id:'result',beat_id:'trap',type:'NARRATION',presentation:'main',visual_event:''},
 {id:'reaction',beat_id:'trap',type:'CHARACTER_SPEECH',auto_voice:true,presentation:'main',visual_event:'CHARACTER_ENTER'}
];
const run={chapter_id:'selene_01',intro_seen:true,assets:{trap:{type:'VIDEO'}},visual_events:{ARROW_TRAP:{cinematic:'trap'}},events};
const tick=()=>new Promise(r=>setImmediate(r));

test('warning must end before movie; reaction waits for ended, skip or fallback',async()=>{
 for(const completion of ['ended','skip','error']){
  const log=[];let finish;
  const lane=new ChapterVoiceQueue(async e=>{log.push(e.id);await new Promise(r=>finish=r);},()=>finish?.());
  lane.enqueue(chapterSequence(run,events));
  assert.deepEqual(log,['warning']);finish();await tick();
  assert.deepEqual(log,['warning','movie']);await tick();assert.equal(log.length,2);
  finish(completion);await tick();assert.equal(log.at(-1),'result');finish();await tick();
  assert.equal(log.at(-1),'reaction');finish();await tick();
 }
});
test('post-movie narration and dialogue remain concealed until their turn',()=>{
 assert.deepEqual(concealedSequenceEvents(run,new Set(['warning','movie'])),['result','reaction']);
 assert.deepEqual(concealedSequenceEvents(run,new Set(events.map(e=>e.id))),[]);
});
test('turning automatic speech off preserves the movie and text timeline',()=>{
 assert.deepEqual(chapterSequence(run,events,false).map(e=>e.id),events.map(e=>e.id));
});
test('stopping or leaving the world cannot resume a delayed reaction',async()=>{
 const log=[];let finish;const lane=new ChapterVoiceQueue(async e=>{log.push(e.id);await new Promise(r=>finish=r);},()=>finish?.());
 lane.enqueue(chapterSequence(run,events));finish();await tick();lane.cancel();await tick();
 assert.deepEqual(log,['warning','movie']);
});
