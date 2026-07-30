#!/usr/bin/env python3
"""Generate the realm's Cedar schema from the ggg entity definitions.

Cedar validates policies against a schema, so that schema has to describe the
entities the ORM actually stores. Hand-writing it would mean a renamed field
silently turns a policy condition into a type error discovered at decision time
— which is to say, in production, on a denial. Deriving it from
``build_schema()`` makes that a build failure instead.

The generated file is committed so it is reviewable in diffs: a change to an
entity that widens what policies can see should be visible in a pull request,
not conjured at deploy time.

Two modes:

  --check   CI. Fails if the committed schema differs from what the current
            entity definitions produce, or if Cedar would reject it.
  --write   Regenerate the committed schema.

Choices that are not inferred, because they are authorization decisions rather
than data-model facts, are MEMBERSHIPS and ACTIONS below.
"""

import argparse
import difflib
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "src", "realm_backend")
SCHEMA_PATH = os.path.join(BACKEND_DIR, "core", "cedar", "realm.cedarschema")

NAMESPACE = "Realm"

# Users authenticate; everything else is a resource.
PRINCIPAL_TYPE = "User"

# Which relations become Cedar's `in` hierarchy. These are the two the realm's
# Python checks already treat as membership:
#
#   departments -> `principal in resource.department`, replacing
#                  user_in_department()
#   profiles    -> `principal in Realm::UserProfile::"admin"`, replacing
#                  is_realm_admin() and the @require(Operations.X) decorators
#
# Nothing else is a parent. Making every foreign key a parent would put
# unrelated entities in each other's ancestor sets, and `in` would start
# succeeding for reasons nobody intended.
MEMBERSHIPS = {
    "User": ["departments", "profiles"],
}

# The generic verb surface from #280. Named actions are for the verbs that do
# more than read or write; the rest get added as those verbs are ported.
ACTIONS = {
    "entity.get": "read",
    "entity.list": "read",
    "entity.create": "write",
    "entity.update": "write",
    "entity.delete": "write",
    # Named because a guardrail has to refer to it specifically: deciding an
    # appeal is the one action an appellant must never take on their own appeal.
    "appeal.decide": "write",
}

# Facts about the request rather than the data. `extension` is what lets a
# guardrail distinguish a call originating inside a sandboxed extension from
# one made by host code — the host already knows this, and threads it through
# `make_rpc_handler(ext_id, ...)`. Without it, no policy could tell the two
# apart, since both arrive as the same principal.
CONTEXT = {
    "extension": "String",
}


def build() -> tuple:
    """Generate the schema text from the current entity definitions."""
    sys.path.insert(0, BACKEND_DIR)

    import ggg
    from ic_python_db.schema import build_schema

    try:
        from ic_basilisk_toolkit.cedar_schema import generate_cedar_schema
    except ImportError as exc:
        raise SystemExit(
            "ic_basilisk_toolkit.cedar_schema is unavailable. It is newer than "
            "the pinned ic-basilisk-toolkit in requirements.txt; bump that pin "
            "once the toolkit release containing it is published.\n"
            f"  underlying error: {exc}"
        ) from exc

    entity_types = {
        name: getattr(ggg, name)
        for name in ggg.__all__
        if isinstance(getattr(ggg, name, None), type)
    }
    schema = build_schema(entity_types)
    return generate_cedar_schema(
        schema,
        namespace=NAMESPACE,
        principal_type=PRINCIPAL_TYPE,
        memberships=MEMBERSHIPS,
        actions=ACTIONS,
        context=CONTEXT,
    )


def read_committed() -> str:
    if not os.path.exists(SCHEMA_PATH):
        return ""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return f.read()


def cmd_write() -> int:
    text, report = build()
    os.makedirs(os.path.dirname(SCHEMA_PATH), exist_ok=True)
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {os.path.relpath(SCHEMA_PATH, REPO_ROOT)}")
    print(report.summary())
    return 0


def cmd_check() -> int:
    text, report = build()
    committed = read_committed()
    if committed == text:
        print(f"schema is current: {report.entities} entity types, "
              f"{report.attributes} attributes")
        return 0

    print("Cedar schema is stale — entity definitions have changed.\n")
    diff = difflib.unified_diff(
        committed.splitlines(keepends=True),
        text.splitlines(keepends=True),
        fromfile="committed",
        tofile="generated",
    )
    sys.stdout.writelines(diff)
    print("\nRun: python scripts/generate_cedar_schema.py --write")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="fail if stale (CI)")
    group.add_argument("--write", action="store_true", help="regenerate")
    args = parser.parse_args()
    return cmd_check() if args.check else cmd_write()


if __name__ == "__main__":
    sys.exit(main())
