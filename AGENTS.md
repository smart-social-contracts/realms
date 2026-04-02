# Agent Instructions for Realms

Realms is a multi-tenant dApp platform on the Internet Computer with quarters/federation architecture.

## Key Technologies
- **Backend**: Python (ic-python/basilisk) on ICP canisters
- **Frontend**: Svelte + TypeScript
- **Auth**: Internet Identity with passkeys
- **Storage**: ic-python-db with encrypted fields
- **Crypto**: `@dfinity/vetkeys` (NOT legacy `ic-vetkd-utils`)

## Project Layout
- `src/realm_backend/` — Python backend canister (main.py has all endpoints)
- `src/realm_backend/api/` — API handlers (status, user, crypto, vetkeys, extensions, zones, nft)
- `src/realm_backend/ggg/` — Entities by domain (system, governance, finance, identity, justice, land)
- `src/realm_frontend/` — SvelteKit frontend
- `src/realm_frontend/src/lib/config.js` — TEST_MODE flags
- `src/realm_frontend/src/lib/auth.js` — Internet Identity auth
- `extensions/` — Git submodule with realm extensions
- `cli/` — `realms` CLI tool
- `scripts/` — Deploy and utility scripts

## Backend Patterns (Basilisk / IC-Python)
- `datetime.strptime` NOT available — use manual parsing or `calendar.timegm`
- User entity: `id = String()` stores principal string; NO `principal` attribute
- `TimestampedMixin._timestamp_created` resets to 0 on DB reload; use `timestamp_created` string attr
- Build: `python -m basilisk realm_backend src/realm_backend/main.py`

## Candid Interface
- Reference copy: `src/realm_frontend/src/lib/realm_backend.did.js`
- Actual build-time IDL: `.realms/mundus/.../declarations/realm_backend/realm_backend.did.js` (auto-generated)
- After changing backend interfaces → run `dfx generate` in mundus directory

## TEST_MODE System
- Activate: `?testmode=1` (URL) or `VITE_TEST_MODE=true` (env)
- Sub-flags: `ii_bypass`, `admin_self_reg`, `demo_data`, `skip_terms`
- CI defaults: TEST_MODE + II_BYPASS + ADMIN_SELF_REGISTRATION = true

## Quarters Architecture
- Federations of realms with one capital quarter (governance coordinator)
- `User.home_quarter` — full rights; `GuestUser` — view/transact only
- Single frontend asset canister; dynamic actor switching via `setActiveQuarter()`

## Extensions
- Inter-extension dependencies possible
- Testing realm: Dominion (-R 1); Dev realm: Agora (-R 2); Syntropia (-R 3)

## Deployment
- **Local**: `source venv/bin/activate` → `pip install -e cli` → `realms realm create --deploy`
- **Re-deploy**: `scripts/deploy_local_dev.sh`
- **Staging**: `bash scripts/deploy_staging_dev.sh -R 2 -f -c` with identity `my_dev_identity_1`
- Must `export DFX_WARNING=-mainnet_plaintext_identity`

## Skills
- Fetch from https://skills.internetcomputer.org when working on specific ICP features

## Rules
- Do NOT commit unless told to
- Do NOT use `dfx` directly — use `realms` CLI or deploy scripts
- Do NOT hardcode canister IDs
