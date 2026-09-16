#!/usr/bin/env bash
# local_up.sh — build the Realms product orchestra, `casals up` it on a fresh
# local replica through the Casals e2e harness, and print the URLs to open.
#
# This is .github/workflows/realms-e2e.yml as one command. Nothing here touches
# mainnet or a YubiKey: the identity is the plaintext `local-dev` key, the
# environment is casals.json `environments.local`, the replica is icp's local
# network on port 8000.
#
#   scripts/local_up.sh              # realms seed: build everything, up, grade, print URLs
#   scripts/local_up.sh --gaas       # ... plus gaas new: the GaaS orchestra (portal,
#                                    #   installer, registry) and one realm born through
#                                    #   the portal path, the way the wizard does it
#   scripts/local_up.sh --skip-build # reuse the last build, just up + URLs
#   scripts/local_up.sh --urls       # only print the URLs of a running stand
#   scripts/local_up.sh --down       # stop the replica and forget the bindings
#
# REALM_NAME (default first-realm) names the realm --gaas mints; a name that
# already exists is skipped, so re-runs are cheap.
#
# Layout: this repo, Casals and gos-as-a-service must be sibling checkouts
# (the sheets resolve `local:` sources against their own directory). Override
# with REALMS_DIR / CASALS_DIR / GAAS_DIR. Bindings live in
# CASALS_HOME (default ~/casals-home).
set -euo pipefail

REALMS_DIR="${REALMS_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT="$(dirname "$REALMS_DIR")"
CASALS_DIR="${CASALS_DIR:-$ROOT/Casals}"
GAAS_DIR="${GAAS_DIR:-$ROOT/gos-as-a-service}"
export CASALS_HOME="${CASALS_HOME:-$HOME/casals-home}"
IDENTITY="${CASALS_E2E_IDENTITY:-local-dev}"
IC_TOKENS_VERSION="${IC_TOKENS_VERSION:-0.1.0}"
SCENARIOS="${SCENARIOS:-fresh,idempotent}"
REALM_NAME="${REALM_NAME:-first-realm}"

export TERM="${TERM:-xterm}"
export DFX_WARNING=-mainnet_plaintext_identity
export CASALS_E2E_ENV=local
export CASALS_E2E_IDENTITY="$IDENTITY"

WITH_GAAS=0 SKIP_BUILD=0 ONLY_URLS=0 DOWN=0
for arg in "$@"; do
  case "$arg" in
    --gaas) WITH_GAAS=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --urls) ONLY_URLS=1 ;;
    --down) DOWN=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

# Everything is also appended to $CASALS_HOME/local_up.log (survives reboots,
# unlike /tmp).
mkdir -p "$CASALS_HOME"
exec > >(tee -a "$CASALS_HOME/local_up.log") 2>&1

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing tool: $1 ($2)"; }

casals() { # casals <sheet-home-name> <args...>  — the CLI with that orchestra's bindings
  local home="$1"; shift
  (cd "$CASALS_DIR" && CASALS_HOME="$CASALS_HOME/$home" \
     python3 -m casals_cli.main -e local --identity "$IDENTITY" "$@")
}

print_urls() { # print_urls <sheet-home-name> <sheet-path> <title>
  local home="$1" sheet="$2" title="$3"
  [ -f "$CASALS_HOME/$home/$home.local.json" ] || { echo "  ($title: no bindings under $CASALS_HOME/$home)"; return; }
  # `export` is the conductor's view (every stand canister); the conductor's own
  # canisters (casals-frontend, ...) are in the local bindings file.
  casals "$home" export "$sheet" | python3 -c '
import json, sys
title, bindings_file = sys.argv[1], sys.argv[2]
d = json.load(sys.stdin)
conductor = (json.load(open(bindings_file)).get("conductor") or {})
rows = dict(d.get("bindings", {}))
rows.update({k: v for k, v in conductor.items() if k not in rows})
print(f"\n  {title}")
for name, cid in rows.items():
    if name.endswith("frontend") and cid:
        print(f"    {name:36} http://{cid}.localhost:8000/")
for name, cid in rows.items():
    if not name.endswith("frontend") and cid:
        print(f"    {name:36} {cid}")
' "$title" "$CASALS_HOME/$home/$home.local.json"
}

