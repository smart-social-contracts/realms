"""Unit tests for the Cloudflare DNS applier. No network."""

from __future__ import annotations

import pytest

from realms.cli.cloudflare import (
    PROXIED,
    CloudflareDns,
    CloudflareError,
    apply_records,
    cloudflare_record_type,
    token_from_env,
    zone_for_domain,
)
from realms.cli.commands.env import _dns_settings
from realms.cli.dns import render_dns_records


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if self._payload is _NOT_JSON:
            raise ValueError("not json")
        return self._payload


_NOT_JSON = object()


class _FakeSession:
    """Records requests and replays queued responses keyed by (method, path)."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []
        self.zone_result = [{"id": "zone-1"}]
        self.existing: dict[tuple[str, str], dict] = {}
        self.written: list[dict] = []
        self.deleted: list[str] = []

    def request(self, method, url, headers=None, timeout=None, **kwargs):
        path = url.split("/client/v4", 1)[1]
        self.calls.append((method, path, kwargs))
        self.last_headers = headers or {}

        if method == "GET" and path == "/zones":
            return _Response({"success": True, "result": self.zone_result})
        if method == "GET" and path.endswith("/dns_records"):
            params = kwargs.get("params") or {}
            hit = self.existing.get((params.get("type"), params.get("name")))
            if hit is None:
                result = []
            else:
                result = hit if isinstance(hit, list) else [hit]
            return _Response({"success": True, "result": result})
        if method == "DELETE":
            self.deleted.append(path.rsplit("/", 1)[-1])
            return _Response({"success": True, "result": {"id": "gone"}})
        if method in {"POST", "PATCH"}:
            self.written.append({"method": method, "path": path, "body": kwargs.get("json")})
            return _Response({"success": True, "result": {"id": "rec-new"}})
        raise AssertionError(f"unexpected {method} {path}")


def _records(canister_id="aaaaa-aa"):
    return render_dns_records("test.realmsgos.org", canister_id)


class TestZoneDerivation:
    def test_two_label_zones(self):
        assert zone_for_domain("test.realmsgos.org") == "realmsgos.org"
        assert zone_for_domain("staging.gos.earth") == "gos.earth"

    def test_apex_is_its_own_zone(self):
        assert zone_for_domain("realmsgos.org") == "realmsgos.org"

    def test_bare_label_is_refused(self):
        with pytest.raises(CloudflareError):
            zone_for_domain("localhost")


class TestRecordTypeMapping:
    def test_cname_alias_becomes_cname(self):
        host, txt, acme = _records()
        assert host.record_type == "CNAME/ALIAS"
        assert cloudflare_record_type(host) == "CNAME"
        assert cloudflare_record_type(txt) == "TXT"
        assert cloudflare_record_type(acme) == "CNAME"


class TestApply:
    def test_creates_all_three_records_on_an_empty_zone(self):
        session = _FakeSession()
        outcomes = apply_records(
            _records("kv5e2-yiaaa-aaaak-qze3a-cai"),
            token="tok",
            zone="realmsgos.org",
            session=session,
        )

        assert [o.action for o in outcomes] == ["created", "created", "created"]
        bodies = [w["body"] for w in session.written]
        assert [b["type"] for b in bodies] == ["CNAME", "TXT", "CNAME"]
        assert [b["name"] for b in bodies] == [
            "test.realmsgos.org",
            "_canister-id.test.realmsgos.org",
            "_acme-challenge.test.realmsgos.org",
        ]
        # The canister id is the payload of the TXT record, verbatim.
        assert bodies[1]["content"] == "kv5e2-yiaaa-aaaak-qze3a-cai"

    def test_never_proxies(self):
        session = _FakeSession()
        apply_records(_records(), token="tok", zone="realmsgos.org", session=session)
        assert PROXIED is False
        assert all(w["body"]["proxied"] is False for w in session.written)

    def test_remap_patches_only_the_canister_id_record(self):
        session = _FakeSession()
        # Zone already correct for the old canister.
        session.existing = {
            ("CNAME", "test.realmsgos.org"): {
                "id": "r1",
                "content": "test.realmsgos.org.icp1.io",
                "proxied": False,
                "ttl": 60,
            },
            ("TXT", "_canister-id.test.realmsgos.org"): {
                "id": "r2",
                "content": "old11-canister-id",
                "proxied": False,
                "ttl": 60,
            },
            ("CNAME", "_acme-challenge.test.realmsgos.org"): {
                "id": "r3",
                "content": "_acme-challenge.test.realmsgos.org.icp2.io",
                "proxied": False,
                "ttl": 60,
            },
        }

        outcomes = apply_records(
            _records("new22-canister-id"), token="tok", zone="realmsgos.org", session=session
        )

        assert [o.action for o in outcomes] == ["unchanged", "updated", "unchanged"]
        assert len(session.written) == 1
        patch = session.written[0]
        assert patch["method"] == "PATCH"
        assert patch["path"].endswith("/dns_records/r2")
        assert patch["body"]["content"] == "new22-canister-id"
        assert "old11-canister-id -> new22-canister-id" == outcomes[1].detail

    def test_second_run_changes_nothing(self):
        session = _FakeSession()
        session.existing = {
            ("CNAME", "test.realmsgos.org"): {
                "id": "r1", "content": "test.realmsgos.org.icp1.io", "proxied": False, "ttl": 60,
            },
            ("TXT", "_canister-id.test.realmsgos.org"): {
                "id": "r2", "content": "same-id", "proxied": False, "ttl": 60,
            },
            ("CNAME", "_acme-challenge.test.realmsgos.org"): {
                "id": "r3",
                "content": "_acme-challenge.test.realmsgos.org.icp2.io",
                "proxied": False,
                "ttl": 60,
            },
        }
        outcomes = apply_records(
            _records("same-id"), token="tok", zone="realmsgos.org", session=session
        )
        assert [o.action for o in outcomes] == ["unchanged"] * 3
        assert session.written == []

    def test_a_proxied_record_gets_turned_off(self):
        session = _FakeSession()
        session.existing = {
            ("CNAME", "test.realmsgos.org"): {
                "id": "r1",
                "content": "test.realmsgos.org.icp1.io",
                "proxied": True,  # orange cloud on: breaks the IC gateway
                "ttl": 60,
            },
        }
        outcomes = apply_records(
            _records(), token="tok", zone="realmsgos.org", session=session
        )
        assert outcomes[0].action == "updated"
        assert outcomes[0].detail == "settings realigned"
        assert session.written[0]["body"]["proxied"] is False

    def test_zone_derived_from_domain_when_not_given(self):
        session = _FakeSession()
        apply_records(_records(), token="tok", domain="test.realmsgos.org", session=session)
        zone_call = next(c for c in session.calls if c[1] == "/zones")
        assert zone_call[2]["params"] == {"name": "realmsgos.org"}

    def test_token_is_sent_as_bearer(self):
        session = _FakeSession()
        apply_records(_records(), token="sekrit", zone="realmsgos.org", session=session)
        assert session.last_headers["Authorization"] == "Bearer sekrit"

    def test_empty_record_list_touches_nothing(self):
        session = _FakeSession()
        assert apply_records([], token="tok", zone="realmsgos.org", session=session) == []
        assert session.calls == []


class TestDuplicates:
    """The IC refuses a domain whose _canister-id holds more than one TXT record."""

    def _session_with_two_txt(self):
        session = _FakeSession()
        session.existing = {
            ("TXT", "_canister-id.test.realmsgos.org"): [
                {"id": "keep", "content": "old-id", "proxied": False, "ttl": 60},
                {"id": "dupe", "content": "stale-id", "proxied": False, "ttl": 60},
            ],
        }
        return session

    def test_extra_txt_records_are_deleted(self):
        session = self._session_with_two_txt()
        outcomes = apply_records(
            _records("new-id"), token="tok", zone="realmsgos.org", session=session
        )

        assert session.deleted == ["dupe"]
        txt = outcomes[1]
        assert txt.action == "updated"
        assert "dropped 1 duplicate" in txt.detail
        assert "old-id -> new-id" in txt.detail

    def test_duplicate_is_reported_even_when_content_already_right(self):
        session = _FakeSession()
        session.existing = {
            ("TXT", "_canister-id.test.realmsgos.org"): [
                {"id": "keep", "content": "same-id", "proxied": False, "ttl": 60},
                {"id": "dupe", "content": "same-id", "proxied": False, "ttl": 60},
            ],
        }
        outcomes = apply_records(
            _records("same-id"), token="tok", zone="realmsgos.org", session=session
        )
        # Not "unchanged": the zone did change, and silence would hide the fix.
        assert outcomes[1].action == "updated"
        assert outcomes[1].detail == "dropped 1 duplicate"
        assert session.deleted == ["dupe"]

    def test_a_single_record_is_never_deleted(self):
        session = _FakeSession()
        session.existing = {
            ("TXT", "_canister-id.test.realmsgos.org"): {
                "id": "only", "content": "same-id", "proxied": False, "ttl": 60,
            },
        }
        apply_records(_records("same-id"), token="tok", zone="realmsgos.org", session=session)
        assert session.deleted == []


class TestErrors:
    def test_unknown_zone_is_an_error(self):
        session = _FakeSession()
        session.zone_result = []
        with pytest.raises(CloudflareError, match="no Cloudflare zone named"):
            apply_records(_records(), token="tok", zone="nope.org", session=session)

    def test_403_names_the_permissions_needed(self):
        class Forbidden(_FakeSession):
            def request(self, method, url, headers=None, timeout=None, **kwargs):
                return _Response(
                    {"success": False, "errors": [{"code": 9109, "message": "unauthorized"}]},
                    status_code=403,
                )

        with pytest.raises(CloudflareError, match="Zone:Read and DNS:Edit"):
            apply_records(_records(), token="tok", zone="realmsgos.org", session=Forbidden())

    def test_api_failure_surfaces_cloudflare_error_text(self):
        class Failing(_FakeSession):
            def request(self, method, url, headers=None, timeout=None, **kwargs):
                return _Response(
                    {"success": False, "errors": [{"code": 1004, "message": "bad record"}]}
                )

        with pytest.raises(CloudflareError, match="1004: bad record"):
            apply_records(_records(), token="tok", zone="realmsgos.org", session=Failing())

    def test_non_json_body_is_reported(self):
        class Html(_FakeSession):
            def request(self, method, url, headers=None, timeout=None, **kwargs):
                return _Response(_NOT_JSON, status_code=502)

        with pytest.raises(CloudflareError, match="non-JSON body"):
            apply_records(_records(), token="tok", zone="realmsgos.org", session=Html())

    def test_empty_token_refused_up_front(self):
        with pytest.raises(CloudflareError, match="empty Cloudflare API token"):
            CloudflareDns("")


class TestTokenFromEnv:
    def test_reads_and_strips(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "  tok  ")
        assert token_from_env() == "tok"

    def test_absent_is_none(self, monkeypatch):
        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        assert token_from_env() is None

    def test_blank_is_none(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "   ")
        assert token_from_env() is None

    def test_honours_a_custom_variable_name(self, monkeypatch):
        monkeypatch.setenv("CF_TOKEN_STAGING", "abc")
        assert token_from_env("CF_TOKEN_STAGING") == "abc"


class TestDnsSettings:
    def test_defaults_when_absent(self):
        provider, zone, token_env, ttl = _dns_settings({})
        assert provider == "manual"
        assert zone == ""
        assert token_env == "CLOUDFLARE_API_TOKEN"
        assert ttl == 60

    def test_explicit_values_honoured(self):
        cfg = {
            "dns": {
                "provider": "CloudFlare",
                "zone": "realmsgos.org",
                "token_env": "CF_TOKEN_STAGING",
                "ttl": 120,
            }
        }
        provider, zone, token_env, ttl = _dns_settings(cfg)
        assert provider == "cloudflare"
        assert zone == "realmsgos.org"
        assert token_env == "CF_TOKEN_STAGING"
        assert ttl == 120

    def test_unknown_provider_refused(self):
        with pytest.raises(ValueError, match="dns.provider must be one of"):
            _dns_settings({"dns": {"provider": "route53"}})

    def test_ttl_floor_enforced(self):
        with pytest.raises(ValueError, match="at least 60"):
            _dns_settings({"dns": {"ttl": 30}})
        assert _dns_settings({"dns": {"ttl": 1}})[3] == 1

    def test_no_token_field_is_read(self):
        cfg = {
            "dns": {
                "provider": "cloudflare",
                "token": "must-not-be-used",
                "token_env": "MY_CF_TOKEN",
            }
        }
        _, _, token_env, _ = _dns_settings(cfg)
        assert token_env == "MY_CF_TOKEN"


class TestRenderDnsRecords:
    def test_three_records_match_gaas_contract(self):
        canister_id = "kv5e2-yiaaa-aaaak-qze3a-cai"
        records = render_dns_records("test.realmsgos.org", canister_id)

        assert len(records) == 3
        assert records[0].record_type == "CNAME/ALIAS"
        assert records[0].host == "test.realmsgos.org"
        assert records[0].value == "test.realmsgos.org.icp1.io"

        assert records[1].record_type == "TXT"
        assert records[1].host == "_canister-id.test.realmsgos.org"
        assert records[1].value == canister_id

        assert records[2].record_type == "CNAME"
        assert records[2].host == "_acme-challenge.test.realmsgos.org"
        assert records[2].value == "_acme-challenge.test.realmsgos.org.icp2.io"


class TestPreflight:
    """A missing token must stop the run before the deploy, not after it."""

    def test_manual_needs_no_token(self, monkeypatch):
        from realms.cli.commands.env import _check_dns_credentials

        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        _check_dns_credentials({"dns": {"provider": "manual"}}, "test.realmsgos.org")

    def test_absent_dns_block_needs_no_token(self, monkeypatch):
        from realms.cli.commands.env import _check_dns_credentials

        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        _check_dns_credentials({}, "test.realmsgos.org")

    def test_cloudflare_without_token_raises_before_deploying(self, monkeypatch):
        from realms.cli.commands.env import _check_dns_credentials

        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="CLOUDFLARE_API_TOKEN is not set"):
            _check_dns_credentials({"dns": {"provider": "cloudflare"}}, "test.realmsgos.org")

    def test_cloudflare_with_token_passes(self, monkeypatch):
        from realms.cli.commands.env import _check_dns_credentials

        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
        _check_dns_credentials({"dns": {"provider": "cloudflare"}}, "test.realmsgos.org")

    def test_custom_token_env_is_honoured(self, monkeypatch):
        from realms.cli.commands.env import _check_dns_credentials

        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        monkeypatch.setenv("CF_REALMS", "tok")
        _check_dns_credentials(
            {"dns": {"provider": "cloudflare", "token_env": "CF_REALMS"}},
            "test.realmsgos.org",
        )
