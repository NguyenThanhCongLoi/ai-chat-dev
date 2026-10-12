"""Export the frozen ver1 Git revision, independent of the current branch."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="v1.0.0", help="Release tag; default: v1.0.0")
    parser.add_argument("--include-local-music", action="store_true", help="Private deployment ZIP only")
    args = parser.parse_args()
    commit = git("rev-parse", "--verify", args.ref + "^{commit}")
    names = git("ls-tree", "-r", "--name-only", commit).splitlines()
    forbidden = {"ElfCompanion.tsx", "companionState.ts", "elf-companion.css", "elf_normal.webm", "elf_talk.webm"}
    for name in names:
        path = Path(name)
        if path.name in forbidden:
            parser.error("This revision contains companion video: " + name)
        if path.name in {".env", "secrets.vault.json"} or path.suffix in {".db", ".sqlite", ".sqlite3"}:
            parser.error("Sensitive/runtime file tracked: " + name)
    music_dir = ROOT / "music_backgr" / "mp3"
    music = sorted(p for p in music_dir.rglob("*") if p.is_file()) if args.include_local_music else []
    if args.include_local_music and not music:
        parser.error("No local music found in music_backgr/mp3; no ZIP created.")
    out_dir = ROOT / "backups" / "releases"
    out_dir.mkdir(parents=True, exist_ok=True)
    kind = "private" if args.include_local_music else "source"
    out = out_dir / ("ai-companion-ver1-" + kind + "-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".zip")
    subprocess.run(["git", "archive", "--format=zip", "--output", str(out), commit], cwd=ROOT, check=True)
    with zipfile.ZipFile(out, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in music:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr("RELEASE_INFO.json", json.dumps({"ref": args.ref, "commit": commit, "companion_video": False, "private_music": args.include_local_music}, indent=2))
    print("Revision:", commit)
    print("ZIP:", out)
    print("Secrets and server database must be backed up separately.")


if __name__ == "__main__":
    main()
