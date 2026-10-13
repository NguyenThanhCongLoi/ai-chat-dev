"""Freeze the public ver1 contract while implementations move between modules."""
import json
from pathlib import Path
from character_chat.main import app


def test_ver1_openapi_and_route_order_remain_compatible():
    expected = json.loads((Path(__file__).parent / "fixtures/ver1_api_contract.json").read_text(encoding="utf-8"))
    assert app.openapi() == expected["openapi"]
    routes = [
        {"path": route.path, "methods": sorted(route.methods), "name": route.name, "tags": route.tags}
        for route in app.routes
        if getattr(route, "methods", None)
    ]
    assert routes == expected["routes"]
