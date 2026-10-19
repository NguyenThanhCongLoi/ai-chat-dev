/** Keep the decoded image and its exact render source alive for the chapter. */
type PreparedImage={promise:Promise<void>;source:string;image:HTMLImageElement};
const cache=new Map<string,PreparedImage>();
export function preparedImageSource(url:string){return cache.get(url)?.source||url;}
export function prepareChapterImage(url:string){
 const cached=cache.get(url);if(cached)return cached.promise;
 const image=new Image();image.decoding="async";
 const entry:PreparedImage={image,source:"",promise:Promise.resolve()};
 entry.promise=(async()=>{
  const response=await fetch(url,{signal:AbortSignal.timeout(30000)});
  if(!response.ok)throw Error("Image unavailable");
  const blob=await response.blob();entry.source=URL.createObjectURL(blob);
  await new Promise<void>((resolve,reject)=>{
   image.onload=()=>resolve();image.onerror=()=>reject(Error("Image unavailable"));image.src=entry.source;
  });
  await image.decode();
 })().catch(error=>{if(entry.source)URL.revokeObjectURL(entry.source);cache.delete(url);throw error;});
 cache.set(url,entry);
 while(cache.size>120){const key=cache.keys().next().value!;const old=cache.get(key)!;cache.delete(key);void old.promise.then(()=>URL.revokeObjectURL(old.source)).catch(()=>{});}
 return entry.promise;
}
