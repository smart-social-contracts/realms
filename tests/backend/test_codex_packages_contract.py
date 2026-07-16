"""Contract tests for codex packages (issue #244).

Every publishable codex under ``codices/codices/`` must be a valid
``kind: codex`` extension package:

  - manifest declares kind/codex_api_version this core supports
  - unified layout: backend/entry.py (hook module), data files under backend/
  - no legacy integration mechanisms (entity_method_overrides, init.py)
  - entry.py implements the mandatory hooks and only known optional ones
  - all Python sources parse; all declared data files exist

These tests are the regression net for the packaging contract between core
and codices — they fail when either side drifts.
"""

import ast
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
CODICES_ROOT = REPO_ROOT / "codices" / "codices"

# Hook API v1 contract (mirrors core/codex_hooks.py).
SUPPORTED_CODEX_API_VERSIONS = {1}
MANDATORY_HOOKS = {"get_config", "init"}
OPTIONAL_HOOKS = {
    "seed",
    "on_user_register",
    "on_treasury_send",
    "check_lifecycle_transition",
    "get_dashboard_config",
    "get_extension_overrides",
}

# Internal/legacy directories that are not publishable codex packages.
SKIP_DIRS = {"_common", "common", "westminster"}


def _codex_dirs():
    if not CODICES_ROOT.is_dir():
        return []
    return sorted(
        d for d in CODICES_ROOT.iterdir()
        if d.is_dir()
        and d.name not in SKIP_DIRS
        and not d.name.startswith(".")
        and (d / "manifest.json").exists()
    )


def _manifest(codex_dir):
    with open(codex_dir / "manifest.json") as f:
        return json.load(f)


def _entry_functions(codex_dir):
    """Top-level function names defined in backend/entry.py."""
    source = (codex_dir / "backend" / "entry.py").read_text()
    tree = ast.parse(source)
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


CODEX_DIRS = _codex_dirs()
CODEX_IDS = [d.name for d in CODEX_DIRS]


@pytest.fixture(params=CODEX_DIRS, ids=CODEX_IDS)
def codex_dir(request):
    return request.param


def test_codices_discovered():
    """The known first-party codices are present (submodule checked out)."""
    if not CODICES_ROOT.is_dir():
        pytest.skip("codices submodule not checked out")
    assert {"agora", "syntropia", "dominion"}.issubset(set(CODEX_IDS))


class TestManifestContract:
    def test_kind_is_codex(self, codex_dir):
        assert _manifest(codex_dir).get("kind") == "codex"

    def test_api_version_supported(self, codex_dir):
        version = _manifest(codex_dir).get("codex_api_version")
        assert version in SUPPORTED_CODEX_API_VERSIONS

    def test_machine_id_matches_directory(self, codex_dir):
        """The registry namespace key is the lowercase machine id — it must
        match the package directory, never a capitalized display name."""
        manifest = _manifest(codex_dir)
        assert manifest.get("id") == codex_dir.name
        assert manifest["id"] == manifest["id"].lower()

    def test_has_version(self, codex_dir):
        assert _manifest(codex_dir).get("version")

    def test_no_entity_method_overrides(self, codex_dir):
        """Monkey-patch overrides are replaced by the hook API (issue #244)."""
        assert "entity_method_overrides" not in _manifest(codex_dir)

    def test_dependencies_shape(self, codex_dir):
        deps = _manifest(codex_dir).get("dependencies", [])
        assert isinstance(deps, (list, dict))
        names = list(deps.keys()) if isinstance(deps, dict) else deps
        for name in names:
            assert isinstance(name, str) and name

    def test_data_files_exist_under_backend(self, codex_dir):
        manifest = _manifest(codex_dir)
        for key, rel in (manifest.get("data_files") or {}).items():
            path = codex_dir / "backend" / rel
            assert path.exists(), f"data_files[{key}] missing: backend/{rel}"


class TestPackageLayout:
    def test_backend_entry_exists(self, codex_dir):
        assert (codex_dir / "backend" / "entry.py").exists()

    def test_no_legacy_init_py(self, codex_dir):
        """Legacy exec'd init.py is replaced by the init hook."""
        assert not (codex_dir / "init.py").exists()

    def test_no_loose_python_at_package_root(self, codex_dir):
        """All code ships under backend/ (unified extension layout)."""
        loose = [
            p.name for p in codex_dir.iterdir()
            if p.suffix == ".py" and not p.name.startswith("test")
        ]
        assert loose == [], f"loose .py files outside backend/: {loose}"

    def test_all_python_sources_parse(self, codex_dir):
        for path in (codex_dir / "backend").rglob("*.py"):
            ast.parse(path.read_text(), filename=str(path))

    def test_all_data_files_are_valid_json(self, codex_dir):
        data_dir = codex_dir / "backend" / "data"
        if not data_dir.is_dir():
            return
        for path in data_dir.rglob("*.json"):
            json.loads(path.read_text())


class TestHookContract:
    def test_mandatory_hooks_implemented(self, codex_dir):
        functions = _entry_functions(codex_dir)
        missing = MANDATORY_HOOKS - functions
        assert not missing, f"entry.py missing mandatory hooks: {missing}"

    def test_public_hooks_are_known(self, codex_dir):
        """Every public entry.py function that looks like a hook must be part
        of the versioned contract — no ad-hoc core touchpoints."""
        functions = _entry_functions(codex_dir)
        hook_like = {
            f for f in functions
            if f.startswith("on_") or f.startswith("check_") or f in {"init", "seed"}
            or f.startswith("get_")
        }
        unknown = hook_like - MANDATORY_HOOKS - OPTIONAL_HOOKS
        assert not unknown, f"unknown hook-like functions: {unknown}"
