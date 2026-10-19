const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ts=require("../frontend/node_modules/typescript");
const React=require("../frontend/node_modules/react");
const {renderToStaticMarkup}=require("../frontend/node_modules/react-dom/server");
const out={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("frontend/src/worlds/EmbeddedScene.tsx","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,{exports:out,require:name=>name==="react/jsx-runtime"?require("../frontend/node_modules/react/jsx-runtime"):{preparedImageSource:s=>s}});
const object={id:"clue",mode:"embedded",interactive:true,discovered:false,x:.4,y:.4,width:.1,height:.1,polygon:[[.4,.4],[.5,.4],[.5,.5]],title:"Clue"};
function render(o,blocked=false){return renderToStaticMarkup(React.createElement(out.default,{run:{objects:[o],embedded_scene:{cleanups:[]},assets:{}},blocked,onInspect:()=>{},inspectLabel:"Inspect "}));}
test("ordinary active clues have a glimmer without revealing secret optional clues",()=>{
 assert.match(render(object),/data-hint-for="clue"/);
 const secret=render({...object,optional:true});
 assert.doesNotMatch(secret,/maItemLight/);
 assert.match(secret,/data-world-target="clue"/);
 assert.match(secret,/aria-disabled="false"/);
});
test("blocked and collected targets have no guiding glimmer",()=>{
 assert.doesNotMatch(render(object,true),/maItemLight/);
 assert.doesNotMatch(render({...object,discovered:true}),/maItemLight/);
});
