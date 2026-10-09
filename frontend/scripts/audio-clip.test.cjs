const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript"),vm=require("node:vm");
const exportsObject={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("src/admin/audioClip.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:exportsObject,Blob,DataView,ArrayBuffer,Math,Number,Error});
const {encodeWavClip}=exportsObject;
test("WAV contains only selected samples, with valid PCM16 mono header",async()=>{
  const samples=new Float32Array([0,0,0,0,-1,-.5,.5,1,0,0,0,0]);
  const buffer={duration:3,sampleRate:4,length:12,numberOfChannels:1,getChannelData:()=>samples};
  const clip=encodeWavClip(buffer,1,2),bytes=await clip.arrayBuffer(),view=new DataView(bytes);
  assert.equal(clip.type,"audio/wav");assert.equal(bytes.byteLength,52);
  assert.equal(Buffer.from(bytes).subarray(0,4).toString(),"RIFF");
  assert.equal(view.getUint16(22,true),1);assert.equal(view.getUint32(24,true),4);
  assert.equal(view.getUint32(40,true),8);
  assert.deepEqual([0,1,2,3].map(i=>view.getInt16(44+i*2,true)),[-32768,-16384,16384,32767]);
});
test("Stereo is mixed to mono, selected duration is bounded",async()=>{
  const buffer={duration:20,sampleRate:2,length:40,numberOfChannels:2,getChannelData:i=>new Float32Array(40).fill(i?-.5:.5)};
  const bytes=await encodeWavClip(buffer,2,4).arrayBuffer();
  assert.equal(new DataView(bytes).getInt16(44,true),0);
  for(const [start,end] of [[-1,2],[2,1],[0,11],[19,21],[NaN,1]])assert.throws(()=>encodeWavClip(buffer,start,end));
});
