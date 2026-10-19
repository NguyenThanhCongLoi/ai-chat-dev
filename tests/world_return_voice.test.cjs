const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript"),out={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("frontend/src/roleplay/openingVoiceMessages.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:out});
const greet={id:"hello",sender_type:"character",character_id:"selene",text:"Hello"};
const question={id:"question",sender_type:"user",text:"Remember Moonfall?"};
const latest={...greet,id:"latest",text:"I still remember our discovery."};
test("World return selects the most recent character dialogue instead of a greeting",()=>{
 const messages=[greet,question,latest,{id:"event",sender_type:"system",text:"Returned"}];
 assert.equal(out.openingVoiceMessages(messages,true)[0].id,"latest");
 assert.equal(out.openingVoiceMessages(messages)[0].id,"hello");
});
test("World return never autoplays a user or empty message",()=>{
 assert.equal(out.openingVoiceMessages([question],true).length,0);
 assert.equal(out.openingVoiceMessages([latest,{...greet,id:"empty",text:"  "}],true)[0].id,"latest");
});
