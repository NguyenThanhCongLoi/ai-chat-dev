"""Prepare home World intros with their original soundtrack (VP9 + Opus).
Usage: python scripts/prepare_world_hub_videos.py --source image/video
Original files are preserved. Playlist order is alphabetical (01_, 02_, ...).
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=ROOT/"image/video")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--overwrite",action="store_true")
    parser.add_argument("--high-quality",action="store_true",help="Less compressed native-resolution VP9; keep standard version as alternative")
    args=parser.parse_args()
    source=args.source.resolve()
    if not source.is_dir():parser.error("Intro folder not found: "+str(source))
    inputs=sorted((p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in {".mp4",".mov",".m4v"}),key=lambda p:p.as_posix().casefold())
    if not inputs:parser.error("No MP4/MOV intro videos found; manifest unchanged")
    binary=args.ffmpeg or shutil.which("ffmpeg")
    if not binary:
        sys.path.insert(0,str(ROOT/".tools/media-python"))
        try:
            import imageio_ffmpeg
            binary=imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:parser.error("Install FFmpeg or pass --ffmpeg")
    destination=ROOT/"image/worlds/hub/video"
    destination.mkdir(parents=True,exist_ok=True)
    manifest_path=ROOT/"character_chat/story_data/world_hub.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    assets=[a for a in manifest["assets"] if not a["id"].startswith("world_intro_")]
    intro=[];report=[]
    for item in inputs:
        ident="world_intro_"+hashlib.sha256(item.relative_to(source).as_posix().encode()).hexdigest()[:12]
        if args.high_quality:ident+="_hq"
        output=destination/(ident+".webm")
        if args.overwrite or not output.exists():
            pending=destination/(ident+".pending.webm")
            try:
                subprocess.run([binary,"-nostdin","-hide_banner","-loglevel","error","-y","-i",str(item),
                    "-map","0:v:0","-map","0:a:0?","-vf","scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=24" if args.high_quality else "scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2,fps=24",
                    "-c:v","libvpx-vp9",*(["-crf","22","-b:v","0"] if args.high_quality else ["-crf","36","-b:v","1000k","-maxrate","1400k","-bufsize","2800k"]),"-deadline","good","-cpu-used","4","-row-mt","1",
                    "-pix_fmt","yuv420p","-c:a","libopus","-b:a","96k",str(pending)],check=True)
                subprocess.run([binary,"-nostdin","-hide_banner","-loglevel","error","-i",str(pending),"-f","null","-"],check=True)
                pending.replace(output)
            finally:
                pending.unlink(missing_ok=True)
        assets.append(dict(id=ident,path=output.relative_to(ROOT/"image").as_posix()))
        intro.append(ident)
        report.append(dict(source=str(item),output=output.relative_to(ROOT).as_posix(),
                           bytes_before=item.stat().st_size,bytes_after=output.stat().st_size))
    if args.high_quality:
        standard=[a for a in manifest["assets"] if a["id"].startswith("world_intro_") and not a["id"].endswith("_hq")]
        assets.extend(standard)
        manifest["standard_intro"]=[i.removesuffix("_hq") for i in intro]
    manifest.update(intro=intro,assets=assets)
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report_path=ROOT/"artifacts/world-hub/video-conversion.json"
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
