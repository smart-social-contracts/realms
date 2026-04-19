# On-chain `realm_installer.deploy_realm`

Closes [#192](https://github.com/smart-social-contracts/realms/issues/192).

`realm_installer.deploy_realm` performs an **end-to-end realm install**
(WASM + extensions + codices) from a single inter-canister call.  All
work runs on-chain — there is no off-chain orchestrator in the loop
beyond firing the initial call.

```
                            ┌────────────────────┐
                            │  caller (CLI / CI  │
  ┌───────────────┐  text   │  / DAO proposal /  │
  │ deploy_realm  │ ◀─────  │  another canister) │
  │  (manifest)   │         └────────────────────┘
  └──────┬────────┘
         │ task_id (immediate, < 1s)
         ▼
  ┌──────────────────────────────────────────────────────────┐
  │ realm_installer (this canister)                          │
  │                                                          │
  │  • persists DeployTask + N×DeployStep (ic-python-db)     │
  │  • enforces concurrency: one active task / target        │
  │  • drives steps via ic.set_timer(_cb, _NEXT_STEP_DELAY_S)│
  │                                                          │
  │  step kinds:                                             │
  │    ─ wasm       → install_chunked_code on target         │
  │    ─ extension  → target.install_extension_from_registry │
  │    ─ codex      → target.install_codex_from_registry     │
  │                                                          │
  │  on per-step error: record, continue with next step      │
  │  on canister upgrade: post_upgrade resumes in-flight     │
  └──────────────────────────────────────────────────────────┘
```

## Why on-chain

1. **No off-chain CI infra in the deploy critical path.** A DAO
   proposal, a UI button, or another canister can deploy a realm
   without anyone holding controller keys on a Linux box.
2. **Auditability.** Every step (and its error, if any) is persisted in
   stable memory and queryable forever via `get_deploy_status`.
3. **Resumability.** Upgrade the installer mid-deploy → `post_upgrade`
   re-arms timers for any task still in `running`.
4. **Concurrency safety.** The installer rejects a second `deploy_realm`
   for the same `target_canister_id` while one is in flight, so the IC
   management chunk-store can't get clobbered by parallel uploads.

## Endpoints

```candid
service : {
  "deploy_realm"      : (text) -> (text);
  "get_deploy_status" : (text) -> (text) query;
  "list_deploys"      : ()     -> (text) query;
  …
}
```

All three endpoints accept/return JSON-encoded text (consistent with
the rest of the realm_installer surface).

### `deploy_realm(manifest_json) → kickoff_json`

Manifest schema:

```json
{
  "target_canister_id":   "ijdaw-dyaaa-aaaac-beh2a-cai",
  "registry_canister_id": "iebdk-baaaa-aaaac-bejga-cai",

  "wasm": {
    "namespace": "wasm",
    "path":      "realm-base-1.2.3.wasm.gz",
    "mode":      "upgrade",
    "init_arg_b64": ""
  },

  "extensions": [
    { "id": "voting", "version": null         },
    { "id": "vault",  "version": "0.2.0"      }
  ],

  "codices": [
    { "id": "syntropia/membership", "version": null, "run_init": true }
  ]
}
```

* `wasm`, `extensions`, `codices` are **all optional** — supply only
  what should change. Omitting `wasm` skips the chunked install.
* `mode` is `install | reinstall | upgrade`. `upgrade` preserves
  stable memory.
* Any field is allowed to contain forward-compatible extra keys; the
  installer ignores them.

Kickoff response:

```json
{ "success": true, "task_id": "deploy_1729382938012345678",
  "status": "queued", "steps_count": 19 }
```

If a deploy is already in-flight against the same target:

```json
{ "success": false,
  "error":   "deploy already in progress for target …",
  "conflicting_task_id": "deploy_…" }
```

### `get_deploy_status(task_id) → status_json`

```json
{ "success": true,
  "task_id": "deploy_…",
  "status":  "running",            // queued|running|completed|partial|failed
  "target_canister_id":   "…",
  "registry_canister_id": "…",
  "started_at":   1729382938,
  "completed_at": null,
  "error": null,
  "wasm":      { "idx": 0, "kind": "wasm",      "label": "wasm/realm-base-…", "status": "completed", "result": {…}, "error": null },
  "extensions":[ { "idx": 1, "kind": "extension","label": "ext/voting",        "status": "completed", … },
                 { "idx": 2, "kind": "extension","label": "ext/vault",         "status": "failed",
                   "error": "registry returned: extension vault@0.2.0 not found" }, … ],
  "codices":   [ { "idx": …, "kind": "codex",    "label": "codex/syntropia/membership", "status": "completed", … } ]
}
```

Terminal statuses:

* `completed` — every step succeeded.
* `partial`   — at least one step failed; the remaining steps still
  ran (continue-and-report semantics from the issue).
* `failed`    — fatal error in the orchestrator itself
  (e.g. couldn't load the task from stable memory).

### `list_deploys() → list_json`

Returns a summary of every `DeployTask` ever recorded by this
installer (newest-first, capped to a sensible page size). Use it to
discover task ids when you've lost the kickoff response.

## CLI

A thin wrapper lives in `realms installer …`:

```bash
# kick off and block until terminal
realms installer deploy \
    --installer <installer-canister-id> \
    --manifest manifest.json \
    --network staging

# fire-and-forget
realms installer deploy -I <id> -m manifest.json --no-wait

# poll an existing task
realms installer status -I <id> --task-id deploy_…  --network staging

# list everything this installer has run
realms installer list   -I <id> --network staging
```

`-m -` reads the manifest from stdin, e.g.
`jq … | realms installer deploy -I … -m -`.

## CI integration

`scripts/ci_install_mundus.py` (used by the **Deploy** workflow)
collapses what used to be three sequential CLI commands per realm
(`realms wasm install` + `realms extension registry-install` ×N +
`realms codex registry-install` ×M) into one `deploy_realm` call per
realm.  All members are dispatched up-front and polled in a single
shared loop, so 3 realms install in roughly the time of the slowest
one (instead of `Σ` of all of them).

## Operational notes

### Concurrency

`deploy_realm` rejects a new request if any task with status
`queued | running` exists for the same `target_canister_id`. To force a
retry after a crash you currently need to wait until the in-flight
task drains (or recreate the installer). A future iteration may add an
explicit `cancel_deploy(task_id)` endpoint.

### Upgrade-mid-deploy

`@post_upgrade` walks every `DeployTask` whose `status` is
`queued | running` and re-arms a timer at the next pending step.
In-flight inter-canister calls *that were already on the wire* during
the upgrade may surface in the per-step `error` field as
"replica returned reject" — re-running the deploy is safe (the
chunk-store is reset between attempts on the IC management side; the
realm itself is idempotent for `upgrade` mode).

### Cycles

The installer pays for chunked uploads + inter-canister calls out of
**its own** cycle balance (no per-call fees from the caller). For a
realm with WASM + 17 extensions + ~6 codices, total cost is well
under 1 T cycles.  Top up the installer with the same approach you'd
use for any long-lived service canister.

### Storage

`DeployTask` and `DeployStep` records live in stable memory
(`StableBTreeMap`, memory id `1`). They're never garbage-collected
automatically — `list_deploys` is therefore your full audit log. If
that becomes a problem in practice, add a `gc_completed_deploys`
admin endpoint.

## See also

* Source: `src/realm_installer/main.py` (the `deploy_realm`,
  `get_deploy_status`, `_cb`, and `_resume_in_flight_deploys`
  functions are the interesting bits).
* Candid: `src/realm_installer/realm_installer.did`.
* CI driver: `scripts/ci_install_mundus.py` (the `stage2_install`
  function, plus `_kickoff_deploy` / `_poll_all_deploys`).
* CLI: `cli/realms/cli/commands/installer.py`.
