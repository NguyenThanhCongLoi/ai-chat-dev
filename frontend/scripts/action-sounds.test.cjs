const {test}=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
const api={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/actionSoundDetector.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:api});
const sound=(id,triggers)=>({id,triggers,enabled:true,volume:1});
test("detects before narration closes and never repeats across chunks",()=>{
 const d=new api.ActionSoundDetector(),clips=[sound("pen",["đặt+bút+xuống"])];
 assert.equal(d.feed("***đặt bú",clips).length,0);
 assert.equal(d.feed("t xuống, ngước mắt",clips).length,1);
 assert.equal(d.feed(" nhìn bạn***",clips).length,0);
});
test("crow across a comma and page turn match the supplied examples",()=>{
 const d=new api.ActionSoundDetector(),clips=[sound("crow",["quạ+kêu"]),sound("page",["lật+trang"])];
 assert.equal(d.feed("***Con quạ trên xà nhà nghiêng đầu, kêu một tiếng khàn khàn.***",clips)[0][0].id,"crow");
 assert.equal(new api.ActionSoundDetector().feed(' ***Ngón tay khựng lại trên gáy sách, rồi tiếp tục lật trang như chưa có gì.***',clips)[0][0].id,"page");
 // Negation unrelated to the action should not suppress the page turn.
});
test("ordinary narration page turn works; dialogue and negated actions stay silent",()=>{
 const clips=[sound("page",["lật+trang"])];
 assert.equal(new api.ActionSoundDetector().feed('*tiếp tục lật trang*',clips).length,1);
 assert.equal(new api.ActionSoundDetector().feed('“Tôi sẽ lật trang.”',clips).length,0);
 assert.equal(new api.ActionSoundDetector().feed('*không lật trang*',clips).length,0);
});
test("variants are grouped; only one action per reply",()=>{
 const clips=[sound("a",["lật+trang"]),sound("b",["lật+trang"]),sound("c",["quạ+kêu"])];
 const result=new api.ActionSoundDetector().feed('*lật trang, quạ kêu*',clips);
 assert.equal(result.length,1);assert.equal(result[0].length,2);
});
test("English and Unicode action triggers; spoken text after closing stars is ignored",()=>{
 const clips=[sound("a",["put+pen+down","翻页"])];
 assert.equal(new api.ActionSoundDetector().feed('*puts the pen down* "put pen down"',clips).length,1);
 assert.equal(new api.ActionSoundDetector().feed('**翻页**',clips).length,1);
 assert.equal(new api.ActionSoundDetector().feed('*smiles* "put pen down"',clips).length,0);
});

test("later chunks with another action never trigger a second sound",()=>{
 const detector=new api.ActionSoundDetector(),clips=[sound("pen",["đặt+bút+xuống"]),sound("page",["lật+trang"])];
 assert.equal(detector.feed("*đặt bút xuống*",clips).length,1);
 assert.equal(detector.feed(" *lật trang*",clips).length,0);
});

test("a detected match is retryable until playback actually commits",()=>{
 const detector=new api.ActionSoundDetector(),clips=[sound("pen",["đặt+bút+xuống"])];
 assert.equal(detector.feed("*đặt bút xuống*",clips,false).length,1);
 assert.equal(detector.feed("",clips,false).length,1);
 detector.commit();
 assert.equal(detector.feed("",clips,false).length,0);
});
test("final response can recover missed action without replaying a committed sound",()=>{
 const detector=new api.ActionSoundDetector(),clips=[sound("page",["lật+trang"])];
 detector.feed("prefix",[],false);
 detector.replaceText("*lật trang*");
 assert.equal(detector.feed("",clips,false).length,1);
 detector.commit();detector.replaceText("*lật trang*");
 assert.equal(detector.feed("",clips,false).length,0);
});
