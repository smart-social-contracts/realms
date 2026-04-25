#!/usr/bin/env bash
# Dispatch GitHub Actions "Deploy Infra".
# Requires: gh auth login, access to smart-social-contracts/realms.
#
# The branch you pass must contain the infra canister code you want deployed
# (push your commits before running).
#
# Usage:
#   ./scripts/dispatch-upgrade-infra.sh [environment] [canisters] [git-ref-for-checkout]
#
# Examples:
#   ./scripts/dispatch-upgrade-infra.sh staging realm_installer main
#   ./scripts/dispatch-upgrade-infra.sh demo all feat/my-branch
#
set -euo pipefail
ENVIRONMENT="${1:-staging}"
CANISTERS="${2:-all}"
BRANCH="${3:-main}"

REPO="smart-social-contracts/realms"
WF="deploy-infra.yml"

if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI: https://cli.github.com/" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "Run: gh auth login" >&2
  exit 1
fi

echo "Dispatching $WF on repo $REPO"
echo "  checkout ref: $BRANCH  |  environment: $ENVIRONMENT  |  canisters: $CANISTERS"

gh workflow run "$WF" \
  --repo "$REPO" \
  --ref "$BRANCH" \
  -f "environment=$ENVIRONMENT" \
  -f "canisters=$CANISTERS"

echo "Queued. Open: https://github.com/$REPO/actions/workflows/$WF"
