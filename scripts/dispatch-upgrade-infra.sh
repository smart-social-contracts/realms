#!/usr/bin/env bash
# Dispatch GitHub Actions "Upgrade Infra Canisters" (Option A).
# Requires: gh auth login, access to smart-social-contracts/realms.
#
# The branch you pass must contain the realm_installer code you want deployed
# (push your commits before running).
#
# Usage:
#   ./scripts/dispatch-upgrade-infra.sh [network] [canisters] [git-ref-for-checkout]
#
# Examples:
#   ./scripts/dispatch-upgrade-infra.sh staging realm_installer main
#   ./scripts/dispatch-upgrade-infra.sh demo realm_installer feat/my-branch
#
set -euo pipefail
NETWORK="${1:-staging}"
CANISTERS="${2:-realm_installer}"
BRANCH="${3:-main}"

REPO="smart-social-contracts/realms"
WF="upgrade-infra-canisters.yml"

if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI: https://cli.github.com/" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "Run: gh auth login" >&2
  exit 1
fi

echo "Dispatching $WF on repo $REPO"
echo "  checkout ref: $BRANCH  |  network: $NETWORK  |  canisters: $CANISTERS"

gh workflow run "$WF" \
  --repo "$REPO" \
  --ref "$BRANCH" \
  -f "network=$NETWORK" \
  -f "canisters=$CANISTERS"

echo "Queued. Open: https://github.com/$REPO/actions/workflows/$WF"
