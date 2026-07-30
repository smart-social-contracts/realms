#!/usr/bin/env python3
"""Move an extension manifest onto the capability bridge.

Drops ``"runtime": "in_process"``, declares ``ggg_api_version`` and the
capabilities the ported backend actually uses, and bumps the patch version so
the result is publishable. Keeping this in one place means every ported
manifest ends up with the same shape, and the edit is reviewable as a diff
rather than as prose.

    python3 scripts/port_manifest.py llm_chat caller.get time.now log.write
"""

import json
import sys
from pathlib import Path

EXTENSIONS = Path("/srv/dev/realms-extensions/extensions")
# The submodule copy the test suite reads.
MIRROR = Path("/srv/dev/realms/extensions/extensions")

API_VERSION = 1


def bump(version: str) -> str:
    parts = (version or "0.0.0").split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        parts.append("1")
    return ".".join(parts)


def port(ext_id: str, capabilities: list) -> str:
    path = EXTENSIONS / ext_id / "manifest.json"
    manifest = json.loads(path.read_text())

    manifest.pop("runtime", None)
    manifest["ggg_api_version"] = API_VERSION
    manifest["capabilities"] = capabilities
    manifest["version"] = bump(str(manifest.get("version", "0.0.0")))

    # Order the bridge contract up front, where a reviewer will see it.
    front = ["name", "version", "ggg_api_version", "capabilities"]
    ordered = {k: manifest[k] for k in front if k in manifest}
    ordered.update({k: v for k, v in manifest.items() if k not in front})

    text = json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text)

    mirror = MIRROR / ext_id / "manifest.json"
    if mirror.exists():
        mirror.write_text(text)

    return ordered["version"]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ext_id, capabilities = sys.argv[1], sys.argv[2:]
    version = port(ext_id, capabilities)
    print(f"{ext_id}: {version} ({len(capabilities)} capabilities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
