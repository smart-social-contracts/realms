#!/bin/bash

set -e
set -x

echo "Building canisters..."

echo "Building backend"
dfx start --clean --background
dfx canister create realm_backend
dfx build realm_backend
dfx generate realm_backend
dfx stop

echo "Building frontend"
npm install --legacy-peer-deps
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend

echo "Building canisters done"