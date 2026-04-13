#!/usr/bin/env bash
# Re-compile all requirements.in → requirements.txt lockfiles.
# Run this whenever you want to pull in new dependency versions.
#
# Usage:
#   ./scripts/update-locks.sh            # update all lockfiles
#   ./scripts/update-locks.sh --upgrade  # upgrade all packages to latest

set -euo pipefail
cd "$(dirname "$0")/.."

EXTRA_ARGS="${*}"
COMPILE="pip-compile --strip-extras --allow-unsafe --quiet ${EXTRA_ARGS}"

echo "==> Compiling main repo lockfiles..."

${COMPILE} --output-file=requirements.txt requirements.in
echo "    requirements.txt"

${COMPILE} --output-file=cli/realms/cli/requirements.txt cli/realms/cli/requirements.in
echo "    cli/realms/cli/requirements.txt"

${COMPILE} --output-file=src/realm_registry_backend/requirements.txt src/realm_registry_backend/requirements.in
echo "    src/realm_registry_backend/requirements.txt"

echo "==> Compiling extensions submodule lockfiles..."

${COMPILE} --output-file=extensions/extensions/vault/requirements.txt extensions/extensions/vault/requirements.in
echo "    extensions/extensions/vault/requirements.txt"

${COMPILE} --output-file=extensions/marketplace/requirements.txt extensions/marketplace/requirements.in
echo "    extensions/marketplace/requirements.txt"

${COMPILE} --output-file=extensions/marketplace/marketplace_backend/requirements.txt extensions/marketplace/marketplace_backend/requirements.in
echo "    extensions/marketplace/marketplace_backend/requirements.txt"

echo ""
echo "Done. Review changes with: git diff **/requirements.txt"