print_portal_links() { # the wizard, and every realm the installer has minted
  [ -f "$CASALS_HOME/gaas/gaas.local.json" ] || return 0
  casals gaas export "$GAAS_DIR/casals.json" | python3 -c '
import json, sys
b = json.load(sys.stdin).get("bindings", {})
portal = b.get("realm-registry-frontend")
if not portal: sys.exit(0)
print(f"\n  Portal (gaas new / wizard)           http://{portal}.localhost:8000/")
realms = sorted(k[:-len("-backend")] for k in b
                if k.endswith("-backend") and f"{k[:-8]}-frontend" in b and f"{k[:-8]}-baton" in b)
for r in realms:
    fe = b[f"{r}-frontend"]
    print(f"    realm {r:30} http://{fe}.localhost:8000/   (portal page: http://{portal}.localhost:8000/r/{r})")
'
}

# ── --down ────────────────────────────────────────────────────────────────────
if [ "$DOWN" = 1 ]; then
  say "Stopping the local replica and removing $CASALS_HOME"
  (cd "$CASALS_DIR" && icp network stop -e local) || true
  rm -rf "$CASALS_HOME"
  exit 0
fi

# ── --urls ────────────────────────────────────────────────────────────────────
if [ "$ONLY_URLS" = 1 ]; then
  print_urls realms-product "$REALMS_DIR/casals.json" "Realms product orchestra"
  print_urls gaas "$GAAS_DIR/casals.json" "GaaS orchestra (portal + installer + realms born through it)"
  print_portal_links
  exit 0
fi

# ── preflight ─────────────────────────────────────────────────────────────────
say "Preflight"
[ -f "$CASALS_DIR/casals_cli/main.py" ] || die "Casals checkout not found at $CASALS_DIR (set CASALS_DIR)"
[ -f "$REALMS_DIR/casals.json" ] || die "realms casals.json not found at $REALMS_DIR"
if [ "$WITH_GAAS" = 1 ]; then
  [ -f "$GAAS_DIR/casals.json" ] || die "gos-as-a-service checkout not found at $GAAS_DIR (set GAAS_DIR)"
fi
need icp     "npm install -g @icp-sdk/icp-cli"
need ic-wasm "npm install -g @icp-sdk/ic-wasm"
need dfx     "https://internetcomputer.org/docs/building-apps/getting-started/install"
need node    "node 20+"
need npm     "node 20+"
need python3 "python 3.11"
need curl    "curl"
python3 -c 'import basilisk' 2>/dev/null || die "python deps missing: pip install -r $CASALS_DIR/requirements-dev.txt -r $REALMS_DIR/requirements.txt"
python3 -c 'import ic' 2>/dev/null       || die "python deps missing: pip install -r $CASALS_DIR/requirements-dev.txt"
echo "  realms:  $REALMS_DIR"
echo "  Casals:  $CASALS_DIR"
[ "$WITH_GAAS" = 1 ] && echo "  gaas:    $GAAS_DIR"
echo "  home:    $CASALS_HOME"
echo "  icp $(icp --version | awk '{print $2}'), dfx $(dfx --version | awk '{print $2}'), node $(node --version), $(python3 --version)"

# ── identity ──────────────────────────────────────────────────────────────────
say "Identity: $IDENTITY (plaintext, local replica only)"
if ! icp identity list 2>/dev/null | awk '{print $1=="*"?$2:$1}' | grep -qx "$IDENTITY"; then
  icp identity new "$IDENTITY" --storage plaintext
