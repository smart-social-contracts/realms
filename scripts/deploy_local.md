dfx canister create realm_backend
dfx generate realm_backend
npm install --legacy-peer-deps
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
dfx deploy realm_backend
dfx deploy realm_frontend
dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "aaa";
  }
)'