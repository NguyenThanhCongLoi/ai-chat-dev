type MusicBuffer=Pick<AudioBuffer,"duration"|"sampleRate"|"length"|"numberOfChannels"|"getChannelData">;
export function encodeMusicClip(buffer:MusicBuffer,start:number,end:number):Blob {
  if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start||end>buffer.duration+.001)
    throw Error("Chọn điểm bắt đầu và kết thúc hợp lệ.");
  const channels=buffer.numberOfChannels,rate=buffer.sampleRate;
  if(!Number.isInteger(channels)||channels<1||channels>8||!Number.isFinite(rate)||rate<=0)throw Error("Audio không hợp lệ.");
  const first=Math.floor(start*rate),last=Math.min(buffer.length,Math.floor(end*rate)),count=last-first;
  if(count<1)throw Error("Đoạn được chọn quá ngắn.");
  const size=count*channels*2;
  if(size+44>20*1024*1024)throw Error("Đoạn nhạc sau cắt vượt 20 MB. Hãy chọn đoạn ngắn hơn.");
  const bytes=new ArrayBuffer(44+size),view=new DataView(bytes);
  const text=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
  text(0,"RIFF");view.setUint32(4,36+size,true);text(8,"WAVE");text(12,"fmt ");
  view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,channels,true);
  view.setUint32(24,rate,true);view.setUint32(28,rate*channels*2,true);
  view.setUint16(32,channels*2,true);view.setUint16(34,16,true);text(36,"data");view.setUint32(40,size,true);
  const samples=Array.from({length:channels},(_,i)=>buffer.getChannelData(i));
  for(let i=0;i<count;i++)for(let channel=0;channel<channels;channel++){
    const value=Math.max(-1,Math.min(1,samples[channel][first+i]));
    view.setInt16(44+(i*channels+channel)*2,Math.round(value<0?value*32768:value*32767),true);
  }
  return new Blob([bytes],{type:"audio/wav"});
}
