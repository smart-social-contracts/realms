#!/usr/bin/env python3
"""Ratchet on which non-core extensions may still run in-process.

Sandboxed extensions run as pure compute over their JSON args: a subinterpreter
has no ``ggg``, ``core`` or ``basilisk``. An extension importing any of them
cannot spawn, and since the in-process fallback was removed that is a hard
failure at call time rather than a silent downgrade to full privilege.

So ``"runtime": "in_process"`` does not *grant* privilege — it documents that
the extension still needs it. ``sandbox_exemptions.json`` pins the set that
does. The point of pinning it is direction: the list may shrink, never grow.
Left unpinned, "just declare in_process" is the path of least resistance and
the trusted set quietly grows forever.

Two modes:

  --check   CI. Fails on a new exemption, an undeclared host-importing
            extension, or a stale entry that has already been ported.
  --write   Stamp ``"runtime": "in_process"`` on manifests that need it.

Core/system extensions are skipped throughout: they are never sandboxed
regardless of what their manifest says.
"""

import argparse
import json
import os
import re
import sys

HOST_IMPORT = re.compile(r"^\s*(?:from|import)\s+(ggg|core|basilisk|_cdk)\b", re.M)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_PATH = os.path.join(REPO_ROOT, "scripts", "sandbox_exemptions.json")
DEFAULT_EXTENSIONS_DIR = os.path.join(REPO_ROOT, "extensions", "extensions")


def load_core_ids(repo_root=REPO_ROOT):
    with open(os.path.join(repo_root, "core-extensions.json")) as f:
        return set(json.load(f).get("core_extensions") or ())


def load_baseline(path=BASELINE_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["exempt"]


def host_imports(ext_dir):
    """Host roots (ggg/core/basilisk/_cdk) imported by an extension's backend."""
    roots = set()
    backend = os.path.join(ext_dir, "backend")
    if not os.path.isdir(backend):
        return roots
    for dirpath, _, filenames in os.walk(backend):
        for name in filenames:
            if not name.endswith(".py"):
                continue
            with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                roots.update(HOST_IMPORT.findall(f.read()))
    return roots


def survey(extensions_dir=DEFAULT_EXTENSIONS_DIR, repo_root=REPO_ROOT):
    """{ext_id: {"imports": set, "declared": bool}} for every non-core extension."""
    core_ids = load_core_ids(repo_root)
    result = {}
    for ext_id in sorted(os.listdir(extensions_dir)):
        ext_dir = os.path.join(extensions_dir, ext_id)
        manifest_path = os.path.join(ext_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        if ext_id in core_ids or manifest.get("system"):
            continue
        result[ext_id] = {
            "imports": host_imports(ext_dir),
            "declared": manifest.get("runtime") == "in_process",
        }
    return result


def check(extensions_dir=DEFAULT_EXTENSIONS_DIR, repo_root=REPO_ROOT,
          baseline_path=BASELINE_PATH):
    """Ratchet violations as a list of human-readable strings (empty == pass)."""
    baseline = load_baseline(baseline_path)
    state = survey(extensions_dir, repo_root)
    problems = []

    for ext_id, info in sorted(state.items()):
        if ext_id in baseline:
            continue
        if info["declared"]:
            problems.append(
                f"{ext_id}: declares \"runtime\": \"in_process\" but is not in the "
                f"exemption baseline. The list only shrinks — write it "
                f"sandbox-clean instead of adding an exemption."
            )
        elif info["imports"]:
            problems.append(
                f"{ext_id}: imports host modules ({', '.join(sorted(info['imports']))}) "
                f"without an exemption, so it will fail at call time once "
                f"sandboxed. Use the capability bridge instead."
            )

    for ext_id in sorted(baseline):
        if ext_id not in state:
            problems.append(
                f"{ext_id}: in the exemption baseline but no longer a non-core "
                f"extension. Remove the stale entry."
            )
        elif not state[ext_id]["imports"]:
            problems.append(
                f"{ext_id}: no longer imports host modules — it has been ported. "
                f"Drop \"runtime\": \"in_process\" from its manifest and delete it "
                f"from the baseline so the ratchet records the progress."
            )

    return problems


def write(extensions_dir=DEFAULT_EXTENSIONS_DIR, repo_root=REPO_ROOT):
    """Stamp "runtime": "in_process" where it is needed but missing."""
    changed = []
    for ext_id, info in sorted(survey(extensions_dir, repo_root).items()):
        if not info["imports"] or info["declared"]:
            continue
        manifest_path = os.path.join(extensions_dir, ext_id, "manifest.json")
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        # Keep "runtime" next to "system"/"version" rather than appended last,
        # so the execution mode is visible at the top of the manifest.
        rebuilt, inserted = {}, False
        for key, value in manifest.items():
            rebuilt[key] = value
            if key == "version" and not inserted:
                rebuilt["runtime"] = "in_process"
                inserted = True
        if not inserted:
            rebuilt["runtime"] = "in_process"

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(rebuilt, f, indent=2, ensure_ascii=False)
            f.write("\n")
        changed.append(ext_id)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extensions_dir", nargs="?", default=DEFAULT_EXTENSIONS_DIR)
    parser.add_argument("--repo-root", default=REPO_ROOT)
    parser.add_argument("--check", action="store_true",
                        help="CI mode: enforce the ratchet, write nothing")
    parser.add_argument("--write", action="store_true",
                        help="stamp in_process on manifests that need it")
    args = parser.parse_args()

    state = survey(args.extensions_dir, args.repo_root)
    exempt = sorted(e for e, i in state.items() if i["imports"])
    clean = sorted(e for e, i in state.items() if not i["imports"])

    if args.write:
        changed = write(args.extensions_dir, args.repo_root)
        print(f"stamped in_process ({len(changed)}): {', '.join(changed) or '-'}")

    print(f"still in-process ({len(exempt)}): {', '.join(exempt) or '-'}")
    print(f"sandbox-clean ({len(clean)}): {', '.join(clean) or '-'}")

    if args.check:
        problems = check(args.extensions_dir, args.repo_root)
        if problems:
            print("\nratchet violations:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"\nratchet OK — {len(exempt)} non-core extensions left to port")
    return 0


if __name__ == "__main__":
    sys.exit(main())
