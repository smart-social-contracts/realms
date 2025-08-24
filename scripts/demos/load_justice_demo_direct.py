#!/usr/bin/env python3
"""
Direct demo case loading script for Justice Litigation extension
Generates demo cases and loads them via the extension API
"""

import json
import subprocess
import sys

def generate_demo_cases():
    """Generate demo litigation cases using the demo_loader"""
    try:
        # Call the demo_loader to generate cases
        result = subprocess.run([
            'dfx', 'canister', 'call', 'realm_backend', 'extension_sync_call',
            '(record { extension_name = "demo_loader"; function_name = "load"; args = "{\\"step\\": \\"justice_litigation\\"}"; })'
        ], capture_output=True, text=True, cwd='/home/user/dev/smartsocialcontracts/realms3')
        
        if result.returncode != 0:
            print(f"Error generating demo cases: {result.stderr}")
            return None
            
        # Parse the response to extract the generated cases
        output = result.stdout
        print("Demo loader response received")
        
        # The demo_loader should have populated the cases directly
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_justice_litigation():
    """Test if the justice litigation extension has cases"""
    try:
        result = subprocess.run([
            'dfx', 'canister', 'call', 'realm_backend', 'extension_sync_call',
            '(record { extension_name = "justice_litigation"; function_name = "get_litigations"; args = "{\\"user_principal\\": \\"x774o-sglch-yuvk4-edntl-sczy4-7igsw-qtx7l-jrior-j2xhw-abvda-lae\\", \\"user_profile\\": \\"admin\\"}"; })'
        ], capture_output=True, text=True, cwd='/home/user/dev/smartsocialcontracts/realms3')
        
        if result.returncode != 0:
            print(f"Error testing justice litigation: {result.stderr}")
            return False
            
        output = result.stdout
        print("Justice litigation test response:")
        print(output)
        
        # Check if we have cases
        if '"total_count": 0' in output or '"litigations": []' in output:
            print("❌ No cases found in justice litigation extension")
            return False
        else:
            print("✅ Cases found in justice litigation extension")
            return True
            
    except Exception as e:
        print(f"Error testing: {e}")
        return False

def main():
    print("🔄 Loading Justice Litigation demo data...")
    
    # Generate demo cases
    if generate_demo_cases():
        print("✅ Demo cases generated successfully")
        
        # Test if cases are accessible
        if test_justice_litigation():
            print("🎉 Justice Litigation extension successfully populated with demo data!")
        else:
            print("⚠️  Demo cases generated but not accessible via extension API")
    else:
        print("❌ Failed to generate demo cases")

if __name__ == "__main__":
    main()
