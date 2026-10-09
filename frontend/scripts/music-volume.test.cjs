const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
const api={};vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/musicVolume.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:api});
test("saved user volume persists, including zero, independently of CMS",()=>{
 const data=new Map(),storage={getItem:key=>data.get(key)??null,setItem:(key,value)=>data.set(key,value)};
 assert.equal(api.savedMusicVolume(storage),.3);
 assert.equal(api.saveMusicVolume(storage,.75),.75);assert.equal(api.savedMusicVolume(storage),.75);
 api.saveMusicVolume(storage,0);assert.equal(api.savedMusicVolume(storage),0);
});
test("invalid storage and excessive values remain valid HTML audio volumes",()=>{
 assert.equal(api.savedMusicVolume({getItem:()=>"invalid"}),.3);
 assert.equal(api.savedMusicVolume({getItem:()=>{throw Error();}}),.3);
 assert.equal(api.normalizedMusicVolume(3),1);
 assert.equal(api.normalizedMusicVolume(-1),0);
 assert.equal(api.saveMusicVolume({setItem:()=>{throw Error();}},.6),.6);
});
