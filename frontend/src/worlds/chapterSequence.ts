import type {ChapterRun,WorldEvent} from "./moonfallTypes";
import {chapterCinematicAllowed,spokenBeat} from "./chapterPresentation";

/** The event order is the authored timeline: speech, movie barrier, reaction. */
export function isStoryMovie(run:ChapterRun,event:WorldEvent){
 const asset=run.assets[run.visual_events[event.visual_event]?.cinematic||""];
 return event.visual_event!=="WORLD_INTRO"&&chapterCinematicAllowed(run,event)&&asset?.type==="VIDEO";
}
export function chapterSequence(run:ChapterRun,events:WorldEvent[],automatic=true){
 const movieBeats=new Set(events.filter(e=>isStoryMovie(run,e)).map(e=>e.beat_id));
 const ordinary=spokenBeat(events.filter(e=>!movieBeats.has(e.beat_id)&&e.type==="CHARACTER_SPEECH"&&e.auto_voice!==false));
 return events.filter(e=>isStoryMovie(run,e)||movieBeats.has(e.beat_id)&&e.presentation!=="archive"&&["NARRATION","CHARACTER_SPEECH"].includes(e.type)||automatic&&ordinary.includes(e));
}
export function concealedSequenceEvents(run:ChapterRun,revealed:Set<string>){
 const beats=new Set(run.events.filter(e=>isStoryMovie(run,e)).map(e=>e.beat_id));
 return run.events.filter(e=>beats.has(e.beat_id)&&!revealed.has(e.id)).map(e=>e.id);
}
