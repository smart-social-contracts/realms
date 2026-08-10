#!/usr/bin/env bash
# Deploy a fresh RealmsGOS Casals instance (backend+frontend), seed multisig,
# adopt shared infra. Usage: ./deploy_env_casals.sh test|demo|staging
set -euo pipefail

ENV_NAME="${1:?usage: $0 test|demo|staging}"
IDENTITY="${IDENTITY:-my_dev_identity_1}"
DEPLOYER="${DEPLOYER:-ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae}"
CYCLEOPS="${CYCLEOPS:-cpbhu-5iaaa-aaaad-aalta-cai}"
CASALS_SRC="${CASALS_SRC:-/srv/dev/Casals}"
REALMS_ROOT="${REALMS_ROOT:-/srv/dev/realms}"
CFG="$REALMS_ROOT/casals-config/realmsgos"
ENV_JSON="$CFG/env-services/${ENV_NAME}.json"

if [[ ! -f "$ENV_JSON" ]]; then
  echo "missing $ENV_JSON" >&2
  exit 1
fi

FR=$(python3 -c "import json; print(json.load(open('$ENV_JSON'))['file_registry'])")
FR_FE=$(python3 -c "import json; print(json.load(open('$ENV_JSON'))['file_registry_frontend'])")

export NO_COLOR=1 DFX_WARNING=-mainnet_plaintext_identity
cd "$CASALS_SRC"

echo "==> [$ENV_NAME] backup + empty mapping for fresh create"
cp -a icp.yaml "icp.yaml.bak-realmsgos-$ENV_NAME"
cp -a .icp/data/mappings/ic.ids.json ".icp/data/mappings/ic.ids.json.bak-$ENV_NAME"
echo '{}' > .icp/data/mappings/ic.ids.json

python3 - <<'PY'
import yaml
with open("icp.yaml") as f:
    doc = yaml.safe_load(f)
doc["canisters"] = [c for c in doc["canisters"] if c["name"] in {"casals_backend", "casals_frontend"}]
with open("icp.yaml", "w") as f:
    yaml.safe_dump(doc, f, sort_keys=False)
print("Filtered:", [c["name"] for c in doc["canisters"]])
PY

echo "==> [$ENV_NAME] icp deploy casals_backend + casals_frontend"
icp deploy -e ic --identity "$IDENTITY" --mode install --cycles 5t -y \
  casals_backend casals_frontend

CASALS=$(python3 -c "import json; print(json.load(open('.icp/data/mappings/ic.ids.json'))['casals_backend'])")
CASALS_FE=$(python3 -c "import json; print(json.load(open('.icp/data/mappings/ic.ids.json'))['casals_frontend'])")
echo "Created casals_backend=$CASALS casals_frontend=$CASALS_FE"

echo "==> [$ENV_NAME] restore icp.yaml + previous mapping"
mv "icp.yaml.bak-realmsgos-$ENV_NAME" icp.yaml
mv ".icp/data/mappings/ic.ids.json.bak-$ENV_NAME" .icp/data/mappings/ic.ids.json

echo "==> [$ENV_NAME] top-up treasury 12T + set_settings"
icp canister top-up --amount 12t "$CASALS" -e ic --identity "$IDENTITY"
icp canister call "$CASALS" set_settings \
  "(\"{\\\"file_registry_canister_id\\\":\\\"$FR\\\",\\\"file_registry_frontend_canister_id\\\":\\\"$FR_FE\\\",\\\"create_cycles\\\":2000000000000,\\\"treasury_reserve\\\":3000000000000,\\\"cycles_autopilot\\\":false,\\\"extra_controller_principals\\\":[\\\"$DEPLOYER\\\",\\\"$CYCLEOPS\\\"]}\")" \
  -e ic --identity "$IDENTITY"

echo "==> [$ENV_NAME] seed orchestration templates"
cd /srv/dev/gos-as-a-service
PYTHONPATH=cli python3 - <<PY
from pathlib import Path
from gaas.conductor_seed import seed_orchestration_templates
seed_orchestration_templates(
    "$CASALS",
    "$FR",
    "ic",
    identity="$IDENTITY",
    casals_src=Path("$CASALS_SRC"),
)
print("seeded")
PY
cd "$CASALS_SRC"

