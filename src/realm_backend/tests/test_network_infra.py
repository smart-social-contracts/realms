"""Unit tests for GOS network infra IDs and bootstrap allowlist."""

from core.network_infra import (
    is_known_bootstrap_principal,
    known_bootstrap_principals,
)

_DEMO_LIVE_INSTALLER = "moqmm-caaaa-aaaah-qu27q-cai"
_DEMO_LIVE_REGISTRY = "mjrky-pyaaa-aaaah-qu27a-cai"
_DEMO_LEGACY_INSTALLER = "2s4td-daaaa-aaaao-bazmq-cai"
_DEMO_LEGACY_REGISTRY = "rhw4p-gqaaa-aaaac-qbw7q-cai"
_TEST_INSTALLER = "fltjm-tyaaa-aaaap-qunhq-cai"
_TEST_REGISTRY = "yhw3g-fyaaa-aaaas-qgorq-cai"


def test_known_bootstrap_principals_includes_live_demo_installer():
    principals = known_bootstrap_principals()
    assert _DEMO_LIVE_INSTALLER in principals
    assert _DEMO_LIVE_REGISTRY in principals
    assert is_known_bootstrap_principal(_DEMO_LIVE_INSTALLER) is True
    assert is_known_bootstrap_principal(_DEMO_LIVE_REGISTRY) is True


def test_known_bootstrap_principals_keeps_legacy_demo_and_test():
    principals = known_bootstrap_principals()
    assert _DEMO_LEGACY_INSTALLER in principals
    assert _DEMO_LEGACY_REGISTRY in principals
    assert _TEST_INSTALLER in principals
    assert _TEST_REGISTRY in principals


def test_known_bootstrap_principals_rejects_unlisted():
    assert is_known_bootstrap_principal("random-attacker") is False
    assert is_known_bootstrap_principal("") is False
    assert is_known_bootstrap_principal(None) is False
