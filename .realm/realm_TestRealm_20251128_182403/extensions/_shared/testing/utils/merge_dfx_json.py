#!/usr/bin/env python3
"""
Merge extension test canisters into realm dfx.json.

This script allows extensions to define their own test canisters (e.g., ICRC ledgers,
custom indexers) and merge them into the main realm dfx.json for unified deployment.
"""

import json
import sys
from pathlib import Path


def merge_dfx_json(test_dfx_path: str, realm_dfx_path: str) -> bool:
    """
    Merge test canisters into realm dfx.json.

    Args:
        test_dfx_path: Path to extension's tests/dfx.json
        realm_dfx_path: Path to realm dfx.json (e.g., .realms/dfx.json)

    Returns:
        True if changes were made, False otherwise
    """
    test_dfx_file = Path(test_dfx_path)
    realm_dfx_file = Path(realm_dfx_path)

    if not test_dfx_file.exists():
        print(f"❌ Test dfx.json not found: {test_dfx_path}", file=sys.stderr)
        return False

    if not realm_dfx_file.exists():
        print(f"❌ Realm dfx.json not found: {realm_dfx_path}", file=sys.stderr)
        return False

    # Read both dfx.json files
    with open(test_dfx_file) as f:
        test_dfx = json.load(f)

    with open(realm_dfx_file) as f:
        realm_dfx = json.load(f)

    # Compute the path prefix based on where test_dfx is located
    test_dir = test_dfx_file.parent
    path_prefix = str(test_dir) + "/"

    # Track if we made any changes
    changes_made = False

    # Add test canisters to realm dfx.json
    for canister_name, canister_config in test_dfx.get("canisters", {}).items():
        if canister_name not in realm_dfx["canisters"]:
            # Adjust path for wasm and candid files to be relative to realm directory
            adjusted_config = canister_config.copy()

            if "wasm" in adjusted_config:
                adjusted_config["wasm"] = path_prefix + adjusted_config["wasm"]

            if "candid" in adjusted_config:
                adjusted_config["candid"] = path_prefix + adjusted_config["candid"]

            realm_dfx["canisters"][canister_name] = adjusted_config
            print(f"✅ Added {canister_name} to unified dfx.json")
            changes_made = True
        else:
            print(f"ℹ️  {canister_name} already exists in dfx.json, skipping")

    # Write back the unified dfx.json if changes were made
    if changes_made:
        with open(realm_dfx_file, "w") as f:
            json.dump(realm_dfx, f, indent=2)
        print("\n✅ dfx.json files unified successfully")
    else:
        print("\nℹ️  No changes needed - test canisters already in dfx.json")
        return True

    return changes_made


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: merge_dfx_json.py <test_dfx_path> <realm_dfx_path>")
        print("Example: merge_dfx_json.py ../tests/dfx.json dfx.json")
        sys.exit(1)

    test_path = sys.argv[1]
    realm_path = sys.argv[2]

    success = merge_dfx_json(test_path, realm_path)
    sys.exit(0 if success else 1)
