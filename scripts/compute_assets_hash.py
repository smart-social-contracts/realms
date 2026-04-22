#!/usr/bin/env python3
"""Compute and write /.well-known/assets-hash into a frontend dist/ directory.

The assets-hash is a composite SHA-256 of all frontend assets:
  sha256( sorted( (relative_path + sha256(file_content)) for each file ) )

This single hash allows on-chain verification of the entire frontend
deployment without enumerating every file via the asset canister's
list() method (which may exceed the 2MB IC response limit).

Usage:
    python3 scripts/compute_assets_hash.py /path/to/dist

Can also be imported:
    from scripts.compute_assets_hash import compute_and_write_assets_hash
    assets_hash = compute_and_write_assets_hash(Path("dist"))
"""

import hashlib
import json
import sys
from pathlib import Path


def compute_assets_hash(dist_dir: Path) -> str:
    """Compute the composite SHA-256 hash of all files in dist/.

    The hash is computed by:
    1. Listing all files recursively (sorted by relative path)
    2. For each file: compute sha256(content)
    3. Concatenate all (relative_path + file_hash) pairs
    4. Hash the concatenation with SHA-256
    """
    entries = []
    for f in sorted(dist_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(dist_dir))
        # Skip the assets-hash file itself if it exists from a prior run
        if rel == ".well-known/assets-hash":
            continue
        file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        entries.append(f"{rel}{file_hash}")

    composite = "".join(entries)
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


def compute_and_write_assets_hash(dist_dir: Path) -> str:
    """Compute the hash and write it to dist/.well-known/assets-hash.

    Returns the hex digest string.
    """
    assets_hash = compute_assets_hash(dist_dir)

    well_known = dist_dir / ".well-known"
    well_known.mkdir(parents=True, exist_ok=True)

    payload = json.dumps({
        "assets_hash": assets_hash,
        "algorithm": "sha256",
        "method": "sorted_path_concat",
    }, indent=2)

    (well_known / "assets-hash").write_text(payload)
    return assets_hash


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dist-directory>", file=sys.stderr)
        sys.exit(1)

    dist_dir = Path(sys.argv[1])
    if not dist_dir.is_dir():
        print(f"ERROR: {dist_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    assets_hash = compute_and_write_assets_hash(dist_dir)
    print(f"assets_hash: {assets_hash}")
    print(f"Written to: {dist_dir / '.well-known' / 'assets-hash'}")


if __name__ == "__main__":
    main()
