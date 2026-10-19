const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),ts=require("../frontend/node_modules/typescript");
function load(path,globals={}){
 const exports={};
 const source=ts.transpileModule(fs.readFileSync(path,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 vm.runInNewContext(source,{exports,Response,localStorage:{getItem:()=>"vi"},setTimeout:f=>{f();return 0;},...globals});
 return exports;
}
const http=load("frontend/src/worlds/worldHttp.ts");
test("Modal plaintext with status 200 becomes a controlled service error",async()=>{
 await assert.rejects(http.readWorldJson(new Response("modal-http: upstream failure")),(e)=>e.status===503&&!e.message.includes("Unexpected token")&&!e.message.includes("modal-http"));
});
test("HTML, empty response, and proxy JSON strings are rejected",async()=>{
 for(const raw of ["<html>Gateway timeout</html>","","null",JSON.stringify("modal-http error")]){
  await assert.rejects(http.readWorldJson(new Response(raw)),e=>e.status===503);
 }
});
test("preserves API validation and authentication status",async()=>{
 await assert.rejects(http.readWorldJson(new Response(JSON.stringify({detail:"Sign in again"}),{status:401})),e=>e.status===401&&e.message==="Sign in again");
 assert.deepEqual(JSON.parse(JSON.stringify(await http.readWorldJson(new Response('{"enabled":true}')))),{enabled:true});
});
test("read-only API retries transient proxy responses once",async()=>{
 let calls=0;
 const api=load("frontend/src/worlds/types.ts",{require:()=>http,fetch:async()=>++calls===1?new Response("modal-http error"):new Response('{"ready":true}')});
 assert.equal((await api.api("/v1/moonfall")).ready,true);assert.equal(calls,2);
});
test("a save/action is never repeated automatically",async()=>{
 let calls=0;
 const api=load("frontend/src/worlds/types.ts",{require:()=>http,fetch:async()=>{calls++;return new Response("modal-http error");}});
 await assert.rejects(api.api("/v1/moonfall/run/act","POST",{action:"inspect"}),e=>e.status===503);
 assert.equal(calls,1);
});
