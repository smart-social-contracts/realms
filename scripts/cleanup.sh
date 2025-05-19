#!/bin/bash

# Define a preservation flag (add --preserve-declarations to preserve them)
PRESERVE_DECLARATIONS=false
if [[ "$*" == *"--preserve-declarations"* ]]; then
  PRESERVE_DECLARATIONS=true
fi

rm -rf \
  .dfx \
  .env \
  node_modules \
  src/realms_frontend/dist/ \
  src/realms_frontend/.svelte-kit/

# Only remove declarations if not preserving
if [ "$PRESERVE_DECLARATIONS" = false ]; then
  rm -rf src/declarations/
fi