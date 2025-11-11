#!/usr/bin/env python3
"""Integration test for download_file function with real file download and checksum verification."""

import subprocess
import json
import time
import sys


def test_download_file_with_checksum_verification():
    """
    Integration test: Download a real file from GitHub and verify its checksum.
    
    This test:
    1. Calls the download_file canister method via dfx
    2. Downloads: https://raw.githubusercontent.com/smart-social-contracts/realms/dd22e5523f84acf72ad875c34aaef52ef644d646/canister_ids.json
    3. Verifies SHA256 checksum: 1585029aba1ad0fd473a523c46664323bf68cdf0b65c082ae4130fe9dc772964
    4. Checks that the file is saved to the specified Codex
    """
    
    print("=" * 80)
    print("Testing download_file with checksum verification")
    print("=" * 80)
    
    # Test parameters
    url = "https://raw.githubusercontent.com/smart-social-contracts/realms/dd22e5523f84acf72ad875c34aaef52ef644d646/canister_ids.json"
    checksum = "sha256:1585029aba1ad0fd473a523c46664323bf68cdf0b65c082ae4130fe9dc772964"
    codex_name = "test_downloaded_canister_ids"
    
    print(f"\n📥 Downloading: {url}")
    print(f"📋 Expected checksum: {checksum}")
    print(f"💾 Target Codex: {codex_name}")
    
    try:
        # Call download_file via dfx
        print("\n🔧 Calling download_file via dfx...")
        cmd = [
            "dfx", "canister", "call", "realm_backend", "download_file",
            f'("{url}", "{codex_name}", null, opt "{checksum}")'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        
        # Parse the response
        output = result.stdout.strip()
        print(f"\n📤 Raw response: {output}")
        
        # Extract JSON from Candid format: ("json_string")
        if output.startswith('(') and output.endswith(')'):
            inner = output[1:-1].strip()
            if inner.endswith(','):
                inner = inner[:-1].strip()
            if inner.startswith('"') and inner.endswith('"'):
                json_str = inner[1:-1]
                # Unescape the JSON
                json_str = json_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                data = json.loads(json_str)
                
                print(f"\n✅ Parsed response:")
                print(json.dumps(data, indent=2))
                
                # Verify the response
                assert data['success'] is True, f"Download failed: {data.get('error', 'Unknown error')}"
                assert data['url'] == url, f"URL mismatch: {data['url']} != {url}"
                assert data['codex_name'] == codex_name, f"Codex name mismatch: {data['codex_name']} != {codex_name}"
                assert data['checksum'] == checksum, f"Checksum not in response"
                assert 'task_id' in data, "task_id not in response"
                
                print(f"\n✅ Download task created successfully!")
                print(f"   Task ID: {data['task_id']}")
                print(f"   Task Name: {data['task_name']}")
                
                # Wait for the task to complete
                print(f"\n⏳ Waiting 15 seconds for task to complete...")
                time.sleep(15)
                
                # Verify the file was downloaded and saved to Codex
                print(f"\n🔍 Verifying Codex '{codex_name}' was created...")
                verify_cmd = [
                    "dfx", "canister", "call", "realm_backend", "execute_code",
                    f'''("
from ggg import Codex

codex = Codex['{codex_name}']
if codex:
    ic.print(f'✅ Codex found: {{codex.name}}')
    ic.print(f'Content length: {{len(codex.code)}} bytes')
    ic.print(f'First 100 chars: {{codex.code[:100]}}')
else:
    ic.print('❌ Codex not found!')
")'''
                ]
                
                verify_result = subprocess.run(
                    verify_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True
                )
                
                print(f"\n📋 Verification output:")
                print(verify_result.stdout)
                
                # Check if verification was successful
                if "✅ Codex found" in verify_result.stdout:
                    print(f"\n🎉 TEST PASSED: File downloaded, checksum verified, and saved to Codex!")
                    return True
                else:
                    print(f"\n❌ TEST FAILED: Codex was not created")
                    return False
        
        else:
            print(f"❌ Unexpected response format: {output}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n❌ TEST FAILED: Command timed out")
        return False
    except subprocess.CalledProcessError as e:
        print(f"\n❌ TEST FAILED: dfx command failed")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_download_file_with_checksum_verification()
    sys.exit(0 if success else 1)
