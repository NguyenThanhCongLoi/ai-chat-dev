import copy from "./worldUiCopy.json";
import {hubText} from "./worldHubCopy";
const values=copy as Record<string,Record<string,string>>;
export function worldUi(vi:string,en:string,language:string){return language==="vi"?vi:values[vi]?.[language]||hubText(vi,en,language);}
