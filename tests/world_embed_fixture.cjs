// Isolated browser host reproduces the platform keeping World mounted but hidden.
const esbuild=require("../frontend/node_modules/esbuild");
esbuild.buildSync({
 stdin:{contents:`
 import React,{useState} from "react";
 import {createRoot} from "react-dom/client";
 import WorldApp from "./src/worlds/WorldApp";
 function Host(){
  const [active,setActive]=useState(true),[clicked,setClicked]=useState(false);
  return <><section hidden={!active}><WorldApp characterId="selene" active={active} onChat={()=>setActive(false)}/></section>
   {!active&&<button id="host-chat" onClick={()=>setClicked(true)}>{clicked?"Chat responds":"Returned to chat"}</button>}</>;
 }
 createRoot(document.getElementById("root")).render(<Host/>);
 `,resolveDir:require("node:path").resolve("frontend"),loader:"tsx"},
 bundle:true,format:"iife",jsx:"automatic",define:{"import.meta.env":"{}"},outfile:process.argv[2],logLevel:"error"
});
