#!/usr/bin/env python3
"""
Test script to verify simplified data structure works with dfx canister calls
"""

import json
import subprocess
import sys
from pathlib import Path

def test_data_structure():
    """Test that simplified data can be properly formatted for dfx calls"""
    
    # Load the simplified data
    data_file = Path(__file__).parent / "realm_data.json"
    with open(data_file, 'r') as f:
        realm_data = json.load(f)
    
    # Test instruments (previously had metadata field)
    instruments = realm_data.get('instruments', [])
    print(f"Testing {len(instruments)} instruments...")
    
    for i, instrument in enumerate(instruments[:2]):  # Test first 2
        print(f"\nInstrument {i+1}: {instrument}")
        
        # Create the args structure that would be passed to dfx
        args = {
            "entity_type": "instruments",
            "data": [instrument]
        }
        
        # Convert to JSON and escape for dfx command
        args_json = json.dumps(args)
        escaped_args = args_json.replace('"', '\\"')
        
        print(f"JSON args: {args_json}")
        print(f"Escaped args: {escaped_args}")
        
        # Simulate the dfx command structure
        dfx_args = f'(record {{ extension_name = "admin_dashboard"; function_name = "import_data"; args = "{escaped_args}"; }})'
        print(f"DFX args: {dfx_args}")
        
        # Verify no nested JSON strings exist
        if 'metadata' in instrument:
            print("❌ ERROR: Found metadata field that should have been removed!")
            return False
        else:
            print("✅ No problematic metadata field found")
    
    # Test disputes (previously had metadata field)
    disputes = realm_data.get('disputes', [])
    print(f"\nTesting {len(disputes)} disputes...")
    
    for i, dispute in enumerate(disputes):
        print(f"\nDispute {i+1}: {dispute}")
        
        if 'metadata' in dispute:
            print("❌ ERROR: Found metadata field that should have been removed!")
            return False
        else:
            print("✅ No problematic metadata field found")
    
    # Test mandates (previously had metadata field)
    mandates = realm_data.get('mandates', [])
    print(f"\nTesting {len(mandates)} mandates...")
    
    for i, mandate in enumerate(mandates[:2]):  # Test first 2
        print(f"\nMandate {i+1}: {mandate}")
        
        if 'metadata' in mandate:
            print("❌ ERROR: Found metadata field that should have been removed!")
            return False
        else:
            print("✅ No problematic metadata field found")
    
    print("\n🎉 All tests passed! Simplified data structure is ready for import.")
    return True

if __name__ == "__main__":
    success = test_data_structure()
    sys.exit(0 if success else 1)
