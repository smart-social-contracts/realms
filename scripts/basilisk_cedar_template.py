"""Pinned Cedar basilisk template — the only realm_backend pack path.

The plain CPython template (``cpython_canister_template.wasm``) has no
``_basilisk_sandbox`` and is not selectable. basilisk honours
``BASILISK_TEMPLATE_WASM`` over its default cache file; every leftover-free
or layered pack must set that variable to the Cedar image
(``cpython_canister_template_cedar.wasm``, ic-basilisk >= 0.14.2).

This module does not inspect a finished realm WASM. It only pins the
template used to pack one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Union

PathLike = Union[str, os.PathLike]

CEDAR_TEMPLATE_NAME = "cpython_canister_template_cedar.wasm"
PLAIN_TEMPLATE_NAME = "cpython_canister_template.wasm"
CEDAR_TEMPLATE_URL = (
    "https://github.com/smart-social-contracts/basilisk/releases/download/"
    f"cpython-wasm-3.13.0-ic1/{CEDAR_TEMPLATE_NAME}"
)

# C symbol for _basilisk_sandbox.sha256 (basilisk_sandbox.c). A cached Cedar
# file that predates this export cannot hash spawn sources.
_SANDBOX_SHA256_SYMBOL = b"sandbox_sha256"


def is_plain_cpython_template(path: PathLike) -> bool:
    """True if *path* is the default/plain CPython template (no sandbox)."""
    return Path(path).name == PLAIN_TEMPLATE_NAME


def cedar_template_cache_path() -> Path:
    return Path.home() / ".cache" / "realms" / "templates" / CEDAR_TEMPLATE_NAME


def _require_cedar_template(template_path: Path) -> None:
    if is_plain_cpython_template(template_path):
        raise SystemExit(
            f"plain CPython template {template_path} is not a realm_backend "
            f"pack path. Use {CEDAR_TEMPLATE_NAME} (ic-basilisk >= 0.14.2)."
        )
    if template_path.name != CEDAR_TEMPLATE_NAME:
        raise SystemExit(
            f"realm_backend must pack with {CEDAR_TEMPLATE_NAME}, not "
            f"{template_path.name}"
        )
    if not template_path.is_file():
        raise SystemExit(f"Cedar template not found: {template_path}")
    if _SANDBOX_SHA256_SYMBOL not in template_path.read_bytes():
        raise SystemExit(
            f"BASILISK template {template_path} predates _basilisk_sandbox.sha256 "
            f"(missing C symbol {_SANDBOX_SHA256_SYMBOL!r}). Delete the cached "
            f"file so {CEDAR_TEMPLATE_NAME} is fetched from ic-basilisk >= 0.14.2."
        )


def ensure_cedar_template() -> str:
    """Fetch the pinned Cedar template into the local cache and return its path."""
    dest = cedar_template_cache_path()
    if not dest.exists():
        import urllib.request

        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"   ⬇️  fetching Cedar template: {CEDAR_TEMPLATE_URL}")
        urllib.request.urlretrieve(CEDAR_TEMPLATE_URL, dest)
    _require_cedar_template(dest)
    return str(dest)


def apply_cedar_template_env(
    env: Optional[Mapping[str, str]] = None,
) -> MutableMapping[str, str]:
    """Copy *env* and force ``BASILISK_TEMPLATE_WASM`` to the Cedar template.

    An existing value — including the plain CPython template — is ignored.
    The old template is not selectable.
    """
    out: MutableMapping[str, str] = dict(os.environ if env is None else env)
    out["BASILISK_TEMPLATE_WASM"] = ensure_cedar_template()
    return out
