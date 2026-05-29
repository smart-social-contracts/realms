# Quarters: Horizontal Scalability Architecture

## Overview

Quarters enable Realms to scale horizontally. Each quarter is a **full, autonomous realm backend** that participates in a **federation** — a group of quarters sharing a common manifest, extensions, and governance framework. Any quarter can **secede** at any time to become an independent realm, taking all its users and data with it.

This design supports the core Realms GOS principle: **opting out must always be frictionless**.

---

## Terminology

| Term | Definition |
|------|-----------|
| **Quarter** | A full realm backend canister that participates in a federation. Holds its own users, governance data, extensions. |
| **Capital** | The quarter designated as the federation coordinator. Hosts the federation codex, coordinates realm-wide votes, tax aggregation. It is still a quarter — holds users, runs governance — and can be moved by vote. |
| **Federation** | A group of quarters sharing a manifest, extensions, and governance framework. Communication is peer-to-peer. |
| **Home quarter** | The quarter where a user is registered with full rights (vote, propose, tax obligations). |
| **Guest access** | Lightweight presence on a non-home quarter (transact, view, participate in local events — no governance weight). |
| **Secession** | A quarter leaving the federation to become an independent realm. Zero data migration required. |

---

## Design Principles

1. **A quarter IS a realm.** Same WASM, same entities, same API surface. The only difference is two flags (`is_quarter`, `is_capital`) and a `federation_realm_id`.

2. **Federation is an opt-in overlay.** Every quarter is born as a full realm that *chooses* to participate. The federation layer is useful but not load-bearing.

3. **No quarter depends on another to function.** If the capital goes down, quarters keep operating locally. Realm-wide governance pauses but local governance continues.

4. **One frontend serves all quarters.** The frontend is a static SvelteKit app served from a single asset canister. It dynamically switches which backend canister it talks to.

5. **Opting out is frictionless.** Secession = flip a flag. All users, data, governance, extensions remain intact.

---

## Topology

```
                    ┌─────────────────────┐
                    │   1 FRONTEND        │
                    │   (asset canister)  │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
     ┌────────▼───┐  ┌───────▼──────┐  ┌─────▼──────┐
     │ Capital    │  │  Quarter B   │  │ Quarter C  │  ... × N
     │ (Quarter A)│←→│              │←→│            │  (peer gossip)
     │ ~1000 users│  │  ~1000 users │  │ ~1000 users│
     └────────────┘  └──────────────┘  └────────────┘
```

- **Capital** coordinates realm-wide governance but is logically equal to other quarters.
- **Peer gossip** syncs quarter list + population counts between all quarters.
- **Frontend** bootstraps from the capital's canister ID (baked in at build time), then routes dynamically.

---

## What Quarters Share

- **Manifest** (`manifest.json`) — source of truth lives on the capital; quarters hold copies.
- **Extensions** — same set deployed to all quarters.
- **Federation Codex** — realm-wide governance rules (tax policy, voting rules, quarter assignment strategy).

## What Quarters Own Independently

- **Users** — each user has one home quarter.
- **Governance data** — proposals, votes, disputes, etc. local to the quarter.
- **Zones** — potentially same or different geographic zones.

---

## User Model

### Home Quarter (Full Membership)
- User's `User` entity lives here with full profiles and permissions.
- Votes on realm-wide proposals are counted via home quarter.
- Tax obligations apply here.
- Subject to this quarter's justice system.
- On secession, user goes with the quarter.

### Guest Access (Lightweight)
- `GuestUser` entity on non-home quarters (principal + home quarter reference + permissions).
- Can transact, view content, participate in local events.
- No governance weight (no voting, no proposing).
- Severed on secession of either quarter.

### Registration Flow
1. User opens frontend → connects to capital (bootstrap canister ID).
2. Capital runs assignment strategy (least populated / user choice / codex-defined).
3. Capital returns assigned quarter canister ID.
4. Frontend switches actor to the assigned quarter.
5. User registers on the assigned quarter (this is their home).

