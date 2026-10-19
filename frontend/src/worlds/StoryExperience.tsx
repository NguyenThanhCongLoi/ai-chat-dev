import {useEffect,useState} from "react";
import {api} from "./types";
import MoonfallApp from "./MoonfallApp";
import AdventureApp from "./AdventureApp";
import type {WorldProps} from "./moonfallTypes";
export default function StoryExperience(props:WorldProps){
 const [version,setVersion]=useState<number>(),[error,setError]=useState("");
 useEffect(()=>{let live=true;void api<{engine_version?:number}>("/v1/moonfall").then(c=>{if(live)setVersion(c.engine_version||1);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[props.characterId]);
 return version===2?<AdventureApp {...props}/>:version===1?<MoonfallApp {...props}/>:<div className="maLoading" role="status">{error||"Moonfall…"}</div>;
}
