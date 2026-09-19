"""`realms marketplace publish`: manifests → listings → create + approve calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from realms.cli.commands import marketplace_publish as mp


def _tree(tmp_path: Path) -> Path:
    ext = tmp_path / "extensions" / "extensions"
    (ext / "llm_chat").mkdir(parents=True)
    (ext / "llm_chat" / "manifest.json").write_text(json.dumps({
        "name": "llm_chat", "version": "1.0.22", "description": "Ask \"things\"",
        "sidebar_label": {"en": "AI Assistant", "es": "Asistente"}, "categories": ["oversight"], "icon": "brain",
        "doc_url": "https://example.org/doc",
    }))
    (ext / "_shared").mkdir()
    (ext / "_shared" / "manifest.json").write_text("{}")
    (ext / "no_manifest").mkdir()
    cdx = tmp_path / "codices" / "codices"
    (cdx / "agora").mkdir(parents=True)
    (cdx / "agora" / "manifest.json").write_text(json.dumps({
        "id": "agora", "version": "0.9.6", "name": "Agora", "description": "Migration codex", "kind": "codex",
        "realm_type": "municipality", "categories": ["governance"],
    }))
    return tmp_path


class TestDiscovery:
    def test_walks_like_files_publish(self, tmp_path):
        listings = mp.discover(_tree(tmp_path))
        assert [(l.kind, l.item_id) for l in listings] == [("codex", "agora"), ("extension", "llm_chat")]

    def test_filters(self, tmp_path):
        root = _tree(tmp_path)
        assert [l.item_id for l in mp.discover(root, extensions_only=True)] == ["llm_chat"]
        assert [l.item_id for l in mp.discover(root, codices={"nope"})] == ["llm_chat"]

    def test_extension_fields_and_namespace(self, tmp_path):
        ext = [l for l in mp.discover(_tree(tmp_path)) if l.kind == "extension"][0]
        assert ext.fields["name"] == "AI Assistant"
        assert ext.fields["categories"] == "oversight"
        assert ext.fields["download_url"] == "https://example.org/doc"
        assert mp.namespace_for(ext) == "ext/llm_chat/1.0.22"

    def test_codex_fields_and_namespace(self, tmp_path):
        cdx = [l for l in mp.discover(_tree(tmp_path)) if l.kind == "codex"][0]
        assert cdx.fields["realm_type"] == "municipality"
        assert cdx.fields["name"] == "Agora"
        assert mp.namespace_for(cdx) == "codex/agora/0.9.6"

    def test_missing_version_is_refused(self):
        with pytest.raises(ValueError, match="no version"):
            mp.extension_listing({"name": "x"}, "x")


class TestCandid:
    def test_text_escaping(self):
        assert mp.candid_text('a "b" \\ c') == '"a \\"b\\" \\\\ c"'

    def test_record_types(self):
        rec = mp.candid_record({"s": "x", "n": 0, "b": True})
        assert rec == '(record { s = "x"; n = 0 : nat64; b = true })'

    def test_listing_input_carries_registry(self, tmp_path):
        ext = [l for l in mp.discover(_tree(tmp_path)) if l.kind == "extension"][0]
        rec = mp.listing_input(ext, "reg-id")
        assert 'file_registry_canister_id = "reg-id"' in rec
        assert 'file_registry_namespace = "ext/llm_chat/1.0.22"' in rec
        assert 'description = "Ask \\"things\\""' in rec


class TestResults:
    def test_generic_result(self):
        assert mp.parse_generic_result('(variant { Ok = "created:llm_chat" })') == (True, "created:llm_chat")
        ok, msg = mp.parse_generic_result('(variant { Err = "An active developer license is required" })')
        assert ok is False and "license" in msg

    def test_review_result(self):
        assert mp.parse_review_result(json.dumps({"success": True, "verification_status": "verified"})) == (True, "verified")
        assert mp.parse_review_result(json.dumps({"success": False, "error": "reviewers only"})) == (False, "reviewers only")


class TestPublish:
    def test_creates_then_reviews_each_listing(self, tmp_path):
        calls = []

        def fake_call(canister, method, arg, network, identity, **kw):
            calls.append((method, arg))
            if method.startswith("create_"):
                return '(variant { Ok = "created:x" })'
            return json.dumps({"success": True, "verification_status": "verified"})

        ok, failed = mp.publish_listings(mp.discover(_tree(tmp_path)), marketplace="mp", registry="reg",
                                         network="ic", identity="op", approve=True, call=fake_call)
        assert (ok, failed) == (2, 0)
        assert [m for m, _ in calls] == ["create_codex", "review_listing", "create_extension", "review_listing"]
        assert calls[1][1] == '("codex", "agora", true, "first-party package")'

    def test_failed_create_skips_review_and_counts(self, tmp_path):
        def fake_call(canister, method, arg, network, identity, **kw):
            return '(variant { Err = "An active developer license is required" })'

        ok, failed = mp.publish_listings(mp.discover(_tree(tmp_path)), marketplace="mp", registry="reg",
                                         network="ic", identity="op", approve=True, call=fake_call)
        assert (ok, failed) == (0, 2)

    def test_no_approve_only_creates(self, tmp_path):
        methods = []

        def fake_call(canister, method, arg, network, identity, **kw):
            methods.append(method)
            return '(variant { Ok = "updated:x" })'

        mp.publish_listings(mp.discover(_tree(tmp_path)), marketplace="mp", registry="reg",
                            network="ic", identity=None, approve=False, call=fake_call)
        assert methods == ["create_codex", "create_extension"]