### Returning User Flow
1. Frontend checks localStorage for cached `home_quarter` canister ID.
2. If cache hit → connect directly to home quarter.
3. If cache miss → call capital's `get_my_user_status()` → get `home_quarter`.
4. If capital unavailable → broadcast query to known quarters (slow fallback).

---

## Assignment Strategies

Defined in the federation codex (`assign_quarter` function). Built-in strategies:

1. **random** — `hash(principal) % len(active_quarters)` → uniform load.
2. **user_choice** — honour user's preference if quarter has capacity.
3. **least_populated** — pick quarter with fewest residents.

Custom codexes can implement arbitrary rules (geography, invitation codes, profile attributes).

---

## Auto-Scaling

When all active quarters exceed `MAX_POPULATION`:
1. Any quarter (or the capital) detects the condition.
2. Creates a new canister via `ic.create_canister()`.
3. Deploys the same WASM with the same manifest/extensions.
4. Announces the new quarter to peers via gossip.
5. New registrations are directed to the new quarter.

---

## Secession

A quarter declares independence:
1. Set `is_quarter = False`, `is_capital = False`, clear `federation_realm_id`.
2. Stop participating in peer gossip.
3. Deploy own frontend asset canister (optional — can reuse existing).
4. All local users, data, governance, extensions remain intact.
5. Former peers remove it from their quarter list.
6. Guest users from/to this quarter lose cross-access.

**Joining a federation** is the reverse: set `is_quarter = True`, configure `federation_realm_id`, start gossip, register with peers.

---

## Data Model Changes

### Realm Entity
```python
# Existing
is_quarter = Boolean(default=False)
federation_realm_id = String(max_length=64)

# New
is_capital = Boolean(default=False)  # This quarter coordinates federation governance
```

### User Entity
```python
# New
home_quarter = String(max_length=64)  # Canister ID of user's home quarter
```

### GuestUser Entity (New)
```python
class GuestUser(Entity):
    principal = String()           # Visitor's IC principal
    home_quarter = String()        # Where they actually live
    permissions = String()         # What they can do here
```

### Quarter Entity (Existing — No Changes Needed)
```python
class Quarter(Entity, TimestampedMixin):
    name = String()
    canister_id = String()         # Backend canister principal
    federation = ManyToOne("Realm", "quarter_ids")
    population = Integer(default=0)
    status = String(default="active")  # active/suspended/splitting/merging
```

---

## API Changes

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `join_realm(profile, preferred_quarter)` | Persist `home_quarter` on User entity after assignment |
| `get_my_user_status()` | Return stored `home_quarter` instead of `""` |
| `change_quarter(new_quarter_canister_id)` | Persist new `home_quarter` on User entity |

### New Endpoints

| Endpoint | Purpose |
|----------|---------|
| `declare_independence()` | Secede from federation |
| `join_federation(capital_canister_id)` | Join an existing federation |
| `sync_quarters()` | Peer gossip: exchange quarter list + populations |
| `register_guest(principal, home_quarter)` | Create GuestUser for cross-quarter access |

---

## Frontend Changes

1. **Auto-routing on login** — after `get_my_user_status()`, call `setActiveQuarter(home_quarter)`.
2. **Two-step join** — register on capital, get assignment, register on assigned quarter.
3. **Guest mode** — `QuarterSelector` already exists; tag non-home quarters as "guest" in the UI.
4. **localStorage cache** — persist `home_quarter` canister ID for instant reconnect.

---

## Implementation Phases

### Phase 1: Core Loop (High Priority)
- Add `is_capital` to Realm entity
- Add `home_quarter` to User entity
- Fix `join_realm()`, `get_my_user_status()`, `change_quarter()` to persist/read `home_quarter`
- Frontend auto-routing on login
- Frontend two-step join flow

### Phase 2: Federation (Medium Priority)
- GuestUser entity + `register_guest` endpoint
- Peer gossip (`sync_quarters` inter-canister calls)
- `declare_independence()` / `join_federation()` endpoints
- CLI `--capital` flag for `quarter create`

### Phase 3: Automation (Low Priority)
- Auto-provisioning new quarters at capacity
- Optional QuarterRouter canister (cache/accelerator, not required)
