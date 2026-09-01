"""file_registry resolution requires --registry (no silent fallback)."""

import pytest
import typer

from realms.cli.commands.files import _resolve_registry


def test_resolve_registry_explicit_wins():
    assert _resolve_registry("demo", "aaaaa-aa") == "aaaaa-aa"


def test_resolve_registry_strips_whitespace():
    assert _resolve_registry("demo", "  aaaaa-aa  ") == "aaaaa-aa"


def test_resolve_registry_missing_flag_fails_loud():
    with pytest.raises(typer.BadParameter, match="Pass --registry"):
        _resolve_registry("demo", None)


def test_resolve_registry_empty_flag_fails_loud():
    with pytest.raises(typer.BadParameter, match="Pass --registry"):
        _resolve_registry("demo", "   ")
