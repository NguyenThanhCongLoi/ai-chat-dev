const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
const text=fs.readFileSync("src/i18n.ts","utf8");
const source=text.slice(0,text.indexOf("const ERROR_MESSAGES"))+
 text.slice(text.indexOf("export function restoredLanguage"),text.indexOf("export function localizeInterface"));
function fixture(storage){
 const exports={},document={documentElement:{lang:""}};
 vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports,localStorage:storage,document});
 return {api:exports,document};
}
test("selected language survives reopening and stale account defaults",()=>{
 const data=new Map(),{api,document}=fixture({getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)});
 assert.equal(api.restoredLanguage("en"),"en");
 api.rememberLanguage("my");assert.equal(document.documentElement.lang,"my");
 assert.equal(api.storedLanguage(),"my");assert.equal(api.restoredLanguage("vi"),"my");
 data.set("ui_language","unsupported");assert.equal(api.restoredLanguage("ja"),"ja");
});
test("blocked browser storage does not crash language loading",()=>{
 const {api,document}=fixture({getItem(){throw Error();},setItem(){throw Error();}});
 assert.equal(api.restoredLanguage("ko"),"ko");
 api.rememberLanguage("en");assert.equal(document.documentElement.lang,"en");
});
