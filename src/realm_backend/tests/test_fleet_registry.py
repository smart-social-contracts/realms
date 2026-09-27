"""The fleet file-registry map is data in this repo, not in GaaS."""

import json
from pathlib import Path

import pytest

from core.fleet_registry import (
    parse_fleet_registries,
    registry_for_environment,
)

_REPO_FILE = Path(__file__).resolve().parents[3] / "fleet-registries.json"


def test_committed_map_resolves_staging_and_production():
    table = parse_fleet_registries(_REPO_FILE.read_text())
    assert registry_for_environment(table, "staging") == "rmf3r-xiaaa-aaaak-qzgja-cai"
    assert registry_for_environment(table, "production") == "qofs7-qyaaa-aaaag-azbya-cai"


def test_comment_keys_are_ignored_and_names_are_case_insensitive():
    table = parse_fleet_registries(
        json.dumps({"_comment": "ignore", "Staging": "aaaaa-aa"})
    )
    assert "_comment" not in table
    assert registry_for_environment(table, "STAGING") == "aaaaa-aa"


def test_unknown_environment_names_the_published_ones():
    table = parse_fleet_registries(json.dumps({"staging": "aaaaa-aa"}))
    with pytest.raises(ValueError, match="test"):
        registry_for_environment(table, "test")


def test_empty_environment_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        registry_for_environment({"staging": "aaaaa-aa"}, "  ")


def test_document_must_be_an_object():
    with pytest.raises(ValueError, match="object"):
        parse_fleet_registries("[]")
