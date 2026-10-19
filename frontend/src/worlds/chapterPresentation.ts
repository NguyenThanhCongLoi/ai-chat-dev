import type {ChapterRun} from "./moonfallTypes";
/** Explicit pacing for the eight-chapter arc. Decorative generic clips are not a playlist. */
export function chapterCinematicAllowed(run:ChapterRun,event:{visual_event:string;chapter_id?:string}){
 const chapter=(run as ChapterRun&{chapter_id?:string}).chapter_id;
 if(!chapter)return true; // Legacy World has its own story.
 if(event.chapter_id&&event.chapter_id!==chapter)return false;
 switch(event.visual_event){
  case "SEAL_TRAP":return chapter==="selene_03";
  case "ARCHIVE_AWAKENS":return chapter==="selene_05";
  case "MIRROR_DESYNC":return chapter==="selene_06";
  case "PALE_MOON_MANIFESTATION":return chapter==="selene_07";
  case "ARROW_TRAP":return chapter==="selene_01";
  case "ECHO_GIRL":return chapter==="selene_02";
  case "ACADEMY_COLLAPSE":return chapter==="selene_04";
  case "WORLD_INTRO":return !run.intro_seen;
  case "MAGIC_SEAL_ACTIVATE":return ["selene_03","selene_07"].includes(chapter);
  case "VAULT_AWAKEN":case "MAJOR_REVEAL":return chapter==="selene_06";
  case "CHAPTER_COMPLETE":return chapter==="selene_08"&&(run as ChapterRun&{ending?:{id:string}|null}).ending?.id==="between_memory_and_moonlight";
  // The chapter memory video owns its transition; collecting a pendant must not
  // open another memory movie, nor append exit/rooftop clips to every chapter.
  default:return false;
 }
}
export function spokenBeat<T extends {type:string;auto_voice?:boolean}>(events:T[]){
 return events.filter(e=>e.auto_voice!==false&&e.type==="CHARACTER_SPEECH").slice(0,1);
}
