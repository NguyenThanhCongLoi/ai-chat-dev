const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ts=require('../frontend/node_modules/typescript'),exportsTiming={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('frontend/src/worlds/introTiming.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:exportsTiming});
test('intro accepts natural speech and modest acceleration within the cue',()=>{
 assert.equal(exportsTiming.introVoiceRate(3,{start:0,end:4}),1);
 assert.ok(exportsTiming.introVoiceRate(4.5,{start:0,end:4})<=1.25);
});
test('intro refuses voice that would cross a planned music-only pause',()=>{
 assert.throws(()=>exportsTiming.introVoiceRate(6,{start:0,end:4}),/longer than its cue/);
 assert.throws(()=>exportsTiming.introVoiceRate(Infinity,{start:0,end:4}),/Invalid/);
});