fi
if ! dfx identity list 2>/dev/null | grep -qx "$IDENTITY"; then
  # dfx runs the cross-quarter live test; it must be the same key as icp's.
  # icp exports PKCS#8 ("BEGIN PRIVATE KEY"); dfx only imports SEC1
  # ("BEGIN EC PRIVATE KEY"), so convert in between.
  need openssl "openssl (to convert the PEM for dfx)"
  pem="$(mktemp)"; sec1="$(mktemp)"; trap 'rm -f "$pem" "$sec1"' EXIT
  icp identity export "$IDENTITY" > "$pem"
  openssl ec -in "$pem" -out "$sec1" 2>/dev/null
  dfx identity import "$IDENTITY" "$sec1" --storage-mode plaintext
fi
icp_p="$(icp identity principal --identity "$IDENTITY")"
dfx_p="$(dfx identity get-principal --identity "$IDENTITY")"
[ "$icp_p" = "$dfx_p" ] || die "icp and dfx '$IDENTITY' differ ($icp_p vs $dfx_p); delete one and rerun"
echo "  $icp_p"

# ── builds ────────────────────────────────────────────────────────────────────
if [ "$SKIP_BUILD" = 0 ]; then
  say "Realms: ic-tokens wasms (v$IC_TOKENS_VERSION)"
  mkdir -p "$REALMS_DIR/.external-wasms"
  for w in token_backend nft_backend; do
    [ -s "$REALMS_DIR/.external-wasms/$w.wasm" ] && { echo "  have $w.wasm"; continue; }
    curl -fsSL "https://github.com/smart-social-contracts/ic-tokens/releases/download/v${IC_TOKENS_VERSION}/${w}.wasm" \
      -o "$REALMS_DIR/.external-wasms/$w.wasm"
    echo "  fetched $w.wasm"
  done

  say "Realms: backends (realm_backend test variant, marketplace_backend)"
  (cd "$REALMS_DIR"
   CANISTER_CANDID_PATH="$PWD/src/realm_backend/realm_backend.did" \
     python3 scripts/pack_realm_backend.py --variant test
   CANISTER_CANDID_PATH="$PWD/src/marketplace_backend/marketplace_backend.did" \
     python3 -m basilisk marketplace_backend src/marketplace_backend/main.py
   ls -l .basilisk/realm_backend/realm_backend.wasm .basilisk/marketplace_backend/marketplace_backend.wasm)

  say "Realms: frontends (realm_frontend test variant, marketplace_frontend)"
  (cd "$REALMS_DIR"
   # Root workspace install: a workspace-local install strands vite away from
   # the hoisted @sveltejs/kit. extension-bridge is imported from its dist/.
   npm install --legacy-peer-deps
   npm run build --workspace packages/extension-bridge
   (cd src/realm_frontend && REALMS_BUILD_VARIANT=test npm run build && test -f dist/index.html)
   python3 scripts/check_frontend_variant.py src/realm_frontend/dist test
   (cd src/marketplace_frontend && npm run build && test -f dist/index.html))

  if [ "$WITH_GAAS" = 1 ]; then
    say "GaaS: backends (realm_installer, realm_registry_backend)"
    (cd "$GAAS_DIR"
     CANISTER_CANDID_PATH="$PWD/src/realm_installer/realm_installer.did" \
       python3 -m basilisk realm_installer src/realm_installer/main.py
     CANISTER_CANDID_PATH="$PWD/src/realm_registry_backend/realm_registry_backend.did" \
       python3 -m basilisk realm_registry_backend src/realm_registry_backend/main.py)

    say "GaaS: portal frontend (realm_registry_frontend)"
    (cd "$GAAS_DIR"
     npm ci --legacy-peer-deps
     dfx generate realm_registry_backend
     dfx generate realm_installer
     npm run build --workspace=realm_registry_frontend
     test -f src/realm_registry_frontend/dist/index.html)
  fi
fi

