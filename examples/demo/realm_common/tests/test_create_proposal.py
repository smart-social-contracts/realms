#!/usr/bin/env python3
"""
Test proposal creation flow on staging.

Usage:
    python examples/demo/realm_common/tests/test_create_proposal.py

    (Run from realms root directory or set REALM_DIR!)

Prerequisites:
    - dfx configured with staging network
    - realm_backend deployed on staging
"""

import json
import os
import sys
import uuid

# Add tests directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Determine working directory: use REALM_DIR env var, or current directory if it has dfx.json
REALM_DIR = os.environ.get("REALM_DIR", os.getcwd())
if not os.path.exists(os.path.join(REALM_DIR, "dfx.json")):
    # Fallback: check if we're in a realm subdirectory
    if os.path.exists("dfx.json"):
        REALM_DIR = os.getcwd()
    else:
        print("ERROR: Must run from a realm directory with dfx.json or set REALM_DIR")
        sys.exit(1)
os.chdir(REALM_DIR)
print(f"Working directory: {REALM_DIR}")

from test_utils import (
    get_canister_id,
    get_current_principal,
    print_error,
    print_ok,
    run_command,
)


def execute_on_canister(code: str) -> dict:
    """Execute Python code on realm_backend canister."""
    # Use semicolons for one-liner to avoid newline escaping issues
    one_liner = code.strip().replace("\n", "; ")
    escaped = one_liner.replace("\\", "\\\\").replace('"', '\\"')
    cmd = f"dfx canister call realm_backend execute_code_shell '(\"{escaped}\")'"
    result = run_command(cmd)
    if not result:
        return {}
    try:
        # Parse the Candid response - extract the JSON part
        # Response format: ("{ ... }")
        if '"{' in result:
            start = result.find('"{') + 1
            end = result.rfind('}"') + 1
            json_str = result[start:end].replace('\\"', '"').replace("\\n", "\n")
            return json.loads(json_str)
        return {"raw": result}
    except Exception as e:
        return {"raw": result, "parse_error": str(e)}


def test_create_proposal():
    """Test: Create a proposal on staging realm."""
    print("\n" + "=" * 60)
    print("TEST: Create Proposal Flow")
    print("=" * 60)

    # Get canister ID
    backend_id = get_canister_id("realm_backend")
    if not backend_id:
        print_error("Missing realm_backend canister ID")
        return False

    print(f"Backend: {backend_id}")

    # Get current principal for the proposer
    principal = get_current_principal()
    if not principal:
        print_error("Failed to get current principal")
        return False
    print(f"Proposer principal: {principal}")

    # Step 1: Create a proposal
    print("\n--- Step 1: Create Proposal ---")
    proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
    proposal_title = "Test Proposal from CI"
    proposal_description = "Automated test proposal created during staging post-deployment test"
    
    # Use proposal_id field (not id) as per Proposal entity definition
    create_code = f'''
from ggg import Proposal
prop = Proposal(proposal_id="{proposal_id}", title="{proposal_title}", description="{proposal_description}", status="Active")
print(prop.proposal_id)
'''
    result = execute_on_canister(create_code)
    raw = result.get("raw", "")
    print(f"Result: {raw}")
    
    if proposal_id in raw:
        print_ok(f"✅ Proposal {proposal_id} created successfully!")
        return True
    else:
        print_error(f"❌ Failed to create proposal: {result}")
        return False


if __name__ == "__main__":
    import sys

    sys.exit(0 if test_create_proposal() else 1)
