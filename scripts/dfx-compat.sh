#!/usr/bin/env sh
# Operator hosts wrap dfx behind a deprecation gate that requires
# --run-deprecated; a stock dfx install rejects the flag outright. npm scripts
# cannot probe, so they call this instead of dfx directly.
set -e

if dfx --run-deprecated --version >/dev/null 2>&1; then
  exec dfx --run-deprecated "$@"
fi

exec dfx "$@"
