const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),ts=require("typescript");
function fixture(fetcher){
 const calls=[],revoked=[];let id=0;
 const exports={};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/roleplay/musicTrackCache.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{
  exports,AbortController,setTimeout,clearTimeout,
  fetch:async(url,options)=>{calls.push(url);return fetcher?fetcher(url,options):{ok:true,headers:{get:()=>10},blob:async()=>({size:10})};},
  URL:{createObjectURL:()=>"blob:"+ ++id,revokeObjectURL:url=>revoked.push(url)}
 });
 return {cache:new exports.MusicTrackCache(),calls,revoked};
}
test("next song preload is reused without a second download",async()=>{
 const {cache,calls}=fixture();
 const [first,second]=await Promise.all([cache.get("/song"),cache.get("/song")]);
 assert.equal(first,second);assert.equal(first,"blob:1");assert.equal(calls.length,1);
 assert.equal(await cache.get("/song"),first);assert.equal(calls.length,1);
 cache.dispose();
});
test("cache only holds two songs and revokes old buffers",async()=>{
 const {cache,revoked}=fixture();
 await cache.get("/one");await cache.get("/two");await cache.get("/three");
 assert.deepEqual(revoked,["blob:1"]);cache.dispose();
 assert.deepEqual(revoked,["blob:1","blob:2","blob:3"]);
});
test("failed preloading falls back to streaming and can retry",async()=>{
 const {cache,calls}=fixture(async()=>{throw Error("offline");});
 assert.equal(await cache.get("/song"),"/song");
 assert.equal(await cache.get("/song"),"/song");
 assert.equal(calls.length,2);cache.dispose();
});
test("disposed preload cannot retain a late buffer",async()=>{
 let release;
 const {cache,revoked}=fixture(()=>new Promise(resolve=>{release=resolve;}));
 const pending=cache.get("/song");cache.dispose();
 release({ok:true,headers:{get:()=>10},blob:async()=>({size:10})});
 assert.equal(await pending,"/song");assert.deepEqual(revoked,[]);
});

test("playlist can use native URL immediately while preload is pending",async()=>{
 let release;
 const {cache}=fixture(()=>new Promise(resolve=>{release=resolve;}));
 const pending=cache.get("/song");
 assert.equal(cache.ready("/song"),undefined);
 assert.equal(cache.ready("/song")??"/song","/song");
 release({ok:true,headers:{get:()=>10},blob:async()=>({size:10})});
 await pending;
 assert.equal(cache.ready("/song"),"blob:1");
 cache.dispose();
 assert.equal(cache.ready("/song"),undefined);
});
