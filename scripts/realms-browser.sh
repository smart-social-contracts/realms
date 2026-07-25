#!/usr/bin/env bash
# Launch an isolated Chrome window for manual Realms QA on staging.
#
# Usage:
#   realms-browser.sh <identity-number> [realm-slug]
#
# Examples:
#   realms-browser.sh 1                      # Identity 1 (admin/founder), ?ti=1
#   realms-browser.sh 2                      # Identity 2 (member), ?ti=2
#   realms-browser.sh 3 manualtest1000syntropia
#
# identity-number matches ?ti= (1-based: Identity 1 → ti=1).

set -euo pipefail

IDENTITY="${1:?Usage: realms-browser.sh <identity-number> [realm-slug]}"
SLUG="${2:-manualtest1000syntropia}"
PROFILE="/tmp/realms-chrome-id${IDENTITY}"
URL="https://staging.realmsgos.org/r/${SLUG}/join?ti=${IDENTITY}"

rm -rf "${PROFILE}"

google-chrome \
  --user-data-dir="${PROFILE}" \
  --incognito \
  --no-first-run \
  --no-default-browser-check \
  --disable-application-cache \
  --disk-cache-size=1 \
  --new-window \
  "${URL}" &

echo "Opened Identity ${IDENTITY} (?ti=${IDENTITY}) → ${URL}"
