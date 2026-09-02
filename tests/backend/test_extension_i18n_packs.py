"""Extension frontend i18n pack contract (issue #393)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
EXTENSIONS_ROOT = REPO_ROOT / "extensions" / "extensions"

I18N_EXTENSIONS = [
    "welcome",
    "public_dashboard",
    "voting",
    "member_manager",
    "realm_settings",
    "member_dashboard",
]

LOCALE_IDS = ["en", "es", "de", "fr", "it", "zh-CN", "ca-valencia"]


def _i18n_dir(ext_id: str) -> Path:
    return EXTENSIONS_ROOT / ext_id / "frontend" / "i18n" / "locales" / "extensions" / ext_id


def _load_flat_keys(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return set(data.keys())


@pytest.mark.skipif(not EXTENSIONS_ROOT.is_dir(), reason="extensions submodule not checked out")
@pytest.mark.parametrize("ext_id", I18N_EXTENSIONS)
def test_extension_i18n_locale_files_exist(ext_id: str):
    i18n_dir = _i18n_dir(ext_id)
    assert i18n_dir.is_dir(), f"missing i18n dir for {ext_id}: {i18n_dir}"
    for locale in LOCALE_IDS:
        locale_path = i18n_dir / f"{locale}.json"
        assert locale_path.is_file(), f"missing {ext_id} locale file: {locale_path}"


@pytest.mark.skipif(not EXTENSIONS_ROOT.is_dir(), reason="extensions submodule not checked out")
@pytest.mark.parametrize("ext_id", I18N_EXTENSIONS)
def test_extension_i18n_non_en_keys_match_en(ext_id: str):
    i18n_dir = _i18n_dir(ext_id)
    en_keys = _load_flat_keys(i18n_dir / "en.json")
    for locale in LOCALE_IDS:
        if locale == "en":
            continue
        locale_keys = _load_flat_keys(i18n_dir / f"{locale}.json")
        missing = sorted(en_keys - locale_keys)
        extra = sorted(locale_keys - en_keys)
        assert not missing, f"{ext_id}/{locale}.json missing keys: {missing}"
        assert not extra, f"{ext_id}/{locale}.json extra keys: {extra}"
