import {useEffect,useRef} from "react";
import "./memoryLocationEffects.css";
type Props={profile:number;active:boolean;transitionKey:string;eventKey?:string;eventType?:string};
/** Presentation only: one bounded 2D canvas, no story mutations or WebGL. */
export function MemoryLocationEffects({profile,active,transitionKey,eventKey="",eventType=""}:Props){
 const ref=useRef<HTMLCanvasElement>(null),pulse=useRef({key:"",type:"",at:0});
 useEffect(()=>{if(pulse.current.key!==eventKey)pulse.current={key:eventKey,type:eventType,at:performance.now()};},[eventKey,eventType]);
 useEffect(()=>{
  const canvas=ref.current;if(!canvas)return;
  const ctx=canvas.getContext("2d");if(!ctx)return;
  const reduced=matchMedia("(prefers-reduced-motion: reduce)"),saveData=(navigator as Navigator&{connection?:{saveData:boolean}}).connection?.saveData;
  let visible=true,frame=0,last=0,clock=0,measure=0,count=0,lite=!!saveData,w=1,h=1,dpr=1,noiseStep=-1,noisePattern:CanvasPattern|null=null;
  const total=[0,40,50,30,45,25,53,40,32][profile]||30;
  const particles=Array.from({length:total},(_,i)=>({x:((i*137.508)%997)/997,y:((i*73.331)%991)/991,r:1+(i%3),phase:i*2.399,speed:10+(i*7%21)}));
  const sprite=document.createElement("canvas");sprite.width=sprite.height=64;
  const sc=sprite.getContext("2d")!;
  const gradient=sc.createRadialGradient(32,32,0,32,32,32);gradient.addColorStop(0,"rgba(207,228,255,.8)");gradient.addColorStop(1,"rgba(207,228,255,0)");sc.fillStyle=gradient;sc.fillRect(0,0,64,64);
  const grain=document.createElement("canvas");grain.width=grain.height=96;
  const gc=grain.getContext("2d")!;
  const resize=()=>{const box=canvas.getBoundingClientRect();w=Math.max(1,box.width);h=Math.max(1,box.height);dpr=Math.min(1.5,devicePixelRatio||1);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);};
  const sizeObserver=new ResizeObserver(resize);sizeObserver.observe(canvas);resize();
  const ring=(radius:number,angle:number,alpha:number)=>{
   ctx.save();ctx.translate(w*.5,h*.62);ctx.rotate(angle);ctx.globalAlpha=alpha;ctx.strokeStyle="#9fd8ff";ctx.lineWidth=1;
   ctx.beginPath();ctx.arc(0,0,radius,0,Math.PI*2);ctx.stroke();
   for(let i=0;i<18;i++){const a=i*Math.PI/9;ctx.save();ctx.rotate(a);ctx.strokeRect(radius-4,-3,8,6);ctx.restore();}
   ctx.restore();
  };
  const draw=(time:number)=>{
   const t=reduced.matches?0:time;ctx.clearRect(0,0,w,h);
   const vignette=ctx.createRadialGradient(w/2,h/2,h*.2,w/2,h/2,Math.max(w,h)*.62);vignette.addColorStop(0,"rgba(0,0,0,0)");vignette.addColorStop(1,"rgba(0,0,0,.35)");ctx.fillStyle=vignette;ctx.fillRect(0,0,w,h);
   const step=Math.floor(t/.4);
   if(step!==noiseStep){noiseStep=step;const data=gc.createImageData(96,96);for(let i=0;i<data.data.length;i+=4){const n=(i*13+step*17)%255;data.data[i]=data.data[i+1]=data.data[i+2]=n;data.data[i+3]=12;}gc.putImageData(data,0,0);noisePattern=ctx.createPattern(grain,"repeat");}
   if(noisePattern){ctx.fillStyle=noisePattern;ctx.fillRect(0,0,w,h);}
   if(profile===8){ctx.fillStyle="rgba(255,237,190,.06)";ctx.fillRect(0,0,w,h);}
   if(profile===1||profile===5){
    ctx.save();ctx.globalAlpha=profile===1?.15+.15*(1+Math.sin(t*Math.PI/3))/2:.08;
    for(let i=0;i<3;i++){const x=w*(.18+i*.25),g=ctx.createLinearGradient(x,0,x+w*.14,h);g.addColorStop(0,profile===5?"#ffe9c4":"#cfe4ff");g.addColorStop(1,"transparent");ctx.fillStyle=g;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x+25,0);ctx.lineTo(x+w*.4,h);ctx.lineTo(x+w*.15,h);ctx.fill();}
    ctx.restore();
   }
   if(profile===2||profile===7||profile===6){
    const pulse=1+.04*Math.sin(t*Math.PI/(profile===7?3.5:4));
    ctx.globalAlpha=.18;ctx.drawImage(sprite,w*.65-80*pulse,h*.18-80*pulse,160*pulse,160*pulse);ctx.globalAlpha=1;
   }
   if(profile===3){const beat=reduced.matches?.25:Math.min(1,(t%6)/3)*(t%6<3?1:0);ring(Math.min(w,h)*.17,t*Math.PI/10,.5*beat);ring(Math.min(w,h)*.24,-t*Math.PI/17,.5*beat);}
   const n=Math.min(lite?Math.ceil(total/2):total,t<.8&&profile!==8?48:60);
   for(let i=0;i<n;i++){
    const p=particles[i];let x=p.x*w,y=p.y*h;
    ctx.globalAlpha=.25+.35*(.5+.5*Math.sin(t+p.phase));ctx.fillStyle=profile===8&&i<20?"#eef4ff":profile===8?"#ffedbe":profile===5?"#ffe9c4":profile===4&&i%2?"#ffb066":"#cfe4ff";
    if(profile===1){x=((x-t*(10+i%11))%w+w)%w;y+=Math.sin(t*.3+p.phase)*5;}
    else if(profile===7){const a=t*Math.PI*2/25+p.phase;x=w*.65+Math.cos(a)*w*(.09+p.x*.18);y=h*.3+Math.sin(a)*h*(.15+p.y*.3);}
    else if(profile===6&&i<18){const a=t*Math.PI/6+i*Math.PI/9;x=w*.65+Math.cos(a)*w*.11;y=h*.32+Math.sin(a)*h*.15;}
    else if(profile===8&&i<20){x+=Math.sin(t*.4+p.phase)*18;y=(y+t*(10+i%9))%h;}
    else {const speed=profile===4?40+i%41:profile===6?20+i%21:p.speed;y=((y-t*speed)%h+h)%h;x=(x+t*(profile===4?12:3))%w;}
    if(profile===8&&i>=20){ctx.globalAlpha=.2+.3*(.5+.5*Math.sin(t*.3+p.phase));ctx.drawImage(sprite,x-14,y-14,28,28);}
    else {ctx.save();ctx.translate(x,y);ctx.rotate(t*.2+p.phase);if(profile===8&&i<20){ctx.beginPath();ctx.ellipse(0,0,2,5,0,0,Math.PI*2);ctx.fill();}else if(profile===6||profile===7){ctx.fillRect(-2,-3,3,6);}else {ctx.beginPath();ctx.arc(0,0,p.r,0,Math.PI*2);ctx.fill();}ctx.restore();}
   }
   ctx.globalAlpha=1;
   const age=(performance.now()-pulse.current.at)/1000;
   if(age<1.2&&age>=0&&!reduced.matches){const glow=Math.max(0,1-age/1.2);if(pulse.current.type.includes("MAGIC")){ring(Math.min(w,h)*(.1+age*.1),age,.45*glow);}else if(/CLUE|MEMORY|CHAPTER_COMPLETE/.test(pulse.current.type)){ctx.globalAlpha=glow*.35;ctx.drawImage(sprite,w*.5-80-age*40,h*.5-80-age*40,160+age*80,160+age*80);ctx.globalAlpha=1;}}
   if(profile===1){ctx.globalAlpha=.15+.15*(1+Math.sin(t*Math.PI/2))/2;ctx.drawImage(sprite,w*.7-35,h*.45-35,70,70);ctx.globalAlpha=1;}
   if(profile===2)for(let i=0;i<8;i++){ctx.globalAlpha=Math.pow(Math.max(0,Math.sin(t*(1+i%3*.3)+i*1.7)),8);ctx.fillStyle="#eaf4ff";ctx.fillRect(w*(.1+i*.11),h*(.2+(i%3)*.17),2,2);}ctx.globalAlpha=1;
   if(profile===5)for(let i=0;i<3;i++){ctx.globalAlpha=.15+.08*Math.sin(t*(3+i)+i);ctx.drawImage(sprite,w*(.2+i*.28)-18,h*.7-18,36,36);}ctx.globalAlpha=1;
   // Effects remain canvas-local; never shake text, controls or the character DOM.
   if(profile===4&&!reduced.matches){const flash=Math.max(0,1-(t%5.7)/.15);ctx.fillStyle="rgba(207,228,255,"+(flash*.12)+")";ctx.fillRect(0,0,w,h);}
   // Entry fragmentation uses at most twelve of the existing particle budget.
   if(t<.8&&!reduced.matches&&profile!==8){ctx.fillStyle="#cfe4ff";ctx.globalAlpha=(1-t/.8)*.4;for(let i=0;i<Math.min(12,n);i++){const a=i*Math.PI/6;ctx.fillRect(w/2+Math.cos(a)*t*w*.3,h/2+Math.sin(a)*t*h*.3,2,3);}ctx.globalAlpha=1;}
  };
  const tick=(now:number)=>{
   frame=0;if(!active||!visible||document.hidden)return;
   if(now-last>=1000/30-1){const dt=last?Math.min(.1,(now-last)/1000):0;clock+=dt;last=now;draw(clock);count++;if(!measure)measure=now;if(now-measure>=2000){if(count*1000/(now-measure)<25)lite=true;measure=now;count=0;}}
   if(!reduced.matches)frame=requestAnimationFrame(tick);
  };
  const resume=()=>{cancelAnimationFrame(frame);frame=0;last=0;measure=0;count=0;if(active&&visible&&!document.hidden){if(reduced.matches)draw(0);else frame=requestAnimationFrame(tick);}};
  const observer=new IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting??false;resume();});observer.observe(canvas);
  document.addEventListener("visibilitychange",resume);reduced.addEventListener("change",resume);resume();
  return()=>{cancelAnimationFrame(frame);observer.disconnect();sizeObserver.disconnect();document.removeEventListener("visibilitychange",resume);reduced.removeEventListener("change",resume);};
 },[profile,active,transitionKey]);
 return <canvas ref={ref} className="memoryLocationEffects" aria-hidden="true" data-effect-profile={profile}/>;
}
