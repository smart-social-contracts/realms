#!/bin/bash

set -e
set -x

dfx stop
dfx start --clean --background --logfile dfx.log
dfx deploy internet_identity
dfx deploy realm_backend --yes
dfx generate realm_backend
npm install --legacy-peer-deps
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
sh scripts/update_config.sh
dfx deploy realm_frontend
scripts/setup_demo.sh