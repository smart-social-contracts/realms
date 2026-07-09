#!/usr/bin/env python3
"""Backward-compatible entry point — prefer casals-config/_gen_arrangements.py."""
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("_gen_arrangements", _HERE / "_gen_arrangements.py")
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _mod.main()
