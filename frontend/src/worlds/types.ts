import {readWorldJson} from "./worldHttp";
export type Actor={id:string;name:string;description?:string;origin:string};
export {WorldError} from "./worldHttp";
import {WorldError} from "./worldHttp";
export async function api<T>(path:string,method="GET",body?:unknown):Promise<T>{
 const token=localStorage.getItem("auth_token");
 for(let attempt=0;;attempt++){
  try{
   const response=await fetch(path,{method,cache:"no-store",headers:{...(token?{Authorization:"Bearer "+token}:{}),...(body?{"Content-Type":"application/json"}:{})},body:body?JSON.stringify(body):undefined});
   return await readWorldJson<T>(response);
  }catch(error){
   if(method!=="GET"||attempt>=1||!(error instanceof WorldError)||![502,503,504].includes(error.status))throw error;
   await new Promise(resolve=>setTimeout(resolve,600));
  }
 }
}
