import React,{useState} from "react";
import {createRoot} from "react-dom/client";
import {useActionSounds,prepareActionSounds,activateActionSounds} from "../src/roleplay/useActionSounds";
import {renderActionSounds} from "../src/admin/actionSounds";
function App(){
 const [room,setRoom]=useState<string|null>("room");
 const [enabled,setEnabled]=useState(true);
 const sfx=useActionSounds(room,"user",enabled);
 Object.assign(window,{sfxFeed:sfx.feed,sfxFinish:sfx.finish});
 return <><button id="mute" onClick={()=>setEnabled(value=>!value)}>Mute</button><button id="activate" onClick={()=>{activateActionSounds();void prepareActionSounds("user");}}>Activate</button><button id="exit" onClick={()=>setRoom(null)}>Exit</button><button id="cms" onClick={()=>void renderActionSounds()}>CMS</button><section id="action-sounds"/></>;
}
createRoot(document.getElementById("root")!).render(<App/>);
