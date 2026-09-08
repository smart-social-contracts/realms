"""Ensure descriptor test-flag mapping has a single source of truth."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from realms.cli.descriptor_flags import TEST_PARAM_MAP

ROOT = Path(__file__).resolve().parents[2]

CONSUMERS = (
    ROOT / "casals-config" / "_gen_arrangements.py",
    ROOT / "cli" / "realms" / "cli" / "commands" / "mundus.py",
    ROOT / "scripts" / "ci_install_mundus.py",
)

# Inline dict literals mapping TEST_MODE_* descriptor params to flag keys.
_HARDCODED_MAP_PATTERN = re.compile(
    r'["\']TEST_MODE_[A-Z0-9_]+["\']\s*:\s*["\'][a-z_]+["\']'
)

EXPECTED_KEYS = frozenset(
    {
        "TEST_MODE",
        "TEST_MODE_II_BYPASS",
        "TEST_MODE_USER_SELF_REGISTRATION",
        "TEST_MODE_DEMO_DATA",
        "TEST_MODE_SKIP_TERMS",
        "TEST_MODE_SKIP_PASSPORT_ZKPROOF",
        "TEST_MODE_DISABLE_MONETARY_TOKENS",
        "TEST_MODE_DEMO_NOTICE",
    }
)


def test_no_hardcoded_test_mode_maps_in_consumers():
    for path in CONSUMERS:
        source = path.read_text()
        assert not _HARDCODED_MAP_PATTERN.search(source), (
            f"{path.relative_to(ROOT)} still contains a hardcoded TEST_MODE_* mapping"
        )


def test_shared_map_has_expected_keys():
    assert frozenset(TEST_PARAM_MAP) == EXPECTED_KEYS


def test_shared_map_excludes_removed_skip_authentication():
    assert "TEST_MODE_SKIP_AUTHENTICATION" not in TEST_PARAM_MAP
    assert "skip_authentication" not in TEST_PARAM_MAP.values()


def test_consumer_files_parse():
    for path in CONSUMERS:
        ast.parse(path.read_text())
