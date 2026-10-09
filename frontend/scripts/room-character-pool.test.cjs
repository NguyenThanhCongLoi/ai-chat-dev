const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
const api={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/roomCharacterPool.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:api});
test("system source stays populated after all presets were added to collection",()=>{
 const presets=[{id:"preset-a",preset_type:"a"},{id:"preset-b",preset_type:"b"}];
 const owned=[{id:"owned-a",creation_type:"preset",preset_type:"a"},{id:"owned-b",creation_type:"preset",preset_type:"b"},{id:"custom",creation_type:"custom"}];
 const pool=api.roomCharacterPool(owned,presets);
 assert.equal(pool.filter(item=>item.source==="system").length,2);
 assert.equal(pool.filter(item=>item.source==="owned").length,1);
 assert.equal(pool.length,3);
 assert.deepEqual(Array.from(pool.filter(item=>item.source==="system"),item=>item.character.id),["owned-a","owned-b"]);
});
test("new presets are selectable; hidden templates are not advertised",()=>{
 const pool=api.roomCharacterPool([],[{id:"preset",preset_type:"a"},{id:"hidden",preset_type:"b",home_section:"hidden"}]);
 assert.equal(pool.length,1);assert.equal(pool[0].character.id,"preset");
});
