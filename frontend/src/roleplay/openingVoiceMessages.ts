import type {Message} from "./types";

/** Opening greetings only: never autoplay later replies from stored history. */
export function openingVoiceMessages(messages:Message[]):Message[] {
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
