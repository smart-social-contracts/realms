#!/usr/bin/env python3
"""Leftover-free realm_backend pack. Cedar is the only template.

Also selects the **build variant**. basilisk copies the whole
``src/realm_backend`` tree into the WASM, so a test-only code path left in that
tree would ship to production even if no setting could reach it. The two variants
therefore live in ``scripts/build_variants/`` — outside the packed tree — and
exactly one is copied over ``src/realm_backend/core/build_variant.py`` before
packing. What is not selected is not compiled in.

Production is the default; a test build must be asked for explicitly. After
packing, the artifact is byte-scanned for the test sentinel, so "we built the
right variant" is verified against the WASM rather than assumed from the flags.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from basilisk_cedar_template import apply_cedar_template_env  # noqa: E402

# Always exported on the Cedar pack. Do not gate these behind leftover-free
# or a per-deploy sandbox allowlist — the GOS installer calls enter_setup
# on every new realm (IC0536 if the method is missing from WASM exports).
REQUIRED_UPDATE_EXPORTS = ("enter_setup",)

VARIANTS = ("production", "test")
DEFAULT_VARIANT = "production"
TEST_BUILD_SENTINEL = b"REALMS_TEST_BUILD_AUTH_BYPASS"


def _variant_source(variant: str) -> Path:
    return _SCRIPTS / "build_variants" / f"{variant}.py"


def select_build_variant(root: Path, variant: str) -> None:
    """Copy the chosen variant over the module the canister imports."""
    if variant not in VARIANTS:
        raise SystemExit(f"unknown build variant {variant!r}; expected one of {VARIANTS}")
    source = _variant_source(variant)
    if not source.is_file():
        raise SystemExit(f"build variant source missing: {source}")
    shutil.copyfile(source, root / "src" / "realm_backend" / "core" / "build_variant.py")
    print(f"   🎚️  build variant: {variant}")


def verify_build_variant(wasm_path: Path, variant: str) -> None:
    """Fail the build unless the artifact matches the variant we asked for.

    A production WASM containing the sentinel means the swap silently did not
    happen — exactly the failure this whole mechanism exists to prevent, so it
    must break the build rather than warn.
    """
    if not wasm_path.is_file():
        raise SystemExit(f"cannot verify build variant: no WASM at {wasm_path}")
    found = TEST_BUILD_SENTINEL in wasm_path.read_bytes()
    if variant == "production" and found:
        raise SystemExit(
            f"production build contains the test sentinel "
            f"{TEST_BUILD_SENTINEL.decode()} — refusing to ship it ({wasm_path})"
        )
    if variant == "test" and not found:
        raise SystemExit(
            f"test build is missing the test sentinel "
            f"{TEST_BUILD_SENTINEL.decode()} — the variant swap did not take effect"
        )
    print(f"   ✅ verified {variant} WASM ({wasm_path.name})")


def _assert_required_exports(did_path: Path) -> None:
    if not did_path.is_file():
        raise SystemExit(
            f"realm_backend pack did not write candid at {did_path}; "
            f"required exports {REQUIRED_UPDATE_EXPORTS}"
        )
    text = did_path.read_text()
    missing = [name for name in REQUIRED_UPDATE_EXPORTS if f'"{name}"' not in text]
    if missing:
        raise SystemExit(
            f"realm_backend pack dropped required update exports: {missing}"
        )


def pack_realm_backend(
    repo_root: Optional[Path] = None, variant: str = DEFAULT_VARIANT
) -> int:
    """Pack ``src/realm_backend/main.py`` with the pinned Cedar template."""
    root = repo_root or _SCRIPTS.parent
    main_py = root / "src" / "realm_backend" / "main.py"
    if not main_py.is_file():
        raise SystemExit(f"realm_backend main.py not found at {main_py}")

    select_build_variant(root, variant)
    try:
        env = apply_cedar_template_env()
        did = root / "src" / "realm_backend" / "realm_backend.did"
        env.setdefault("CANISTER_CANDID_PATH", str(did))
        cmd = [sys.executable, "-m", "basilisk", "realm_backend", str(main_py)]
        print(f"   🐍 {' '.join(cmd)}")
        print(f"   🌲 template: {env['BASILISK_TEMPLATE_WASM']}")
        result = subprocess.run(cmd, cwd=str(root), env=env)
        if result.returncode != 0:
            return result.returncode
        _assert_required_exports(Path(env["CANISTER_CANDID_PATH"]))
        verify_build_variant(
            root / ".basilisk" / "realm_backend" / "realm_backend.wasm", variant
        )
    finally:
        # Leave the checkout on production so a later plain `dfx deploy`, or a
        # developer reading the file, never finds a test build staged.
        select_build_variant(root, DEFAULT_VARIANT)
    return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant",
        choices=VARIANTS,
        default=DEFAULT_VARIANT,
        help="build variant to compile in (default: production)",
    )
    args = parser.parse_args()
    return pack_realm_backend(variant=args.variant)


if __name__ == "__main__":
    sys.exit(main())
