import type {Message} from "./types";

/** Normal entry uses greetings; returning from World resumes only the latest character reply. */
export function openingVoiceMessages(messages:Message[], fromWorld=false):Message[] {
  if(fromWorld){
    const latest=[...messages].reverse().find(m=>m.sender_type==="character"&&m.character_id&&m.text.trim());
    return latest?[latest]:[];
  }
  const seen=new Set<string>();
  const result:Message[]=[];
  for(const message of messages){
    if(message.sender_type==="user")break;
    if(message.sender_type!=="character"||!message.character_id||seen.has(message.character_id))continue;
    seen.add(message.character_id);
    result.push(message);
  }
  return result;
}
