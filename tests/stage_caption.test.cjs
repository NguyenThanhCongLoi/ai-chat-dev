const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript"),exportsObject={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("frontend/src/worlds/stageCaption.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:exportsObject});
const {stageCaption}=exportsObject;
test("chat replies and manual playback never replace authored stage direction",()=>{
 const authored={id:"scene",source:"authored",type:"CHARACTER_SPEECH",chapter_id:"selene_01",scene_id:"gate"};
 const chat={...authored,id:"chat",source:"ai"};
 const wrongMap={...authored,id:"other",scene_id:"other-map"};
 const hidden={...authored,id:"extra",presentation:"archive"};
 const run={chapter_id:"selene_01",location:"gate",events:[authored,chat,wrongMap,hidden],playing:"chat"};
 assert.equal(stageCaption(run).id,"scene");
 assert.equal(stageCaption({...run,playing:"other"}).id,"scene");
 assert.equal(stageCaption({...run,reviewing:true}),undefined);
});

test("a clue reaction remains on stage across logical steps of the same background",()=>{
 const clue={id:"clue",source:"authored",type:"CHARACTER_SPEECH",chapter_id:"selene_01",scene_id:"side_path"};
 const run={chapter_id:"selene_01",location:"ward_aftermath",events:[clue],locations:[{id:"ward_aftermath",scene_ids:["side_path","ward_aftermath"]}]};
 assert.equal(stageCaption(run).id,"clue");
});
