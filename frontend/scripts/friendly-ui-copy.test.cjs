const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
const api={};vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/friendlyUiCopy.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:api});
test("waiting copy is available before language packs load for every supported language",()=>{
 for(const code of ["vi","en","zh","ja","ko","my","km"]) {
  assert.ok(api.friendlyWaitingText(code).length>10);
  assert.ok(api.friendlyLanguageLoadingText(code).length>10);
  if(code!=="vi")assert.notEqual(api.friendlyWaitingText(code),api.friendlyWaitingText("vi"));
 }
 assert.equal(api.friendlyWaitingText("invalid"),api.friendlyWaitingText("en"));
});
test("native target scripts and clear task meaning survive the friendly tone",()=>{
 const scripts={zh:/[一-龯]/,ja:/[ぁ-ん]/,ko:/[가-힣]/,my:/[\u1000-\u109f]/,km:/[\u1780-\u17ff]/};
 for(const [code,pattern] of Object.entries(scripts))assert.match(api.friendlyLanguageLoadingText(code),pattern);
 assert.match(api.friendlyLanguageLoadingText("en"),/language/);
});
