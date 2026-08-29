"""GET /version contract tests (gos-as-a-service#39).

Realm and marketplace backends serve build provenance at /version over the
IC HTTP interface (http_request + http_request_update). Values are stamped
at build/release time; unstamped placeholders (local/dev builds) are omitted
honestly.
"""

import importlib.util
import json
import os

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load(name: str, relpath: str):
    path = os.path.join(_REPO_ROOT, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


realm_version_http = _load(
    "realm_version_http", "src/realm_backend/api/version_http.py"
)
marketplace_version_http = _load(
    "marketplace_version_http", "src/marketplace_backend/api/version_http.py"
)

_REQ = {"method": "GET", "url": "/version", "headers": [], "body": b""}


def _headers_dict(resp):
    return {k: v for k, v in resp["headers"]}


def _assert_contract(resp, canister_name):
    assert resp["status_code"] == 200
    headers = _headers_dict(resp)
    assert headers["Content-Type"] == "application/json"
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert headers["Cache-Control"] == "no-cache, must-revalidate"
    payload = json.loads(resp["body"].decode("utf-8"))
    assert payload["canister"] == canister_name
    return payload


def _assert_unstamped_omits(payload):
    assert "sha" not in payload
    assert "built_at" not in payload
    assert "version" not in payload


# ── realm_backend ──────────────────────────────────────────────────────────


def test_realm_version_ok_unstamped():
    resp = realm_version_http.version_http_response(dict(_REQ))
    payload = _assert_contract(resp, "realm_backend")
    _assert_unstamped_omits(payload)


def test_realm_version_strips_query_string():
    resp = realm_version_http.version_http_response({**_REQ, "url": "/version?foo=bar"})
    assert resp["status_code"] == 200


def test_realm_version_404_other_paths():
    resp = realm_version_http.version_http_response({**_REQ, "url": "/status"})
    assert resp["status_code"] == 404
    body = json.loads(resp["body"].decode("utf-8"))
    assert body == {"error": "not found"}
    assert _headers_dict(resp)["Content-Type"] == "application/json"


def test_realm_version_options_preflight():
    resp = realm_version_http.version_http_response({**_REQ, "method": "OPTIONS"})
    assert resp["status_code"] == 204


def test_realm_version_stamped_fields(monkeypatch):
    monkeypatch.setattr(realm_version_http, "_SHA_STAMP", "a1b2c3d")
    monkeypatch.setattr(realm_version_http, "_BUILT_AT_STAMP", "2026-08-29T13:04:05Z")
    monkeypatch.setattr(realm_version_http, "_VERSION_STAMP", "v0.4.0")
    payload = realm_version_http.get_version_payload()
    assert payload == {
        "canister": "realm_backend",
        "sha": "a1b2c3d",
        "built_at": "2026-08-29T13:04:05Z",
        "version": "v0.4.0",
    }


def test_realm_http_request_upgrade_signal():
    resp = realm_version_http.http_request_upgrade_signal()
    assert resp["upgrade"] is True
    assert resp["body"] == b""


def test_realm_is_version_path():
    assert realm_version_http.is_version_path("/version")
    assert realm_version_http.is_version_path("/version?x=1")
    assert realm_version_http.is_version_path("version")
    assert not realm_version_http.is_version_path("/status")
    assert not realm_version_http.is_version_path("/version/extra")


# ── marketplace_backend ────────────────────────────────────────────────────


def test_marketplace_version_ok_unstamped():
    resp = marketplace_version_http.version_http_response(dict(_REQ))
    payload = _assert_contract(resp, "marketplace_backend")
    _assert_unstamped_omits(payload)


def test_marketplace_version_404_other_paths():
    resp = marketplace_version_http.version_http_response({**_REQ, "url": "/"})
    assert resp["status_code"] == 404
    assert json.loads(resp["body"].decode("utf-8")) == {"error": "not found"}


def test_marketplace_version_options_preflight():
    resp = marketplace_version_http.version_http_response({**_REQ, "method": "OPTIONS"})
    assert resp["status_code"] == 204


def test_marketplace_version_stamped_fields(monkeypatch):
    monkeypatch.setattr(marketplace_version_http, "_SHA_STAMP", "a1b2c3d")
    monkeypatch.setattr(marketplace_version_http, "_BUILT_AT_STAMP", "2026-08-29T13:04:05Z")
    payload = marketplace_version_http.get_version_payload()
    assert payload["sha"] == "a1b2c3d"
    assert payload["built_at"] == "2026-08-29T13:04:05Z"
    assert "version" not in payload  # VERSION_STAMP left unstamped
