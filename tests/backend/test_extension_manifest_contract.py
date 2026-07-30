"""Contract between extension manifests and the capability bridge.

An extension that has been ported to the bridge declares two things:

    "ggg_api_version": 1,
    "capabilities": ["entity.list", "entity.read:Zone", "zone.create", ...]

``capabilities`` is the whole of what the host will let it do — the bridge
refuses any verb not on the list. So the list has to be checkable, or a typo
becomes a permission denied at runtime in a canister rather than a failure
here.

These tests keep the two sides honest:

  - every declared capability is a real verb or entity-read capability;
  - declaring capabilities requires a supported ``ggg_api_version``;
  - a ported extension does not still declare ``runtime: in_process``;
  - an extension declaring capabilities is actually sandbox-clean, since
    capabilities it can never reach are worse than none (they read as
    progress).
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
EXTENSIONS_ROOT = REPO_ROOT / "extensions" / "extensions"

sys.path.insert(0, str(REPO_ROOT / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import codex_scan, extension_bridge  # noqa: E402


def _manifests():
    if not EXTENSIONS_ROOT.is_dir():
        return []
    out = []
    for manifest_path in sorted(EXTENSIONS_ROOT.glob("*/manifest.json")):
        try:
            out.append((manifest_path.parent.name, json.loads(
                manifest_path.read_text(encoding="utf-8"))))
        except ValueError:
            continue
    return out


def _bridge_extensions():
    """Only extensions that have opted into the bridge."""
    return [(e, m) for e, m in _manifests() if m.get("capabilities")]


def _host_imports(ext_id):
    ext_dir = EXTENSIONS_ROOT / ext_id
    files = {
        str(p.relative_to(ext_dir)): p.read_text(encoding="utf-8")
        for p in ext_dir.glob("backend/**/*.py")
    }
    return codex_scan.scan_codex_files(files, codex_scan.SANDBOX_POLICY)


ALL = _manifests()
BRIDGE = _bridge_extensions()


@pytest.mark.skipif(not ALL, reason="extensions submodule not checked out")
@pytest.mark.parametrize("ext_id,manifest", ALL, ids=[e for e, _ in ALL])
def test_capabilities_are_known_verbs(ext_id, manifest):
    known = set(extension_bridge.known_verbs())
    declared = manifest.get("capabilities") or []
    assert isinstance(declared, list), "'capabilities' must be a list"
    unknown = sorted(set(declared) - known)
    assert not unknown, (
        f"{ext_id} declares capabilities the bridge does not offer: {unknown}. "
        f"Known: {sorted(known)}"
    )


@pytest.mark.skipif(not BRIDGE, reason="no extension has been ported yet")
@pytest.mark.parametrize("ext_id,manifest", BRIDGE, ids=[e for e, _ in BRIDGE])
def test_declares_supported_api_version(ext_id, manifest):
    version = manifest.get("ggg_api_version")
    assert version is not None, (
        f"{ext_id} declares capabilities but no 'ggg_api_version'"
    )
    assert version in extension_bridge.SUPPORTED_EXTENSION_API_VERSIONS, (
        f"{ext_id} declares ggg_api_version={version}; this host supports "
        f"{sorted(extension_bridge.SUPPORTED_EXTENSION_API_VERSIONS)}"
    )


@pytest.mark.skipif(not BRIDGE, reason="no extension has been ported yet")
@pytest.mark.parametrize("ext_id,manifest", BRIDGE, ids=[e for e, _ in BRIDGE])
def test_ported_extension_is_not_still_in_process(ext_id, manifest):
    assert manifest.get("runtime") != "in_process", (
        f"{ext_id} uses the capability bridge but still declares "
        f"\"runtime\": \"in_process\", so it never actually sandboxes"
    )


@pytest.mark.skipif(not BRIDGE, reason="no extension has been ported yet")
@pytest.mark.parametrize("ext_id,manifest", BRIDGE, ids=[e for e, _ in BRIDGE])
def test_ported_extension_has_no_host_imports(ext_id, manifest):
    violations = _host_imports(ext_id)
    assert not violations, (
        f"{ext_id} declares bridge capabilities but still imports host modules, "
        f"so it cannot spawn: "
        + "; ".join(f"{v.filename}:{v.lineno} {v.statement}" for v in violations[:5])
    )


@pytest.mark.skipif(not ALL, reason="extensions submodule not checked out")
@pytest.mark.parametrize("ext_id,manifest", ALL, ids=[e for e, _ in ALL])
def test_async_functions_are_declared_functions(ext_id, manifest):
    """``async_functions`` names entry points, so a name that is not one is a
    typo that would silently run the function synchronously — and a synchronous
    run of a function containing ``ctx.services.query`` fails at call time."""
    from core import async_bridge

    declared = async_bridge.declared_async_functions(manifest)
    functions = set(manifest.get("functions") or [])
    unknown = sorted(declared - functions)
    assert not unknown, (
        f"{ext_id} lists {unknown} in 'async_functions' but not in 'functions'"
    )


@pytest.mark.skipif(not ALL, reason="extensions submodule not checked out")
@pytest.mark.parametrize("ext_id,manifest", ALL, ids=[e for e, _ in ALL])
def test_async_extensions_declare_a_service_capability(ext_id, manifest):
    """An async function with no ``service.call:*`` capability can only ever
    fail: it will request an effect the host refuses to perform."""
    from core import async_bridge

    if not async_bridge.declared_async_functions(manifest):
        return
    declared = set(manifest.get("capabilities") or [])
    assert any(c.startswith("service.call:") for c in declared), (
        f"{ext_id} declares async functions but no 'service.call:*' capability, "
        f"so every effect it requests would be denied"
    )


def test_entity_read_capabilities_match_the_policy_registry():
    """`entity.read:X` is only meaningful for a type the bridge can project."""
    for cap in extension_bridge.read_capabilities():
        type_name = cap.split(":", 1)[1]
        assert type_name in extension_bridge.ENTITY_POLICIES
