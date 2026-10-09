from fastapi import FastAPI
from fastapi.testclient import TestClient
from character_chat.background_music import build_background_music_router, music_catalog


def test_catalog_excludes_documents_and_audio_serves_ranges(tmp_path,monkeypatch):
    audio=tmp_path/"Ambient 1.mp3";audio.write_bytes(b"0123456789")
    (tmp_path/"License.pdf").write_bytes(b"private")
    (tmp_path/"config.env").write_text("secret")
    monkeypatch.setenv("ROLEPLAY_MUSIC_DIR",str(tmp_path))
    app=FastAPI();app.include_router(build_background_music_router(lambda:"user"))
    with TestClient(app) as client:
        tracks=client.get("/v1/roleplay/background-music").json()["tracks"]
        assert len(tracks)==1
        assert tracks[0]["title"]=="Ambient 1"
        response=client.get(tracks[0]["url"],headers={"Range":"bytes=2-5"})
        assert response.status_code==206
        assert response.content==b"2345"
        assert response.headers["content-type"]=="audio/mpeg"
        assert client.get("/v1/roleplay/background-music/License.pdf").status_code==404
        assert client.get("/v1/roleplay/background-music/unknown").status_code==404


def test_missing_music_directory_is_empty(tmp_path):
    assert music_catalog(tmp_path/"missing")=={}


def test_bundled_mp3_catalog_has_all_28_tracks():
    tracks=music_catalog()
    assert len(tracks)==28
    assert all(path.suffix==".mp3" for path in tracks.values())