echo "==> [$ENV_NAME] set_sheet + deploy_sheet"
python3 - "$CASALS" "$IDENTITY" "$CFG/sheets/infra-shared.json" <<'PY'
import json, subprocess, sys
casals, identity, sheet_path = sys.argv[1], sys.argv[2], sys.argv[3]
sheet = json.load(open(sheet_path))
sheet.pop("$comment", None)
payload = json.dumps(sheet)
escaped = payload.replace("\\", "\\\\").replace('"', '\\"')
arg = f'("{escaped}")'
subprocess.check_call(["icp", "canister", "call", casals, "set_sheet", arg, "-e", "ic", "--identity", identity])
subprocess.check_call(["icp", "canister", "call", casals, "deploy_sheet", '("{}")', "-e", "ic", "--identity", identity])
PY

MSIG=$(python3 - "$CASALS" "$IDENTITY" <<'PY'
import json, re, subprocess, sys
casals, identity = sys.argv[1], sys.argv[2]
raw = subprocess.check_output(
    ["icp", "canister", "call", casals, "get_tree", "()", "-e", "ic", "--identity", identity, "--query"],
    text=True,
)
m = re.search(r'\(\s*"(.*)"\s*,?\s*\)', raw, re.S)
if not m:
    raise SystemExit(f"could not parse get_tree:\n{raw[:500]}")
inner = bytes(m.group(1), "utf-8").decode("unicode_escape")
d = json.loads(inner)
for sec in d["sections"]:
    for st in sec["stands"]:
        if st["name"] == "multisig":
            for c in st["canisters"]:
                if c["name"] == "multisig":
                    print(c["canister_id"])
                    raise SystemExit
raise SystemExit("multisig not found in get_tree")
PY
)
echo "multisig=$MSIG"

echo "==> [$ENV_NAME] configure multisig"
icp canister call "$MSIG" configure \
  "(vec { principal \"$DEPLOYER\" } : vec principal, 1 : nat, 604800 : nat)" \
  -e ic --identity "$IDENTITY"

echo "==> [$ENV_NAME] add controllers on shared canisters"
python3 - <<PY
import json, subprocess
svc = json.load(open("$ENV_JSON"))
ids = [
  svc["token_backend"], svc["token_frontend"],
  svc["nft_backend"], svc["nft_frontend"],
  svc["marketplace_backend"], svc["marketplace_frontend"],
  svc["file_registry"], svc["file_registry_frontend"],
]
for cid in ids:
    for ctrl in ("$CASALS", "$MSIG"):
        subprocess.run(
            ["icp","canister","settings","update",cid,"--add-controller",ctrl,"-e","ic","--identity","$IDENTITY","-f"],
            check=False,
        )
        print(f"added {ctrl} -> {cid}")
PY

echo "==> [$ENV_NAME] persist IDs"
python3 - <<PY
import json
from pathlib import Path
env_path = Path("$ENV_JSON")
d = json.loads(env_path.read_text())
d["casals_backend"] = "$CASALS"
d["casals_frontend"] = "$CASALS_FE"
d["multisig"] = "$MSIG"
env_path.write_text(json.dumps(d, indent=2) + "\n")
ids_path = Path("$CFG/canister_ids.json")
ids = json.loads(ids_path.read_text()) if ids_path.exists() else {}
for k, v in [("casals_backend","$CASALS"),("casals_frontend","$CASALS_FE"),("multisig","$MSIG")]:
    ids.setdefault(k, {})["$ENV_NAME"] = v
ids_path.write_text(json.dumps(ids, indent=2) + "\n")
print(ids_path.read_text())
PY

echo "==> [$ENV_NAME] register shared infra"
python3 "$CFG/scripts/register_shared_infra.py" \
  --casals "$CASALS" --network "$ENV_NAME" --identity "$IDENTITY"

echo "==> [$ENV_NAME] DONE"
echo "casals_backend=$CASALS"
echo "casals_frontend=$CASALS_FE"
echo "multisig=$MSIG"
echo "frontend_url=https://$CASALS_FE.icp0.io/"
