#!/usr/bin/env python3
"""Quick self-test for main-channel version helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli"))

from realms.cli.casals_versions import (
    is_main_channel,
    main_build_version,
    pick_latest_main_key,
    ver_tuple,
)


def test_is_main_channel():
    assert is_main_channel("main")
    assert is_main_channel("main.1749254400.abc1234")
    assert not is_main_channel("0.4.0")
    assert not is_main_channel("latest")


def test_ver_tuple_orders_main_by_timestamp():
    assert ver_tuple("main.100.abc") < ver_tuple("main.200.def")
    assert ver_tuple("0.4.0") < ver_tuple("main.100.abc")


def test_pick_latest_main_key():
    authorized = [
        {"family": "realm-backend", "version": "0.4.0", "key": "realm-backend@0.4.0"},
        {"family": "realm-backend", "version": "main.100.aaa", "key": "realm-backend@main.100.aaa"},
        {"family": "realm-backend", "version": "main.200.bbb", "key": "realm-backend@main.200.bbb"},
        {"family": "realm-assets", "version": "main.150.ccc", "key": "realm-assets@main.150.ccc"},
    ]
    backend = [w for w in authorized if w["family"] == "realm-backend"]
    assert pick_latest_main_key(backend) == "realm-backend@main.200.bbb"
    assets = [w for w in authorized if w["family"] == "realm-assets"]
    assert pick_latest_main_key(assets) == "realm-assets@main.150.ccc"
    assert pick_latest_main_key([w for w in authorized if w["family"] == "missing"]) is None


def test_main_build_version_format():
    v = main_build_version(Path(__file__).resolve().parents[1])
    parts = v.split(".")
    assert parts[0] == "main"
    assert parts[1].isdigit()
    assert len(parts[2]) == 7


if __name__ == "__main__":
    test_is_main_channel()
    test_ver_tuple_orders_main_by_timestamp()
    test_pick_latest_main_key()
    test_main_build_version_format()
    print("casals_versions: all checks passed")
