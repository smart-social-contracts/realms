#!/usr/bin/env python3
"""Verify a built realm_frontend dist matches the expected build variant.

Scans asset files for the test-only sentinel ``REALMS_TEST_BUILD_AUTH_BYPASS``.
Production builds must not contain it; test builds must.

The sentinel is not a free-floating constant. It is read inside
``_createTestIdentity`` (``src/lib/auth.js``), the single entry point to every
deterministic-identity login, so it reaches the bundle exactly when that code
path does. A sentinel that were merely exported and never used would be
tree-shaken out of *both* variants, and the production check would then pass
without proving anything.

That is also why both directions matter. Absence in a production build is only
evidence that the gating worked if the same mechanism is known to produce the
sentinel when it is supposed to. ``publish_build.py`` runs this check on every
realm frontend it builds, tagged with the variant it asked for, so the test
direction is exercised whenever a test-variant realm is published.

Usage:
    python3 scripts/check_frontend_variant.py <dist_dir> production
    python3 scripts/check_frontend_variant.py <dist_dir> test
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEST_BUILD_SENTINEL = b"REALMS_TEST_BUILD_AUTH_BYPASS"
VARIANTS = ("production", "test")

# Extensions worth scanning (skip images, wasm, etc.).
TEXT_SUFFIXES = {
    ".js",
    ".mjs",
    ".cjs",
    ".html",
    ".css",
    ".json",
    ".map",
    ".txt",
    ".svg",
}


def _iter_text_files(dist_dir: Path):
    for path in sorted(dist_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def sentinel_present(dist_dir: Path) -> tuple[bool, Path | None]:
    for path in _iter_text_files(dist_dir):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if TEST_BUILD_SENTINEL in data:
            return True, path
    return False, None


def verify_frontend_variant(dist_dir: Path, variant: str) -> None:
    if variant not in VARIANTS:
        raise SystemExit(f"unsupported variant '{variant}' (expected: {', '.join(VARIANTS)})")
    if not dist_dir.is_dir():
        raise SystemExit(f"dist directory not found: {dist_dir}")

    found, hit = sentinel_present(dist_dir)
    sentinel = TEST_BUILD_SENTINEL.decode()

    if variant == "production" and found:
        raise SystemExit(
            f"production frontend contains the test sentinel {sentinel} "
            f"({hit.relative_to(dist_dir) if hit else '?'}) — refusing to ship it"
        )
    if variant == "test" and not found:
        raise SystemExit(
            f"test frontend is missing the test sentinel {sentinel} "
            f"— the variant build did not take effect ({dist_dir})"
        )
    print(f"verified {variant} frontend dist ({dist_dir})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path, help="path to realm_frontend dist/")
    parser.add_argument("variant", choices=VARIANTS, help="expected build variant")
    args = parser.parse_args(argv)
    verify_frontend_variant(args.dist_dir.resolve(), args.variant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
