#!/usr/bin/env bash
# Publish Ashoka assistant assets + register listing on the test marketplace.
set -euo pipefail

export TERM=xterm DFX_WARNING=-mainnet_plaintext_identity

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source venv/bin/activate 2>/dev/null || true

FR=uq2mu-kaaaa-aaaah-avqcq-cai
MP=2wldc-niaaa-aaaad-qlxga-cai
ASSISTANT_ID="smart-social-contracts/ashoka"
VERSION="1.0.0"
NS="assistant/${ASSISTANT_ID}/${VERSION}"
SRC="${REPO_ROOT}/assistants/smart-social-contracts/ashoka"

echo "=== 1. Publish assistant files to file_registry ==="
realms files publish-assistant \
  --network test \
  --registry "$FR" \
  --source-dir "$SRC" \
  --version "$VERSION"

echo "=== 2. Create / update marketplace listing ==="
dfx canister call "$MP" create_assistant "(record {
  assistant_id = \"${ASSISTANT_ID}\";
  name = \"Ashoka\";
  description = \"AI governance advisor for Realms — plain-language insights on realm activity, codices, and policy.\";
  version = \"${VERSION}\";
  price_e8s = 0 : nat64;
  pricing_summary = \"Included with core llm_chat on Realms test environments\";
  icon = \"🏛️\";
  categories = \"oversight,governance\";
  runtime = \"self_hosted\";
  endpoint_url = \"https://geister-api.realmsgos.dev/api/ask\";
  base_model = \"gpt-oss:20b\";
  requested_role = \"advisor\";
  requested_permissions = \"read_realm_status,read_codex\";
  domains = \"governance,oversight,codex\";
  languages = \"en\";
  training_data_summary = \"Governance-focused system prompt; inference via Geister (RunPod/Ollama).\";
  eval_report_url = \"https://github.com/smart-social-contracts/geister/tree/main/prompts/personas\";
  file_registry_canister_id = \"${FR}\";
  file_registry_namespace = \"${NS}\";
})" --network test

echo "=== 3. Mark verified (controller) ==="
dfx canister call "$MP" set_verification_status \
  "(\"assistant\", \"${ASSISTANT_ID}\", \"verified\", \"Official Smart Social Contracts governance advisor\")" \
  --network test

echo "=== Done ==="
echo "Browse: https://mxyd5-3qaaa-aaaao-ba2xq-cai.icp0.io/assistants?q=ashoka"
