"""Deletion boundaries and current resource availability are required cleanup gates."""
import runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def test_cleanup_rejects_protected_and_outside_paths():
    checked=runpy.run_path(str(ROOT/"scripts/clean_superseded_assets.py"))["checked"]
    for path in (ROOT,ROOT.parent/"outside",ROOT/"data/character_chat.sqlite",
                 ROOT/".git/config",ROOT/"backups/archive.zip",ROOT/".tools/bin",ROOT/".env",ROOT/"secrets.vault.json"):
        with pytest.raises(ValueError):
            checked(path)
    assert checked(ROOT/"image/worlds/selene/moonfall/unused.webm").is_relative_to(ROOT)

def test_cleanup_never_selects_current_assets():
    active,choices=runpy.run_path(str(ROOT/"scripts/clean_superseded_assets.py"))["plan"]()
    assert active
    assert not active.intersection(choices)
    assert all(".env" not in p.parts and p.suffix not in (".sqlite",".db") for p in choices)
    assert (ROOT/"image/worlds/hub/video/selene_intro_20261018_from17.webm") in active

def test_current_audit_has_no_missing_visuals():
    result=runpy.run_path(str(ROOT/"scripts/audit_selene_media.py"))["audit"]()
    assert result["visuals_ready"],result["missing_visuals"]
