"""Smoke a running service without sending paid LLM requests."""
import argparse
import base64
import json
import os
import urllib.error
import urllib.request


def request(base, path, auth=False):
    headers = {}
    if auth:
        token = base64.b64encode((os.environ["DOCS_USERNAME"] + ":" + os.environ["DOCS_PASSWORD"]).encode()).decode()
        headers["Authorization"] = "Basic " + token
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin", action="store_true", help="Validate CMS with DOCS_USERNAME/PASSWORD from environment")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    status, body = request(base, "/health")
    assert status == 200 and json.loads(body)["status"] == "ok", "Backend health failed"
    for path in ("/",):
        status, body = request(base, path)
        assert status == 200 and b"<html" in body.lower(), "Missing UI: " + path
    assert request(base, "/admin")[0] == 401, "Anonymous CMS UI access must be blocked"
    assert request(base, "/v1/rooms")[0] == 401, "Anonymous room access must be blocked"
    assert request(base, "/v1/admin/settings")[0] == 401, "Anonymous CMS access must be blocked"
    if args.admin:
        status, body = request(base, "/admin", True)
        assert status == 200 and b"<html" in body.lower(), "CMS UI authentication failed"
        status, body = request(base, "/v1/admin/settings", True)
        assert status == 200 and isinstance(json.loads(body), dict), "CMS authentication failed"
    print("PASS: health, UI, CMS UI, authentication" + (", CMS API" if args.admin else ""))


if __name__ == "__main__":
    main()
