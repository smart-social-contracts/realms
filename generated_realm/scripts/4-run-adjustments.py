#!/usr/bin/env python3

import subprocess, os
s = os.path.dirname(os.path.abspath(__file__))

print("🚀 Running adjustments.py...")
v = subprocess.check_output(['dfx', 'canister', 'id', 'vault'], cwd=os.path.dirname(os.path.dirname(s))).decode().strip()
print(f"v: {v}")

print("Replacig vault principal id...")

with open(os.path.join(s, "adjustments.py"), 'r') as f:
	content = f.read().replace('<VAULT_PRINCIPAL_ID>', v)
with open(os.path.join(s, "adjustments.py"), 'w') as f:
	f.write(content)

print(f"✅ Replaced with: {v}")

# Run the adjustments script
subprocess.run(['realms', 'shell', '--file', 'generated_realm/scripts/adjustments.py'], cwd=os.path.dirname(os.path.dirname(s)))