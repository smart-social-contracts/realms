"""Embed the Cedar policy files into Python constants, and check they stay in sync.

Bundled canister modules have no ``__file__``, so the authorizer cannot read
policy text from the filesystem at runtime. String constants survive freezing,
so this script generates ``core/cedar_policies.py`` holding the guardrails and
policies verbatim, and the authorizer imports that instead.

The Cedar schema is generated at runtime from ggg entity definitions (see
``core/cedar_schema_runtime.py``), not embedded here.

The hazard is the two drifting apart: someone edits ``guardrails.cedar`` and the
embedded copy silently keeps the old rules. ``--check`` exists to catch that in
CI, so the embedded copy can never silently lag the source of truth.

    sync_cedar_policies.py --write   # regenerate the embedded module
    sync_cedar_policies.py --check   # fail if it is out of date
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CEDAR_DIR = os.path.join(_HERE, "..", "src", "realm_backend", "core", "cedar")
_OUT = os.path.join(_HERE, "..", "src", "realm_backend", "core", "cedar_policies.py")

_SOURCES = [
    ("GUARDRAILS", "guardrails.cedar"),
    ("POLICIES", "policies.cedar"),
]

_HEADER = '''"""The realm's Cedar policies, embedded as constants.

GENERATED FILE — do not edit. Regenerate with
``scripts/sync_cedar_policies.py --write``; CI checks it is current with
``--check``.

Bundled canister modules have no ``__file__`` and no readable filesystem copy of
these files, so the policy text is carried as data rather than read at runtime.
The ``.cedar`` files remain the source of truth; this module only mirrors them.

The Cedar schema is generated at runtime from ggg entity definitions (see
``core/cedar_schema_runtime.py``), not embedded here.
"""

'''


def render() -> str:
    parts = [_HEADER]
    for name, filename in _SOURCES:
        path = os.path.join(_CEDAR_DIR, filename)
        with open(path) as fh:
            text = fh.read()
        parts.append(f"# --- {filename} ---\n{name} = {text!r}\n\n")
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render()

    if args.write:
        with open(_OUT, "w") as fh:
            fh.write(rendered)
        print(f"wrote {os.path.relpath(_OUT)}")
        return 0

    try:
        with open(_OUT) as fh:
            current = fh.read()
    except OSError:
        print(f"FAIL: {os.path.relpath(_OUT)} is missing; run --write", file=sys.stderr)
        return 1

    if current != rendered:
        print(
            f"FAIL: {os.path.relpath(_OUT)} is stale; run "
            "scripts/sync_cedar_policies.py --write",
            file=sys.stderr,
        )
        return 1
    print("embedded Cedar policies are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
