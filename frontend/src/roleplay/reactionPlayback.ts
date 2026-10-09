/** A short reaction must finish (or be cancelled) before dialogue playback. */
export function playReactionClip(player:HTMLAudioElement, maxMs=3000) {
  let done!:()=>void;
  let timer:ReturnType<typeof setTimeout>|undefined;
  const finished=new Promise<void>(resolve=>{
    let settled=false;
    done=()=>{
      if(settled)return;
      settled=true;
      clearTimeout(timer);
      player.onended=player.onerror=null;
      player.pause();
      resolve();
    };
    player.onended=player.onerror=done;
    timer=setTimeout(done,maxMs);
    try { void player.play().catch(done); } catch { done(); }
  });
  return {finished,cancel:done};
}
