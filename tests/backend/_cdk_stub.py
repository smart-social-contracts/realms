"""Shared _cdk / ic_python_logging stubs for standalone backend tests."""

from __future__ import annotations

import sys
import types
import typing
from unittest.mock import MagicMock


def ensure_ic_python_logging_stub() -> None:
    """Install a minimal ic_python_logging stub idempotently."""
    existing = sys.modules.get("ic_python_logging")
    if existing is not None and getattr(existing, "get_logger", None) is not None:
        return
    mock_logging = MagicMock()
    mock_logging.get_logger = lambda name: MagicMock()
    sys.modules["ic_python_logging"] = mock_logging


def ensure_cdk_stub() -> None:
    """Install a minimal _cdk stub idempotently (Variant, Record, ic, etc.)."""
    ensure_ic_python_logging_stub()

    class Variant(dict):
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    class Record(dict):
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    class _FakeStableMap:
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, *args, **kwargs):
            self._data = {}

        def insert(self, key, value):
            self._data[key] = value

        def get(self, key):
            return self._data.get(key)

    _cdk = sys.modules.get("_cdk")
    if _cdk is None:
        _cdk = types.ModuleType("_cdk")
        sys.modules["_cdk"] = _cdk

    _cdk.Async = getattr(_cdk, "Async", typing.Iterator)
    _cdk.CallResult = getattr(_cdk, "CallResult", dict)
    _cdk.Opt = typing.Optional
    _cdk.Principal = getattr(_cdk, "Principal", MagicMock)
    _cdk.Record = Record
    _cdk.Service = getattr(_cdk, "Service", type("Service", (), {}))
    _cdk.Variant = Variant
    _cdk.StableBTreeMap = getattr(_cdk, "StableBTreeMap", _FakeStableMap)
    _cdk.Vec = getattr(_cdk, "Vec", list)
    _cdk.blob = getattr(_cdk, "blob", bytes)
    _cdk.nat = getattr(_cdk, "nat", int)
    _cdk.nat8 = getattr(_cdk, "nat8", int)
    _cdk.null = getattr(_cdk, "null", None)
    _cdk.service_query = getattr(_cdk, "service_query", lambda fn: fn)
    _cdk.service_update = getattr(_cdk, "service_update", lambda fn: fn)
    _cdk.text = getattr(_cdk, "text", str)

    if not hasattr(_cdk, "ic") or _cdk.ic is None:
        _ic = MagicMock()
        _ic.time.return_value = 0
        _ic.id.return_value.to_str.return_value = "aaaaa-aa"
        _cdk.ic = _ic


def ensure_wallet_stub() -> types.ModuleType:
    """Install ic_basilisk_toolkit.wallet stub; return module for per-test Wallet swaps."""
    ensure_cdk_stub()
    wallet_module = sys.modules.get("ic_basilisk_toolkit.wallet")
    if wallet_module is None:
        wallet_module = types.ModuleType("ic_basilisk_toolkit.wallet")
        sys.modules["ic_basilisk_toolkit.wallet"] = wallet_module
    return wallet_module