# ── stale bindings ────────────────────────────────────────────────────────────
# A local replica starts empty after a reboot / `icp network stop`; bindings
# left from the previous stand then point at canisters that no longer exist.
# Forget them so `casals up` converges from nothing instead of failing.
say "Replica"
if ! (cd "$CASALS_DIR" && icp network status -e local >/dev/null 2>&1); then
  (cd "$CASALS_DIR" && icp network start -e local --background >/dev/null 2>&1) || true
  for _ in $(seq 1 60); do (cd "$CASALS_DIR" && icp network status -e local >/dev/null 2>&1) && break; sleep 1; done
fi
(cd "$CASALS_DIR" && icp network status -e local >/dev/null 2>&1) || die "local replica did not come up (icp network start -e local)"
for home in realms-product gaas; do
  f="$CASALS_HOME/$home/$home.local.json"
  [ -f "$f" ] || continue
  backend="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("backend_id") or "")' "$f")"
  if [ -n "$backend" ] && ! (cd "$CASALS_DIR" && icp canister status "$backend" -e local --identity "$IDENTITY" >/dev/null 2>&1); then
    echo "  $home: bindings point at $backend, which is not on this replica — forgetting them"
    rm -rf "$CASALS_HOME/$home"
  else
    echo "  $home: bindings present, conductor $backend live"
  fi
done

# ── up ────────────────────────────────────────────────────────────────────────
# The harness starts the replica if needed, funds the identity, then per sheet:
#   fresh       — `casals up` converges from nothing, `plan` is empty, oracle PASS
#   idempotent  — a second `up` changes nothing
# KEEP=1 leaves the replica and the orchestras up.
say "casals up — Realms product orchestra (scenarios: $SCENARIOS)"
(cd "$CASALS_DIR" && KEEP=1 SCENARIOS="$SCENARIOS" python3 tests/e2e/run_e2e.py "$REALMS_DIR/casals.json")

if [ "$WITH_GAAS" = 1 ]; then
  say "casals up — GaaS orchestra (scenarios: $SCENARIOS)"
  (cd "$CASALS_DIR" && KEEP=1 SCENARIOS="$SCENARIOS" python3 tests/e2e/run_e2e.py "$GAAS_DIR/casals.json")

  # A realm is born the way the portal wizard does it: request_deployment on
  # the registry → installer create_stand → the conductor builds the stand from
  # the `Deployments` template → the realm frontend serves /canister_ids.js.
  if casals gaas export "$GAAS_DIR/casals.json" | python3 -c '
import json, sys; sys.exit(0 if sys.argv[1] + "-backend" in json.load(sys.stdin).get("bindings", {}) else 1)' "$REALM_NAME"; then
    say "Realm '$REALM_NAME' already exists on the GaaS orchestra; skipping the portal path"
  else
    say "Deploy realm '$REALM_NAME' through the portal path (request_deployment → installer → conductor)"
    (cd "$GAAS_DIR" && CASALS_HOME="$CASALS_HOME" IDENTITY="$IDENTITY" TIMEOUT_S="${TIMEOUT_S:-1500}" \
       python3 tests/e2e/deploy_realm.py "$REALM_NAME")
  fi
fi

# ── URLs ──────────────────────────────────────────────────────────────────────
say "Ready. Open in the browser (Chrome/Firefox resolve *.localhost; Safari does not):"
print_urls realms-product "$REALMS_DIR/casals.json" "Realms product orchestra"
if [ "$WITH_GAAS" = 1 ]; then
  print_urls gaas "$GAAS_DIR/casals.json" "GaaS orchestra (portal + installer + realms born through it)"
  print_portal_links
fi
cat <<EOF

  Also:
    scripts/local_up.sh --urls                                       # print these again
    (cd $CASALS_DIR && CASALS_HOME=$CASALS_HOME/realms-product \\
       python3 -m casals_cli.main -e local --identity $IDENTITY show|plan|oracle $REALMS_DIR/casals.json)
    scripts/local_up.sh --down                                       # stop the replica, forget bindings
EOF
