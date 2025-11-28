#!/usr/bin/env python3
import argparse
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", default="local")
    network = parser.parse_args().network
    
    canisters = ["realm_registry_backend", "realm1_backend", "realm2_backend", "realm3_backend", "realm_registry_frontend", "realm1_frontend", "realm2_frontend", "realm3_frontend"]
    if network == "local":
        canisters.append("internet_identity")
    
    print(f"🔍 Verifying {network} deployment:")
    success = True
    
    for canister in canisters:
        cmd = ["dfx", "canister", "status", canister]
        if network != "local":
            cmd.extend(["--network", network])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and "Status: Running" in result.stdout:
            print(f"✅ {canister}")
        else:
            print(f"❌ {canister}")
            success = False
    
    print("🎉 Success!" if success else "💥 Failed!")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
