const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
const exportsObject={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/openingVoiceMessages.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:exportsObject});
const {openingVoiceMessages}=exportsObject;
const character=(id,character_id)=>({id,character_id,sender_type:"character",text:"Hello"});
test("all group greetings are queued in stored order, one per character",()=>{
 const messages=[character("a1","a"),character("b1","b"),character("a2","a")];
 assert.deepEqual(Array.from(openingVoiceMessages(messages),m=>m.id),["a1","b1"]);
});
test("opening a historical room does not autoplay later responses",()=>{
 const messages=[character("a1","a"),{sender_type:"user",id:"u"},character("b2","b"),character("a2","a")];
 assert.deepEqual(Array.from(openingVoiceMessages(messages),m=>m.id),["a1"]);
});
test("a room with no opening greeting does not read a historical answer",()=>{
 assert.equal(openingVoiceMessages([{sender_type:"user"},character("a2","a")]).length,0);
});
