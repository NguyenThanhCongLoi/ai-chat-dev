"""Freeze the public ver1 contract while implementations move between modules."""
import json
from pathlib import Path
from character_chat.main import app


def test_ver1_openapi_and_route_order_remain_compatible():
    expected = json.loads((Path(__file__).parent / "fixtures/ver1_api_contract.json").read_text(encoding="utf-8"))
    # Update adds Tarot session endpoints; every original ver1 route remains unchanged.
    additions = {"/v1/assistant/profiles", "/v1/assistant/chats/{room_id}/tarot", "/v1/assistant/chats/{room_id}/tarot/reset"}
    additions.update(route.path for route in app.routes if getattr(route, "path", "").startswith(("/v1/admin/character-submissions", "/v1/admin/roleplay-lorebook", "/roleplay/lorebook/admin", "/v1/admin/ai-world", "/v1/ai-world", "/v1/worlds", "/v1/admin/worlds", "/worlds", "/v1/roleplay/rooms/", "/v1/roleplay/character-connections/", "/v1/moonfall", "/v1/admin/moonfall")))
    additions.update({"/v1/roleplay/characters/{character_id}/connections", "/v1/roleplay/characters/{character_id}/connection-suggestion"})
    actual = app.openapi()
    assert {path for path in additions if path.startswith("/v1/")}.issubset(actual["paths"])
    assert {**actual, "paths": {path: value for path, value in actual["paths"].items() if path not in additions}} == expected["openapi"]
    routes = [
        {"path": route.path, "methods": sorted(route.methods), "name": route.name, "tags": route.tags}
        for route in app.routes
        if getattr(route, "methods", None) and route.path not in additions
    ]
    assert routes == expected["routes"]
