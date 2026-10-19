import test from "node:test";
import assert from "node:assert/strict";
import {chapterCinematicAllowed,spokenBeat} from "../frontend/src/worlds/chapterPresentation.ts";
test("chapter 2 never chains pendant transitions, exits, or generic rooftop outros",()=>{
 const run={chapter_id:"selene_02",intro_seen:true};
 for(const visual_event of ["MEMORY_TRIGGER","MEMORY_RECONSTRUCTION_START","MEMORY_RECONSTRUCTION_END","CHAPTER_COMPLETE","LOCATION_ENTER","MAGIC_SEAL_ACTIVATE","VAULT_AWAKEN"]){
  assert.equal(chapterCinematicAllowed(run,{visual_event}),false,visual_event);
 }
});
test("all eight chapters have only their own justified incidental clips",()=>{
 for(let n=1;n<=8;n++){
  const run={chapter_id:"selene_"+String(n).padStart(2,"0"),intro_seen:true,ending:{id:"between_memory_and_moonlight"}};
  assert.equal(chapterCinematicAllowed(run,{visual_event:"MAGIC_SEAL_ACTIVATE"}),n===3||n===7);
  assert.equal(chapterCinematicAllowed(run,{visual_event:"VAULT_AWAKEN"}),n===6);
  assert.equal(chapterCinematicAllowed(run,{visual_event:"CHAPTER_COMPLETE"}),n===8);
  assert.equal(chapterCinematicAllowed(run,{visual_event:"MEMORY_RECONSTRUCTION_END"}),false);
  assert.equal(chapterCinematicAllowed(run,{visual_event:"WORLD_INTRO"}),false);
 }
});
test("wrong-chapter events cannot start a stale video",()=>{
 assert.equal(chapterCinematicAllowed({chapter_id:"selene_06",intro_seen:true},{visual_event:"VAULT_AWAKEN",chapter_id:"selene_03"}),false);
});
test("at most one automatic character line per interaction; hidden extras never queue",()=>{
 const events=[{id:"world",type:"NARRATION"},{id:"s",type:"CHARACTER_SPEECH"},{id:"npc",type:"CHARACTER_SPEECH"},{id:"extra",type:"CHARACTER_SPEECH",auto_voice:false}];
 assert.deepEqual(spokenBeat(events).map(e=>e.id),["s"]);
 assert.deepEqual(spokenBeat([{type:"CHARACTER_SPEECH",auto_voice:false}]),[]);
});

test("an ominous ending never receives the peaceful terrace outro",()=>{assert.equal(chapterCinematicAllowed({chapter_id:"selene_08",intro_seen:true,ending:{id:"remember_me"}},{visual_event:"CHAPTER_COMPLETE"}),false);});
