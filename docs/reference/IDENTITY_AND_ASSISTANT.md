# Cross-realm identity & the user-scoped AI assistant

Implements issue #233. This document describes the **interim staging** cross-realm
identity model. For **production scale** (unlimited realms, no alternative-origins
list), see **[FEDERATION_PORTAL.md](./FEDERATION_PORTAL.md)** — single portal
login origin, `resolve_slug` via consensus update, sandboxed realm iframes with
scoped delegation handoff ([bridge contract](./FEDERATION_PORTAL_REALM_BRIDGE.md)),
no `ii-alternative-origins`.

Below is the current **#233 `derivationOrigin` + alternative-origins** approach
and how the **user-scoped AI assistant** builds on one principal.

## 1. The identity problem

Internet Identity is **pairwise / per-frontend-origin**: the same II anchor
derives a **different principal for each frontend origin**. Every realm and the
registry serve **separate frontend asset canisters** = separate origins, so the
same human is, by default, a *different* `user_principal` on every realm. Any
"user-scoped" feature (assistant history, BYOK keys, MCP tokens) silently
degrades to "realm-scoped" without the fix below.

## 2. The fix — a shared `derivationOrigin`

We pin a single **canonical origin** (the **registry**) and have every frontend
log in with that `derivationOrigin`. Internet Identity then issues the **same
principal** on every realm + the registry, provided the canonical origin lists
each frontend in its `/.well-known/ii-alternative-origins`.

### Canonical origin per environment

| Environment | Canonical origin |
|---|---|
| staging | `https://staging.realmsgos.org` |
| demo | `https://demo.realmsgos.org` |
| test | `https://test.realmsgos.org` |

### Moving parts

1. **Registry frontend** (`src/realm_registry_frontend`)
   - `src/lib/config.js` → `CONFIG.ii_derivation_origin` (per-env; override with
     `VITE_II_DERIVATION_ORIGIN`).
   - `src/lib/auth.js` passes `derivationOrigin` into `client.login(...)`.
   - Serves `static/.well-known/ii-alternative-origins` (the canonical list).
   - `static/.ic-assets.json5` serves that file as `application/json` with
     `Access-Control-Allow-Origin: *` so the II canister can read it.
2. **Realm frontend** (`src/realm_frontend`)
   - `src/lib/auth.js` reads `globalThis.__CANISTER_IDS.derivation_origin` and
     passes it as `derivationOrigin`.
   - The value is injected at deploy time by `realm_installer`
     (`_build_canister_ids_js`) from the deployment manifest's
     `infra.ii_derivation_origin` (set by the registry wizard's
     `deployment-manifest.js`).
3. **Registry deploy manifest** (`deployment-manifest.js`) stamps
   `infra.ii_derivation_origin` so every wizard-deployed realm gets the canonical
   origin automatically.

### Constraints (READ BEFORE SCALING)

- **~10 alternative-origins cap.** Internet Identity limits the number of
  alternative origins. A flat "list every realm frontend" does **not** scale to
  user-created realms. The curated list in
  `static/.well-known/ii-alternative-origins` covers the canonical domains and
  the first-class demo realms. The durable fix for many realms is to route all
  realm frontends through one shared origin / reverse proxy (single frontend
  origin) rather than per-realm asset-canister origins.
- **Secession (see `QUARTERS.md`).** Any realm/quarter that deploys its **own**
  frontend origin MUST be added to the canonical
  `/.well-known/ii-alternative-origins` at secession time, or identity breaks for
  that realm (its users get a fresh principal and look like strangers).
- **Changing `derivationOrigin` re-derives principals.** Flipping it on an
  environment with *real* users would orphan their existing on-chain `User`
  records (keyed by the old per-origin principal). This is safe on
  test/demo/staging (disposable / II-bypass identities) but requires a
  principal-migration plan before enabling on any environment with real users.
- **Test mode is unaffected.** `TEST_MODE_II_BYPASS` uses synthetic Ed25519
  identities, so this concern only manifests on real Internet Identity. **Green
  local/CI tests do NOT prove the derivationOrigin wiring works** — verify
  manually on a deployed environment (see §4).

## 3. The user-scoped assistant

With one principal per human, the assistant is owned by the **user**; the realm
is **optional context**.

- **Geister** (`geister`):
  - `database/schema.sql` adds a nullable `context_realm` to `conversations` and
    `chat_sessions`, backfills it from the legacy `realm_principal`, and relaxes
    `realm_principal NOT NULL` so general-mode (no realm) chats can be stored.
  - `database/db_client.py`: `list_chat_sessions(user_principal, context_realm=None)`
    lists **by user** (global inbox); realm is an optional filter.
    `get_conversation_history`, `store_conversation`, `create_chat_session` take
    an optional `context_realm`.
  - `api.py`: `/api/ask` and `/api/conversations` accept `context_realm`
    (canonical) with `realm_principal` as a back-compat alias. No realm →
    **general mode**: realm status / codex / proposal enrichment and realm tools
    are skipped.
- **Realm surfaces** (`llm_chat` extension, `AiAssistantPanel`): send the realm
  as `context_realm` (not owner) and list the user's **entire** conversation
  inbox so history follows the user between realms and the registry.
- **Registry surface** (`RegistryAssistant.svelte`): a self-contained panel that
  talks to Geister in **general mode**. It never reads any realm's
  `ai_assistant_enabled` flag, so a realm cannot disable the user's global
  assistant.
- **`ai_assistant_enabled`** now governs only the **in-realm, realm-context**
  surface (codex/proposal tools, realm status in prompt) — not the user's global
  assistant.

### Out of scope (separate issues)
BYOK (user's own model/Claude key) and the Realms **MCP** server build on the
canonical principal but are tracked separately. Marketplace **hired** assistants
stay realm-scoped for permissions.

## 4. Manual verification runbook (real II)

Automated tests can't prove §2 (II bypass uses synthetic identities). On a
deployed environment:

1. Log in with the same II anchor on **two different realm frontends** and on the
   **registry**; confirm `principal.toText()` is **identical** in all three
   (browser console logs `Logged in with principal: …`).
2. Confirm `https://<canonical>/.well-known/ii-alternative-origins` returns the
   JSON list with `Content-Type: application/json`.
3. Start a chat in a realm, then open the registry assistant — the conversation
   inbox should be the same (after the Geister DB migration is applied).
4. Apply `geister/database/schema.sql` (idempotent) before/with the Geister
   redeploy; rebuild + repackage the `llm_chat` extension bundle.
