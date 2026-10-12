const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
const api={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/companionState.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:api});
test("companion is scoped to elf rather than unrelated characters",()=>{
 assert.equal(api.hasElfCompanion({name:"Selene Moonbrook"}),true);
 assert.equal(api.hasElfCompanion({name:"Translated name",preset_type:"elf"}),true);
 assert.equal(api.hasElfCompanion({name:"Ruby"}),false);
});
test("talk follows actual speech playback; idle and other speakers stay normal",()=>{
 const messages=[{id:"voice-elf",character_id:"elf"},{id:"voice-other",character_id:"other"}];
 assert.equal(api.companionTalking("elf","voice-elf",messages),true);
 assert.equal(api.companionTalking("elf",null,messages),false);
 assert.equal(api.companionTalking("elf","voice-other",messages),false);
});
