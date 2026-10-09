const { test }=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
function load(name, context) {
  const module={exports:{}};
  const source=ts.transpileModule(fs.readFileSync(path.join(__dirname,"../src/"+name+".ts"),"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText.replaceAll("import.meta.glob","testGlob").replaceAll("import.meta.env","testEnv");
  vm.runInNewContext(source,{...context,exports:module.exports,module});
  return module.exports;
}
function fixture(catalog, translate) {
  const storage=new Map(), frames=[], root={inert:false,setAttribute(){}};
  const win={location:{origin:"http://localhost"},addEventListener(){}};win.parent=win;
  const validation=load("uiTranslationValidation",{});
  const context={
    testGlob:(pattern)=>pattern.includes("catalog")?{"./locales/catalog.json":catalog}:{},
    testEnv:{}, localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
    document:{getElementById:()=>root,querySelectorAll:()=>[]},window:win,
    fetch:async(_url, options)=>({ok:true,json:async()=>({translations:translate(JSON.parse(options.body).texts)})}),
    AbortSignal,requestAnimationFrame:callback=>frames.push(callback),
    require:()=>validation,
  };
  return {api:load("uiLocales",context),storage,root,frames};
}
test("reject missing, identity fallback, wrong script and lost placeholders",()=>{
  const {validUiTranslation:v}=load("uiTranslationValidation",{});
  assert.equal(v("Tâm lý","Mental Wellbeing","ja","Mental Wellbeing"),false);
  assert.equal(v("Tâm lý","Tâm lý","en","Mental Wellbeing"),false);
  assert.equal(v("Tâm lý","心のケア","ja","Mental Wellbeing"),true);
  assert.equal(v("Xóa {name}","削除","ja"),false);
  assert.equal(v("Xóa {name}","{name}を削除","ja"),true);
  assert.equal(v("Loading…","Loading…","en"),true);
  assert.equal(v("×","×","zh"),true);
  assert.equal(v("123","123","my"),true);
  assert.equal(v("×","错误","zh"),false);
  for (const source of ["x","https://…","PNG, JPEG, WEBP · GIF"])
    for (const language of ["en","zh","ja","ko","my"])
      assert.equal(v(source,source,language),true);
  assert.equal(v("Nhập URL","Nhập URL","zh"),false);
  assert.equal(v("Ảnh PNG","Ảnh PNG","ja"),false);
});
test("a partial response cannot be marked complete or cached",async()=>{
  const f=fixture([{source:"Tâm lý",en:"Mental Wellbeing"}],()=>["Tâm lý"]);
  await assert.rejects(f.api.loadCompleteUiTranslations("ja"),/invalid_translation/);
  assert.equal(f.storage.has("ui_complete_v1:ja"),false);
});
test("complete translations are cached and all batches are validated",async()=>{
  let calls=0;
  const sources=Array.from({length:121},(_,i)=>({source:"Mục thứ "+i,en:"Item "+i}));
  const f=fixture(sources, texts=>{calls++;return texts.map(text=>"項目 "+text);});
  const pack=await f.api.loadCompleteUiTranslations("ja");
  assert.equal(Object.keys(pack).length,121);
  assert.equal(calls,2);
  await f.api.loadCompleteUiTranslations("ja");
  assert.equal(calls,2);
});
test("lock remains on errors, and opens only after explicit success",()=>{
  const f=fixture([],()=>[]);
  f.api.setUiLanguageGate({language:"ja",busy:true});
  assert.equal(f.root.inert,true);
  f.api.setUiLanguageGate({language:"ja",busy:false,error:"failed"});
  assert.equal(f.root.inert,true);
  f.api.setUiLanguageGate({language:"ja",busy:false});
  assert.equal(f.root.inert,false);
});
test("wait for two animation frames before unlocking after rendering",async()=>{
  const f=fixture([],()=>[]);let done=false;
  const promise=f.api.afterUiLanguagePaint().then(()=>{done=true;});
  assert.equal(f.frames.length,1);
  f.frames.shift()();
  assert.equal(done,false);
  f.frames.shift()();
  await promise;
  assert.equal(done,true);
});
test("introduction translations reuse cache and do not change source",async()=>{
  let calls=0;const source="Chào bạn, mình là Ruby.";
  const f=fixture([], texts=>{calls++;return texts.map(()=>"こんにちは、Rubyです。");});
  assert.equal((await f.api.loadCharacterIntroductions("ja",[source]))[source],"こんにちは、Rubyです。");
  await f.api.loadCharacterIntroductions("ja",[source]);
  assert.equal(calls,1);
  assert.equal(source,"Chào bạn, mình là Ruby.");
});

test("counted Role Play tabs translate in every bundled language",()=>{
  const api=load("i18n",{});
  for (const language of ["en","zh","ja","ko","my"]) {
    const pack=JSON.parse(fs.readFileSync(path.join(__dirname,"../src/locales/"+language+".json"),"utf8"));
    api.setRuntimeTranslations(pack);
    assert.equal(api.translateUiText("Nhân vật của tôi (6)",language),pack["Nhân vật của tôi"]+" (6)");
    assert.equal(api.translateUiText("Nhân vật hệ thống (9)",language),pack["Nhân vật hệ thống"]+" (9)");
  }
  assert.equal(api.translateUiText("Nhân vật của tôi (6)","vi"),"Nhân vật của tôi (6)");
});
test("long character descriptions are translated fully in small requests",async()=>{
  const seen=[];
  const f=fixture([],texts=>{seen.push(texts);return texts.map(text=>"日本語 "+text);});
  const source="Một câu giới thiệu nhân vật cần dịch đầy đủ. ".repeat(90);
  const result=await f.api.loadCharacterIntroductions("ja",[source],"long-test");
  assert.ok(result[source].length>1200);
  assert.ok(seen.every(batch=>batch.length<=6 && batch.every(text=>text.length<=900) &&
    batch.reduce((sum,text)=>sum+text.length,0)<=1800));
  assert.equal(source,"Một câu giới thiệu nhân vật cần dịch đầy đủ. ".repeat(90));
});
test("introduction retry reuses successful pieces from before an error",async()=>{
  const seen=[];let fail=true;
  const f=fixture([],texts=>{
    seen.push(texts);
    if(fail && seen.length===2) throw new Error("temporary failure");
    return texts.map(text=>"日本語 "+text);
  });
  const source=Array.from({length:100},(_,i)=>"Dòng mô tả nhân vật số "+i+" rất dài và đầy đủ. ").join("");
  await assert.rejects(f.api.loadCharacterIntroductions("ja",[source],"resume-test"));
  const first=seen[0][0];
  fail=false;
  await f.api.loadCharacterIntroductions("ja",[source],"resume-test");
  assert.equal(seen.filter(batch=>batch.includes(first)).length,1);
});
test("runtime translation failure reports introduction stage without secrets",async()=>{
  const f=fixture([],()=>["Chào bạn"]);
  await assert.rejects(f.api.loadCharacterIntroductions("ja",["Chào bạn"]),error=>{
    assert.equal(error.stage,"introductions");
    assert.equal(error.code,"invalid_translation");
    assert.match(f.api.uiLanguageErrorMessage(error,"ja"),/Character introductions/);
    return true;
  });
});

test("bundled Myanmar slogans do not call the translation API",async()=>{
  const pack=JSON.parse(fs.readFileSync(path.join(__dirname,"../src/locales/my.json"),"utf8"));
  const entries=["Bước vào câu chuyện.","Sống cùng nhân vật."].map(source=>({source,en:""}));
  const storage=new Map();
  const win={location:{origin:"http://localhost"},addEventListener(){}};win.parent=win;
  const api=load("uiLocales",{
    testGlob:pattern=>pattern.includes("catalog")?{"./locales/catalog.json":entries}:{"./locales/my.json":pack},
    testEnv:{},localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
    window:win,document:{getElementById:()=>null,querySelectorAll:()=>[]},
    fetch:()=>assert.fail("Complete bundled slogans must never trigger translation"),
    require:()=>load("uiTranslationValidation",{}),
  });
  const result=await api.loadCompleteUiTranslations("my");
  assert.equal(result[entries[0].source],pack[entries[0].source]);
  assert.equal(result[entries[1].source],pack[entries[1].source]);
});
