export type ActionSound={id:string;title:string;url:string;triggers:string[];enabled:boolean;volume:number};
export function normalizeAction(text:string){
  return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/đ/g,"d").replace(/\s+/g," ").trim();
}
export function actionSpans(text:string){
  const spans:{start:number;text:string}[]=[];
  let start=-1;
  for(let i=0;i<text.length;i++){
    if(text[i]!=="*"||text[i-1]==="\\")continue;
    while(text[i+1]==="*")i++;
    if(start<0)start=i+1;
    else{spans.push({start,text:text.slice(start,i).replace(/\*+$/,"")});start=-1;}
  }
  if(start>=0)spans.push({start,text:text.slice(start)});
  return spans;
}
export class ActionSoundDetector{
  private text="";private seen=new Set<string>();private count=0;
  get done(){return this.count>=1;}
  commit(){this.count=1;}
  replaceText(text:string){if(this.count===0)this.text=text.slice(0,32768);}
  feed(delta:string,sounds:ActionSound[],consume=true){
    if(this.count>=1)return [];
    this.text=(this.text+delta).slice(0,32768);
    const result:ActionSound[][]=[];
    for(const span of actionSpans(this.text)){
      // A local clause avoids combining distant, unrelated objects/actions.
      for(const clause of span.text.split(/[.;。!?\n]/)){
        const normalized=normalizeAction(clause);
        const groups=new Map<string,ActionSound[]>();
        for(const sound of sounds){
          for(const rule of sound.triggers){
            const tokens=rule.split("+").map(normalizeAction).filter(Boolean);
            if(!tokens.length||!tokens.every(token=>normalized.includes(token)))continue;
            const beginning=Math.min(...tokens.map(token=>normalized.indexOf(token)));
            if(/\b(khong|chua|dung|not|never|without)\b/.test(normalized.slice(Math.max(0,beginning-45),beginning)))continue;
            const key=span.start+":"+tokens.slice().sort().join("+");
            if(this.seen.has(key))continue;
            const group=groups.get(key)||[];
            if(!group.some(item=>item.id===sound.id))group.push(sound);
            groups.set(key,group);
          }
        }
        for(const [key,options] of groups){
          if(this.count>=1)return result;
          result.push(options);
          if(consume){this.seen.add(key);this.count++;}
          else return result;
        }
      }
    }
    return result;
  }
}
