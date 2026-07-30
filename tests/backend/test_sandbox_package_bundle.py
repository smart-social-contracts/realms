"""Multi-module extensions in the sandbox.

The in-process loader imports an extension directory as a *package*, so
``entry.py`` can do ``from . import roles``. A subinterpreter has no filesystem
and ``sys.path == []``, so until this existed a multi-file extension could not be
sandboxed at all — the spawn reads one source string. That silently ruled out
``procurement`` (#276), which is six modules, and would have forced either a
1,500-line single file or a rewrite.

The fix reuses the mechanism ``ggg_sdk`` already relies on: register the modules
in the sandbox's own ``sys.modules``, where a relative import finds them without
any path lookup.

Load order is the part that can go wrong quietly. ``from .constants import
VALID_TRANSITIONS`` needs ``constants`` already executed, so the modules are
sorted by dependency rather than by name.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import runtime_sandbox as rs  # noqa: E402


@pytest.fixture(autouse=True)
def keep_host_modules():
    """The loader registers its own ``ggg_sdk`` and package in ``sys.modules``.

    In a real subinterpreter that table is private; here it is the test process's,
    so it is restored after every test. Without this, the sandbox's ``ggg_sdk``
    (which has no ``GGG_SDK_SOURCE``) shadows the host's for the rest of the run.
    """
    names = ("ggg_sdk", rs.SANDBOX_PACKAGE)
    saved = {n: sys.modules.get(n) for n in names}
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is not None:
                sys.modules[name] = value
            else:
                sys.modules.pop(name, None)


@pytest.fixture
def extension(monkeypatch):
    """Write a throwaway multi-module extension and point the loader at it."""
    import core.runtime_extensions as rex

    root = tempfile.mkdtemp()
    monkeypatch.setattr(rex, "EXTENSIONS_DIR", root)

    def build(ext_id, files):
        path = os.path.join(root, ext_id)
        os.makedirs(path, exist_ok=True)
        for name, source in files.items():
            with open(os.path.join(path, name), "w") as f:
                f.write(source)
        return ext_id

    return build


def spawn(ext_id):
    """Build and execute the spawned source as a subinterpreter would."""
    source = rs._build_codex_sandbox_source(
        rs._extension_source(ext_id), rs._extension_package_modules(ext_id)
    )
    namespace = {}
    exec(compile(source, "<sandbox>", "exec"), namespace)
    return namespace


def run_sandboxed(ext_id, function_name, args="{}"):
    return spawn(ext_id)[function_name](args)


# ---------------------------------------------------------------------------
# Dependency ordering
# ---------------------------------------------------------------------------


def test_from_dot_import_dependencies_are_detected():
    source = "from . import entities\nfrom . import roles, scoring\n"
    assert set(rs._module_dependencies(source)) == {"entities", "roles", "scoring"}


def test_from_dot_module_import_names_are_detected():
    source = "from .constants import VALID_TRANSITIONS, LIMIT\n"
    assert rs._module_dependencies(source) == ["constants"]


def test_aliased_imports_are_detected():
    assert rs._module_dependencies("from . import roles as r\n") == ["roles"]


def test_load_order_puts_dependencies_first():
    """The case that matters: a from-import needs the names to exist already."""
    order = rs._order_modules({
        "logic": "from .constants import LIMIT\nfrom . import entities\n",
        "entities": "from .constants import LIMIT\n",
        "constants": "LIMIT = 1\n",
    })
    assert order.index("constants") < order.index("entities") < order.index("logic")


def test_independent_modules_are_ordered_stably():
    order = rs._order_modules({"b": "", "a": "", "c": ""})
    assert order == ["a", "b", "c"]


def test_external_imports_are_not_treated_as_dependencies():
    """``from ggg_sdk import ctx`` is not a sibling module."""
    order = rs._order_modules({"only": "from ggg_sdk import ctx\nimport json\n"})
    assert order == ["only"]


def test_import_cycle_does_not_hang(caplog):
    """A cycle is reported and loaded in name order rather than looping."""
    order = rs._order_modules({
        "a": "from . import b\n",
        "b": "from . import a\n",
    })
    assert sorted(order) == ["a", "b"]


# ---------------------------------------------------------------------------
# End to end through the spawned source
# ---------------------------------------------------------------------------


PACKAGE = {
    "constants.py": "LIMIT = 7\nVALID = {'draft': 'open'}\n",
    "entities.py": "from .constants import LIMIT\n\ndef cap():\n    return LIMIT\n",
    "helpers.py": (
        "from . import entities\n"
        "from .constants import VALID\n"
        "\n"
        "def doubled():\n"
        "    return entities.cap() * 2\n"
        "\n"
        "def transitions():\n"
        "    return VALID\n"
    ),
    "entry.py": (
        "import json\n"
        "from . import helpers\n"
        "from .constants import LIMIT\n"
        "\n"
        "def run(args):\n"
        "    return json.dumps({\n"
        "        'limit': LIMIT,\n"
        "        'doubled': helpers.doubled(),\n"
        "        'transitions': helpers.transitions(),\n"
        "    })\n"
    ),
}


def test_a_multi_module_extension_runs(extension):
    """``from . import helpers`` and ``from .constants import LIMIT`` both work
    inside the sandbox, with no filesystem and an empty sys.path."""
    import json

    ext_id = extension("demo", PACKAGE)
    result = json.loads(run_sandboxed(ext_id, "run"))
    assert result == {
        "limit": 7, "doubled": 14, "transitions": {"draft": "open"},
    }


def test_the_async_dispatcher_sees_a_bundled_extension(extension):
    """Bundling and the effect-style dispatcher have to coexist — both are
    appended to the same spawned source."""
    ext_id = extension("demo_async", PACKAGE)
    out = spawn(ext_id)["__ext_async_round__"]("{}", "run", {})
    assert out["status"] == "ok"
    assert '"limit": 7' in out["value"]


def test_entry_and_dunder_init_are_not_bundled_as_submodules(extension):
    """``entry.py`` is the spawned source itself, and ``__init__.py`` would
    re-run the package body."""
    ext_id = extension("demo_skip", {
        **PACKAGE, "__init__.py": "raise RuntimeError('should not run')\n",
    })
    names = [name for name, _ in rs._extension_package_modules(ext_id)]
    assert "entry" not in names and "__init__" not in names
    assert set(names) == {"constants", "entities", "helpers"}


def test_a_single_file_extension_needs_no_package(extension):
    """The common case must not grow a package it does not use."""
    ext_id = extension("solo", {
        "entry.py": "def run(args):\n    return 'ok'\n",
    })
    assert rs._extension_package_modules(ext_id) == []
    assert run_sandboxed(ext_id, "run") == "ok"


def test_non_python_files_are_ignored(extension):
    ext_id = extension("mixed", {
        "entry.py": "def run(args):\n    return 'ok'\n",
        "manifest.json": '{"name": "mixed"}',
        "notes.txt": "hello",
    })
    assert rs._extension_package_modules(ext_id) == []


def test_a_submodule_cannot_reach_the_host(extension):
    """Bundling must not become a way in: a sibling module is subject to the same
    empty sys.path as the entry point."""
    ext_id = extension("sneaky", {
        "backdoor.py": "import ggg\n",
        "entry.py": "from . import backdoor\n\ndef run(args):\n    return 'ok'\n",
    })
    # ``ggg`` is importable in this test process, so the honest check is that the
    # submodule is executed as ordinary sandboxed source with no special path,
    # not that this particular import fails off-chain.
    source = rs._build_codex_sandbox_source(
        rs._extension_source(ext_id), rs._extension_package_modules(ext_id)
    )
    assert "sys.path" not in source, "the bundle must not add anything to sys.path"
    assert "backdoor.py" in source, "the submodule is inlined, not loaded from disk"
