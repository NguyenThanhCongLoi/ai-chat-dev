"""User-authorized deterministic matte extraction. Never redraw or overwrite source art."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from PIL import Image,ImageFilter,ImageDraw,ImageFont
from scipy import ndimage
ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/"image/worlds/selene/moonfall/props"
TEXTURES={"ch04_shattered_echo","ch07_fragment_boundaries","ch08_dividing_light_lines"}
def extract(source):
    im=Image.open(source).convert("RGBA")
    rgba=np.array(im)
    existing=rgba[...,3]
    if existing.min()<255:
        # Uploaded PNGs already have a matte. Preserve it exactly, including
        # antialiased edges; never replace it with an opaque chroma-key background.
        rgb=rgba[...,:3].astype(np.float32)
        transparent=existing==0
        if transparent.any():
            key=np.median(rgb[transparent],axis=0)
            a=existing.astype(np.float32)/255
            edge=(existing>0)&(existing<255)
            if key[0]>180 and key[2]>180 and key[1]<80:
                spill=edge&(rgb[...,0]-rgb[...,1]>50)&(rgb[...,2]-rgb[...,1]>50)
            elif key[1]>key[0]+60 and key[1]>key[2]+50:
                spill=edge&(rgb[...,1]-np.maximum(rgb[...,0],rgb[...,2])>35)
            else:spill=np.zeros(edge.shape,dtype=bool)
            rgb[spill]=np.clip((rgb[spill]-(1-a[spill,None])*key)/np.maximum(a[spill,None],.01),0,255)
        rgb[transparent]=0
        rgba[...,:3]=rgb.astype(np.uint8)
        return Image.fromarray(rgba)
    rgb=rgba[...,:3].astype(np.float32)
    low=rgb.min(axis=2);high=rgb.max(axis=2);chroma=high-low
    if source.stem in TEXTURES:
        # These are full-frame memory textures, intentionally composited with
        # screen blend and a soft radial mask by the frontend.
        return im
    if source.stem=="ch08_preserved_memories":
        alpha=np.clip((high-12)/48,0,1)*255
    elif source.stem=="ch04_corridor_guiding_lights":
        # The supplied checkerboard is painted into RGB; neutral squares are
        # background, blue/silver particles are retained as a light overlay.
        alpha=np.clip(chroma/38,0,1)*np.clip((255-low)/50,0,1)*255
    else:
        candidate=(low>228)&(chroma<22)
        edge=np.zeros(candidate.shape,dtype=bool)
        edge[0,:]=candidate[0,:];edge[-1,:]=candidate[-1,:]
        edge[:,0]=candidate[:,0];edge[:,-1]=candidate[:,-1]
        background=ndimage.binary_propagation(edge,mask=candidate)
        # Feather only the one-pixel foreground edge. Interior pale material stays opaque.
        alpha=np.where(background,0,255).astype(np.uint8)
        band=ndimage.binary_dilation(background,iterations=1)&~background
        alpha[band]=np.minimum(alpha[band],np.clip((255-low[band])*8,0,255)).astype(np.uint8)
    im.putalpha(Image.fromarray(alpha.astype(np.uint8)))
    return im
def main():
    output=MEDIA/"prepared";output.mkdir(exist_ok=True)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only",nargs="+",help="Source filenames to update; all other prepared assets are preserved")
    parser.add_argument("--trim",action="store_true",help="Trim transparent outer padding in prepared outputs only")
    parser.add_argument("--method",type=int,choices=range(7),default=6,help="WebP encoder effort, not image quality")
    args=parser.parse_args()
    report=ROOT/"artifacts/memory-adventure/props-preparation.json"
    rows=json.loads(report.read_text(encoding="utf-8")) if args.only and report.exists() else []
    sources=sorted(p for p in MEDIA.iterdir() if p.is_file() and p.suffix.lower() in {".webp",".png",".jpg",".jpeg"})
    if args.only:
        sources=[p for p in sources if p.name in args.only]
        if len(sources)!=len(args.only):raise ValueError("Some requested sources are missing")
    rows=[r for r in rows if r["source"] not in {p.name for p in sources}]
    for source in sources:
        image=extract(source)
        if args.trim and image.mode=="RGBA":
            box=image.getchannel("A").getbbox()
            if box:image=image.crop(box)
        target=output/(source.stem+".webp")
        image.save(target,"WEBP",quality=94,method=args.method,exact=True)
        print("Prepared",source.name,"->",image.size,flush=True)
        rows.append(dict(source=source.name,output="prepared/"+target.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),mode="screen_texture" if source.stem in TEXTURES else "alpha_cutout"))
    report=ROOT/"artifacts/memory-adventure/props-preparation.json"
    report.write_text(json.dumps(rows,indent=2),encoding="utf-8")
    cols=4;w=320;h=224
    sheet=Image.new("RGB",(cols*w,((len(rows)+cols-1)//cols)*h),"#243346")
    draw=ImageDraw.Draw(sheet);font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",13)
    for i,row in enumerate(rows):
        im=Image.open(MEDIA/row["output"]).convert("RGBA");im.thumbnail((300,180))
        x=i%cols*w+(w-im.width)//2;y=i//cols*h+5
        sheet.paste(im,(x,y),im);draw.text((i%cols*w+5,i//cols*h+192),row["source"],fill="white",font=font)
    sheet.save(report.with_name("prepared-props-contact.jpg"),quality=92)
    print("Prepared",len(rows),"props; original files preserved.")
if __name__=="__main__":main()
