"""Tests for ``_resolve_extensions_root`` in the layered-publish scripts.

These exist because we discovered (when CI run #24599789350 on commit
``1b77889`` failed to install ``package_manager`` on staging) that
``scripts/publish_layered.py`` and ``scripts/build_runtime_bundles.py``
were silently iterating the wrong directory and "publishing" zero
extensions, then exiting 0. Stage 2 then crashed with
``No versions found for ext/package_manager``.

The fix is a ``_resolve_extensions_root(repo)`` helper in each script
that auto-detects nested-vs-flat layouts and **fails loud** if neither
contains any extension dirs. These tests pin that behavior.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add repo root + scripts/ to sys.path so we can import the scripts as
# regular modules even though they're top-level scripts (not a package).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_runtime_bundles as brb  # noqa: E402
import publish_layered as pl  # noqa: E402


def _make_ext(dir_path: Path, *, manifest: bool = True, frontend_rt: bool = False) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    if manifest:
        (dir_path / "manifest.json").write_text(json.dumps({"id": dir_path.name}))
    if frontend_rt:
        rt = dir_path / "frontend-rt"
        rt.mkdir()
        (rt / "package.json").write_text(json.dumps({"name": dir_path.name}))


# ---------------------------------------------------------------------------
# publish_layered._resolve_extensions_root
# ---------------------------------------------------------------------------


def test_resolve_picks_nested_layout(tmp_path: Path) -> None:
    """The realms-monorepo case: <repo>/extensions/extensions/<id>/manifest.json."""
    _make_ext(tmp_path / "extensions" / "extensions" / "package_manager")
    assert pl._resolve_extensions_root(tmp_path) == tmp_path / "extensions" / "extensions"


def test_resolve_falls_back_to_flat_layout(tmp_path: Path) -> None:
    """Standalone realms-extensions checkout: <repo>/extensions/<id>/manifest.json."""
    _make_ext(tmp_path / "extensions" / "package_manager")
    assert pl._resolve_extensions_root(tmp_path) == tmp_path / "extensions"


def test_resolve_prefers_nested_when_both_present(tmp_path: Path) -> None:
    """If both layouts somehow exist, the nested one wins (it's the real one
    inside the realms repo and matches what ci_install_mundus.py walks)."""
    _make_ext(tmp_path / "extensions" / "extensions" / "real_one")
    _make_ext(tmp_path / "extensions" / "decoy")
    assert pl._resolve_extensions_root(tmp_path) == tmp_path / "extensions" / "extensions"


def test_resolve_fails_loud_when_no_manifests(tmp_path: Path) -> None:
    """The bug we're fixing: an empty layout used to silently succeed."""
    (tmp_path / "extensions" / "extensions").mkdir(parents=True)
    (tmp_path / "extensions" / "README.md").write_text("hi")
    with pytest.raises(SystemExit) as exc:
        pl._resolve_extensions_root(tmp_path)
    msg = str(exc.value)
    assert "no extension manifests found" in msg
    assert "submodule" in msg  # mentions the likely cause + remedy


def test_resolve_ignores_shared_helper_dir(tmp_path: Path) -> None:
    """A repo with only the ``_shared`` helper dir is effectively empty."""
    (tmp_path / "extensions" / "extensions" / "_shared").mkdir(parents=True)
    with pytest.raises(SystemExit):
        pl._resolve_extensions_root(tmp_path)


def test_resolve_ignores_marketplace_and_testing(tmp_path: Path) -> None:
    """The submodule's own README/marketplace/testing dirs at ``extensions/``
    must not trick the resolver into picking the flat layout."""
    nested = tmp_path / "extensions" / "extensions"
    nested.mkdir(parents=True)
    # Outer-level decoys (these exist in the real submodule):
    (tmp_path / "extensions" / "marketplace").mkdir()
    (tmp_path / "extensions" / "testing").mkdir()
    (tmp_path / "extensions" / "README.md").write_text("hi")
    # No actual extensions ⇒ must fail, NOT pick `tmp_path/extensions`.
    with pytest.raises(SystemExit):
        pl._resolve_extensions_root(tmp_path)


# ---------------------------------------------------------------------------
# publish_layered._step_publish_extensions filter behavior
# ---------------------------------------------------------------------------


def test_publish_only_filter_with_unknown_id_fails_loud(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Passing --only-extensions=<typo> used to silently succeed too."""
    _make_ext(tmp_path / "extensions" / "extensions" / "package_manager")

    with pytest.raises(SystemExit) as exc:
        pl._step_publish_extensions(
            realms_cli=["realms"],
            registry="rrkah-fqaaa-aaaaa-aaaaq-cai",  # ignored on this path
            network="local",
            identity=None,
            extensions_repo=tmp_path,
            only=["definitely_not_an_extension"],
            namespace_prefix="ext",
        )
    msg = str(exc.value)
    assert "matched zero extensions" in msg
    assert "package_manager" in msg  # lists what *was* available


# ---------------------------------------------------------------------------
# build_runtime_bundles._resolve_extensions_root
# ---------------------------------------------------------------------------


def test_brb_resolve_picks_nested_via_frontend_rt(tmp_path: Path) -> None:
    """build_runtime_bundles cares about frontend-rt presence, not manifest.json.

    Some extensions ship only a manifest (no frontend-rt). The resolver
    must still find the layout based on either signal.
    """
    _make_ext(tmp_path / "extensions" / "extensions" / "ext_a", frontend_rt=True)
    assert brb._resolve_extensions_root(tmp_path) == tmp_path / "extensions" / "extensions"


def test_brb_resolve_picks_nested_via_manifest_only(tmp_path: Path) -> None:
    """An extension with only manifest.json (no frontend-rt) is still a valid
    layout signal — the caller will just skip it during bundle building."""
    _make_ext(tmp_path / "extensions" / "extensions" / "ext_a")  # manifest only
    assert brb._resolve_extensions_root(tmp_path) == tmp_path / "extensions" / "extensions"


def test_brb_resolve_falls_back_to_flat(tmp_path: Path) -> None:
    _make_ext(tmp_path / "extensions" / "ext_a", frontend_rt=True)
    assert brb._resolve_extensions_root(tmp_path) == tmp_path / "extensions"


def test_brb_resolve_fails_loud_when_empty(tmp_path: Path) -> None:
    (tmp_path / "extensions" / "extensions").mkdir(parents=True)
    with pytest.raises(SystemExit):
        brb._resolve_extensions_root(tmp_path)
