const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
const exportsObject={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/admin/musicAudioClip.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:exportsObject,Blob,DataView,ArrayBuffer,Math,Number,Error});
const {encodeMusicClip}=exportsObject;
test("music crop keeps stereo and only selected samples",async()=>{
 const buffer={duration:3,sampleRate:2,length:6,numberOfChannels:2,getChannelData:i=>new Float32Array(i?[0,0,.5,1,0,0]:[0,0,-.5,-1,0,0])};
 const blob=encodeMusicClip(buffer,1,2),view=new DataView(await blob.arrayBuffer());
 assert.equal(view.getUint16(22,true),2);assert.equal(view.getUint32(40,true),8);
 assert.deepEqual([0,1,2,3].map(i=>view.getInt16(44+i*2,true)),[-16384,16384,-32768,32767]);
});
test("music supports more than ten seconds but rejects invalid range and oversized WAV",()=>{
 const buffer={duration:60,sampleRate:8,length:480,numberOfChannels:2,getChannelData:()=>new Float32Array(480)};
 assert.ok(encodeMusicClip(buffer,5,35).size>44);
 for(const [a,b] of [[-1,2],[2,1],[0,61],[NaN,1]])assert.throws(()=>encodeMusicClip(buffer,a,b));
 assert.throws(()=>encodeMusicClip({...buffer,sampleRate:192000,length:11520000},0,60),/20 MB/);
});
