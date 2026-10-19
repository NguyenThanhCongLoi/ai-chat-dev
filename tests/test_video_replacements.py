from pathlib import Path
from character_chat.adventure.asset_variants import video_version,VIDEO_DURATIONS
from character_chat.adventure.loader import seed
from character_chat.adventure.props import manifest_assets
def test_replacement_clips_are_present_in_manifest_with_current_durations():
    assets=manifest_assets(seed())
    root=Path("image/worlds/selene/moonfall")
    paths={a["path"]:a for a in assets.values()}
    for path,seconds in VIDEO_DURATIONS.items():
        assert (root/path).is_file(),path
        assert paths[path]["duration"]==seconds
        assert video_version(root,path)!="missing"

def test_replacing_video_at_same_path_changes_cache_key(tmp_path):
    path="clip.webm"
    (tmp_path/path).write_bytes(b"first clip")
    a=video_version(tmp_path,path)
    (tmp_path/path).write_bytes(b"replacement clip with new frames")
    b=video_version(tmp_path,path)
    assert a!=b
    assert video_version(tmp_path,"../outside.webm")=="missing"
