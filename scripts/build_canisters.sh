#!/bin/bash

set -e
set -x

echo "Building canisters..."

echo "Building backend"
dfx start --clean --background

dfx deploy internet_identity

dfx canister create realm1_backend
dfx canister create realm2_backend
dfx canister create realm3_backend
dfx build realm1_backend
dfx build realm2_backend
dfx build realm3_backend
dfx generate realm1_backend
dfx generate realm2_backend
dfx generate realm3_backend
dfx stop

echo "Building frontend"
npm install --legacy-peer-deps
sh scripts/update_config.sh
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend

echo "Building canisters done"
