"""Portable SQLite + DATA_DIR backup. Stop writers before backup/restore."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import tempfile
import zipfile


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def database_info(path):
    with closing(sqlite3.connect(str(path))) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {name: db.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0] for name in sorted(tables)}


def backup(source, output, music=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    database = source / "character_chat.sqlite"
    if not database.is_file():
        raise ValueError("Missing character_chat.sqlite in DATA_DIR")
    if output.is_relative_to(source):
        raise ValueError("Backup output must be outside DATA_DIR")
    if output.exists():
        raise ValueError("Backup already exists; choose a new filename")
    music = Path(music).resolve() if music else None
    if music and not music.is_dir():
        raise ValueError("Music directory does not exist")
    entries = []
    for base, prefix in [(source, "data")] + ([(music, "music")] if music else []):
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlinks are not supported: " + str(path))
            if path.is_file() and path.name not in {"character_chat.sqlite", "character_chat.sqlite-wal", "character_chat.sqlite-shm", "character_chat.sqlite-journal"}:
                entries.append((path, prefix + "/" + path.relative_to(base).as_posix()))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="companion-backup-", dir=output.parent) as temp:
        snapshot = Path(temp) / "character_chat.sqlite"
        with closing(sqlite3.connect(str(database))) as src, closing(sqlite3.connect(str(snapshot))) as dst:
            src.backup(dst)
        entries.append((snapshot, "data/character_chat.sqlite"))
        manifest = {"format": 1, "tables": database_info(snapshot), "files": {}}
        # Exclusive creation prevents silently overwriting another backup.
        try:
            with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                for path, name in entries:
                    before = digest(path)
                    archive.write(path, name)
                    if digest(path) != before:
                        raise ValueError("File changed during backup; stop writers and retry")
                    manifest["files"][name] = before
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            verify(output)
        except Exception:
            output.unlink(missing_ok=True)
            raise
    print("Backup verified:", output, "(private: contains user data and encrypted credentials)")


def verify(archive_path, destination=None):
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive entries")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != 1 or set(names) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("Invalid backup manifest")
        for name, expected in manifest["files"].items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or path.parts[0] not in {"data", "music"}:
                raise ValueError("Unsafe archive path")
            mode = archive.getinfo(name).external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("Symlink in backup")
            h = hashlib.sha256()
            with archive.open(name) as stream:
                target = Path(destination).joinpath(*path.parts) if destination else None
                if target:
                    target.parent.mkdir(parents=True, exist_ok=True)
                sink = target.open("wb") if target else None
                try:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk)
                        if sink:
                            sink.write(chunk)
                finally:
                    if sink:
                        sink.close()
            if h.hexdigest() != expected:
                raise ValueError("Checksum mismatch: " + name)
        if "data/character_chat.sqlite" not in manifest["files"]:
            raise ValueError("Missing database")
    return manifest


def restore(archive, target):
    target = Path(target).resolve()
    if target.exists():
        raise ValueError("Restore target must not exist; never overwrite live data")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="companion-restore-", dir=target.parent) as temp:
        manifest = verify(archive, temp)
        if database_info(Path(temp) / "data/character_chat.sqlite") != manifest["tables"]:
            raise ValueError("Restored table counts differ")
        Path(temp).rename(target)
    print("Restored:", target, "(data/ contains DATA_DIR; music/ contains optional music)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("backup")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--music-dir")
    p = sub.add_parser("verify")
    p.add_argument("archive")
    p = sub.add_parser("restore")
    p.add_argument("archive")
    p.add_argument("--target", required=True)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            backup(args.data_dir, args.output, args.music_dir)
        elif args.command == "restore":
            restore(args.archive, args.target)
        else:
            manifest = verify(args.archive)
            print("Checksums verified; tables:", manifest["tables"])
    except (ValueError, OSError, sqlite3.Error, zipfile.BadZipFile, KeyError) as exc:
        parser.exit(1, "Backup/restore error: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
