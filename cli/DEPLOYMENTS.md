This document is intended to describe the different nuances and complexities of the deployment process.

Command: `realms realm/registry/mundus create --manifest ... --mode ... --network ... --deploy`


1. Creates folder structure in `.realms`
    - `.realms/mundus/...`
    - `.realms/registry/...`
    - `.realms/realm/...`

    Take by default the files in `examples/demo/...`
    Copy the source and script folders from repo
    including scripts/utils/...
        1-install-extensions.sh
        2-deploy-canisters.sh
        3-upload-data.sh
        4-run-adjustments.sh


2. Check if for the `network` param (by default `local` there is any canister id already created in `canister_ids.json`

3. Consider mode (`reinstall` or `upgrade`)
    for `realm`, if `reinstall`, run the script to feed the canister backend with data

