"""Unit tests for the codex import-policy scanner (issue #265).

Covers core/codex_scan.py:
  - forbidden host-internal and private-facade imports are flagged
  - allowed imports (public ggg facade, stdlib, relative siblings) are not
  - statements the scanner must not misread: strings, comments, continuations
  - warn vs enforce reporting in check_codex_imports
  - the scanner runs without ``ast``/``re``, which the canister only stubs
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

sys.modules.setdefault("_cdk", MagicMock())

import core.codex_scan as codex_scan  # noqa: E402


def _reasons(source):
    return [v.statement for v in codex_scan.scan_source("codex.py", source)]


# --- violations -------------------------------------------------------------


def test_flags_host_internal_import():
    assert _reasons("import core.access") == ["import core.access"]


def test_flags_host_internal_from_import():
    assert _reasons("from core.access import _check_access") == [
        "from core.access import _check_access"
    ]


def test_flags_private_ggg_submodule():
    assert _reasons("from ggg.system.user_profile import Operations") == [
        "from ggg.system.user_profile import Operations"
    ]


def test_flags_each_name_in_multi_import():
    assert _reasons("import os, core.access, json") == ["import core.access"]


def test_reports_original_line_number():
    source = '"""Module docstring\n\nspanning lines\n"""\n\nimport core.access\n'
    (violation,) = codex_scan.scan_source("codex.py", source)
    assert violation.lineno == 6


def test_strips_alias_from_reported_name():
    assert _reasons("import core.access as ca") == ["import core.access"]


def test_flags_import_after_semicolon():
    assert _reasons("import json; import core.access") == ["import core.access"]


# --- allowed ----------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "from ggg import User, Realm",
        "import ggg",
        "import json",
        "from datetime import datetime",
        "from . import helpers",
        "from .siblings import thing",
        "from ..package import thing",
    ],
)
def test_allows_permitted_imports(source):
    assert codex_scan.scan_source("codex.py", source) == []


def test_ignores_imports_inside_string_literals():
    source = 'DOC = "from core.access import _check_access"\n'
    assert codex_scan.scan_source("codex.py", source) == []


def test_ignores_imports_inside_docstrings():
    source = '"""Never do this:\n\nfrom core.access import _check_access\n"""\n'
    assert codex_scan.scan_source("codex.py", source) == []


def test_ignores_commented_out_imports():
    assert codex_scan.scan_source("codex.py", "# import core.access\n") == []


def test_ignores_identifiers_that_merely_start_with_a_keyword():
    source = "importer = 1\nfromage = 2\n"
    assert codex_scan.scan_source("codex.py", source) == []


# --- multi-line statements --------------------------------------------------


def test_flags_parenthesized_multiline_import():
    source = "from core.access import (\n    _check_access,\n    Operations,\n)\n"
    (violation,) = codex_scan.scan_source("codex.py", source)
    assert violation.statement == "from core.access import _check_access, Operations"
    assert violation.lineno == 1


def test_flags_backslash_continued_import():
    source = "from core.access \\\n    import _check_access\n"
    (violation,) = codex_scan.scan_source("codex.py", source)
    assert violation.statement == "from core.access import _check_access"


def test_resumes_scanning_after_a_multiline_import():
    source = "from ggg import (\n    User,\n)\nimport core.access\n"
    (violation,) = codex_scan.scan_source("codex.py", source)
    assert violation.lineno == 4


# --- file map ---------------------------------------------------------------


def test_scan_codex_files_skips_non_python_and_non_string_content():
    files = {
        "manifest.json": '{"imports": "from core.access import x"}',
        "entry.py": "import core.access",
        "broken.py": None,
    }
    (violation,) = codex_scan.scan_codex_files(files)
    assert violation.filename == "entry.py"


# --- reporting --------------------------------------------------------------


def test_check_returns_empty_when_clean():
    files = {"entry.py": "from ggg import User"}
    assert codex_scan.check_codex_imports("syntropia", files, enforce=True) == ""


def test_check_warn_mode_never_rejects():
    files = {"entry.py": "import core.access"}
    assert codex_scan.check_codex_imports("syntropia", files, enforce=False) == ""


def test_check_enforce_mode_rejects_with_detail():
    files = {"entry.py": "import core.access"}
    error = codex_scan.check_codex_imports("syntropia", files, enforce=True)
    assert "violates the GGG import policy" in error
    assert "entry.py:1" in error


# --- canister runtime -------------------------------------------------------


def test_scans_without_ast_or_re(monkeypatch):
    """The canister's frozen stdlib stubs ``ast`` and ``re``: importing them
    succeeds but every attribute lookup raises. A scanner that reaches for
    either fails every codex install, so it must use neither."""

    class _StubModule:
        __name__ = "stub"

        def __getattr__(self, name):
            raise AttributeError(f"module 'stub' has no attribute '{name}'")

    for name in ("ast", "re"):
        monkeypatch.setitem(sys.modules, name, _StubModule())

    source = "import core.access\nfrom ggg import User\n"
    assert _reasons(source) == ["import core.access"]
