import React from "react";
import {createRoot} from "react-dom/client";
import {useActionSounds,activateActionSounds} from "../src/roleplay/useActionSounds";
import {useReactionSounds} from "../src/roleplay/useReactionSounds";
function App(){
 const reactions=useReactionSounds("room","user",["character"]);
 const actions=useActionSounds("room","user",reactions.enabled);
 Object.assign(window,{parallelState:{actionReady:actions.ready,reactionReady:reactions.ready,available:actions.available},parallelReady:actions.ready&&reactions.ready,parallelReaction:reactions.react,parallelAction:actions.feed});
 return <button id="activate" onClick={activateActionSounds}>Activate</button>;
}
createRoot(document.getElementById("root")!).render(<App/>);
