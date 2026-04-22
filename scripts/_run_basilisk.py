#!/usr/bin/env python3
"""Wrapper to run basilisk with a modulefinder patch.

Works around a Python 3.10/3.11 bug where modulefinder crashes with
'NoneType' has no attribute 'is_package' on namespace packages.
"""
import modulefinder as _mf

_orig = _mf._find_module

def _patched(name, path=None):
    try:
        return _orig(name, path)
    except AttributeError:
        raise ImportError(name)

_mf._find_module = _patched

from basilisk.__main__ import main
main()
