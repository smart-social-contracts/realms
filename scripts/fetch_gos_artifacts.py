#!/usr/bin/env python3
"""Download prebuilt GaaS (gos-as-a-service) release artifacts.

WASMs land in .external-wasms/; frontend tarballs are extracted to
.external-assets/<name>/dist/.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

GOS_RELEASE = "v0.2.1"

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_WASMS = REPO_ROOT / ".external-wasms"

WASM_ARTIFACTS = (
    "realm_registry_backend.wasm.gz",
    "realm_installer.wasm.gz",
    "file_registry.wasm.gz",
)
FRONTEND_TARBALLS = {
    "realm_registry_frontend": "realm_registry_frontend.tar.gz",
    "file_registry_frontend": "file_registry_frontend.tar.gz",
}


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  • {url}")
    print(f"    → {dest}")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"ERROR: failed to download {url}\n"
            f"  HTTP {exc.code}: {exc.reason}\n"
            f"  The gos-as-a-service release may not be published yet."
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"ERROR: failed to download {url}\n"
            f"  {exc.reason}\n"
            f"  Check network connectivity and the release tag."
        ) from exc
    dest.write_bytes(data)
    print(f"    fetched {dest.stat().st_size:,} bytes")


def _extract_frontend_tarball(tarball_name: str, dist_dir: Path, base_url: str) -> None:
    tarball_path = REPO_ROOT / ".external-assets" / tarball_name
    _download(f"{base_url}/{tarball_name}", tarball_path)

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tarball_path, "r:gz") as tar:
        tar.extractall(path=dist_dir.parent / "_extract")
        extract_root = dist_dir.parent / "_extract"
        inner_dist = extract_root / "dist"
        if inner_dist.is_dir():
            shutil.move(str(inner_dist), str(dist_dir))
        else:
            for entry in extract_root.iterdir():
                dest = dist_dir / entry.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(entry), str(dest))
        shutil.rmtree(extract_root, ignore_errors=True)

    tarball_path.unlink(missing_ok=True)
    if not dist_dir.is_dir() or not any(dist_dir.iterdir()):
        raise SystemExit(
            f"ERROR: {tarball_name} did not produce a non-empty {dist_dir}"
        )
    print(f"  ✓ {dist_dir.relative_to(REPO_ROOT)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        default=GOS_RELEASE,
        help=f"gos-as-a-service release tag (default: {GOS_RELEASE})",
    )
    parser.add_argument(
        "--what",
        choices=("all", "wasms", "frontend"),
        default="all",
        help="Which artifacts to fetch (default: all)",
    )
    args = parser.parse_args(argv)

    release = args.release
    base_url = f"https://github.com/smart-social-contracts/gos-as-a-service/releases/download/{release}"

    print(f"Fetching gos-as-a-service artifacts ({release}, what={args.what})")

    if args.what in ("all", "wasms"):
        print("\nWASMs:")
        for name in WASM_ARTIFACTS:
            dest = EXTERNAL_WASMS / name
            _download(f"{base_url}/{name}", dest)
            print(f"  ✓ {dest.relative_to(REPO_ROOT)}")

    if args.what in ("all", "frontend"):
        print("\nFrontends:")
        for frontend_name, tarball_name in FRONTEND_TARBALLS.items():
            dist_dir = REPO_ROOT / ".external-assets" / frontend_name / "dist"
            _extract_frontend_tarball(tarball_name, dist_dir, base_url)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
