# Quarters: Federation Through a Shared Codex

## Overview

A **realm is a set of quarters that run the same codex.** The codex is the realm's constitution — it encodes every policy: admission, fees, governance, taxation, justice, assignment. Quarters are sovereign demoi (each home to up to a few thousand users) that belong to a realm because their users collectively choose to adopt its codex.

The whole architecture reduces to one primitive:

> **A realm is a shared codex. The capital quarter is its origin and pusher. Admission = receive the codex. Governance = amend the codex. Dissent = fork. Secession = drop the codex.**

Everything else — capital, fees, taxation, reputation — is policy *inside* the codex, not load-bearing infrastructure.

---

## Terminology

| Term | Definition |
|------|-----------|
| **Quarter** | A full, sovereign realm backend canister, home to up to a few thousand users. Holds its own users, governance data, and extensions. Acts as a collective entity via its codex (decisions made by its users' votes). |
| **Realm** | The set of quarters running the same codex. Membership *is* codex-adherence. |
| **Codex** | The shared constitution of a realm. Encodes all policy. Distributed from the capital on admission and on amendment. |
| **Capital** | The quarter that is the codex's origin and pusher, and the gate for admission. It is still an ordinary quarter (holds users, runs governance). Its only realm-wide powers are **admission** and **codex propagation** — both disciplined by every quarter's freedom to secede. |
| **Secession** | A quarter dropping the codex and ceasing to sync. Frictionless: all users and data stay with the quarter. |
| **Fork** | A contentious amendment splits the realm: quarters on the new codex and quarters on the old codex are, by definition, now two realms. Dissent is automatic and frictionless. |

---

## Design Principles

1. **A quarter IS a realm backend.** Same WASM, same entities, same API surface. A quarter is distinguished only by flags (`is_quarter`, `is_capital`) and the codex it runs.

2. **The codex defines the realm.** Two quarters are in the same realm iff they run the same codex. No shared codex, no shared realm.

3. **Quarters are sovereign.** No quarter depends on another to function. Users register directly on the quarter they choose and pay that quarter's fees. There is no global user registry and no cross-quarter "guest" presence — to participate in another quarter, you register there.

4. **The capital is a pusher, not a ruler.** Its two central functions (admission, codex propagation) are real but bounded: any quarter can secede at any time, so the capital's power is continuously re-tested by the exit option.

5. **Centralization is allowed where users tolerate it.** If a realm's codex encodes a strong capital — even a monarchy — and users keep choosing it, that is a legitimate outcome. The system stays neutral; the codex carries the values.

6. **Opting out is frictionless.** Secession = drop the codex and stop syncing. All users, data, governance, and extensions remain intact.

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
     │ (codex      │→ │  (runs codex)│  │(runs codex)│
     │  origin)    │  │              │  │            │
     │ ≤ few k     │  │  ≤ few k     │  │ ≤ few k    │
     └────────────┘  └──────────────┘  └────────────┘
        admission +        sovereign        sovereign
        codex push
```

- The **capital** originates and pushes the codex, and gates admission.
- Each **quarter** is otherwise sovereign: its own users, governance, fees.
- The **frontend** is one static SvelteKit asset canister that dynamically switches which backend quarter it talks to. It bootstraps from the capital's canister ID (baked in at build time).

---

## The Codex

The codex is the only thing quarters of a realm share. It encodes, at minimum:

- **Admission policy** — who may join the realm, and on what terms.
- **Fee policy** — registration and maintenance fees per quarter, ideally set by supply/demand and technical constraints. Fees are the natural assignment mechanism: users register where they choose and pay accordingly.
- **Governance** — how proposals are made, who votes, how amendments are ratified.
- **Capital policy** — whether and how capital-hood can move (advocated: by realm-wide vote across all quarters).
- **Taxation/tributes (optional)** — the codex may require quarters to pay tributes to the capital. This is allowed but not built-in; absence of tribute policy means no tribute.
- **Justice, duplicates, sanctions** — how cross-quarter misbehaviour (e.g. duplicate registrations) is detected and punished. Detection is ex-post and codex-driven, analogous to how analog societies handle it — not prevented by central infrastructure.

There is no quantized, system-level reputation. Reputation is whatever a subject infers about another from available records; the codex (and users) decide what to do with it.

---

## Users

- A user registers directly on the quarter of their choice and pays that quarter's fees.
- A user is present only on quarters where they have registered. There is **no GuestUser** and no seamless cross-quarter presence — visiting another quarter means registering there.
- Duplicate identities across quarters are not prevented by infrastructure. They are detected after the fact and sanctioned per the codex if disallowed.

---

## Admission

1. A prospective quarter requests admission from the capital.
2. The capital applies the realm's codex admission policy.
3. On acceptance, the quarter **receives the codex** and begins running it. It is now part of the realm.

Admission is the capital's gate. Whether a previously-seceded quarter re-enters with its prior history or cold is up to the codex.

---

## Governance: Amendment, Fork, Secession

- **Amendment.** The capital pushes codex amendments. Ratification follows the codex's own rules (advocated: realm-wide vote involving all quarters). A fast sync mechanism propagates the new codex; transient version skew during rollout is handled by syncing, not by special-casing.

- **Fork (dissent).** Because "same codex = same realm," a quarter that rejects an amendment is — by definition — running a different codex, hence a different realm. A contentious amendment therefore *splits* the realm rather than coercing a minority. A realm-wide vote is thus a **coordination signal** (which codex version keeps the most quarters together), not an enforcement act.

- **Secession.** A quarter drops the codex and stops syncing. All its users and data remain intact. Former peers remove it from the realm. This is the only hard check in the system, and it disciplines the capital's admission and propagation powers.

---

## Data Model

### Quarter Entity
```python
class Quarter(Entity, TimestampedMixin):
    name = String()
    canister_id = String()         # backend canister principal
    federation = ManyToOne("Realm", "quarter_ids")
    population = Integer(default=0)
    status = String(default="active")  # active/suspended/splitting/merging
```

### Realm Flags
```python
is_quarter = Boolean(default=False)
is_capital = Boolean(default=False)   # codex origin + admission gate
federation_realm_id = String(max_length=64)
codex_version = String(max_length=64) # current codex version this quarter runs
```

No `home_quarter` on users, no `GuestUser` entity, no central tax aggregator. Those are removed from the model; any equivalent behaviour, if desired, lives in the codex.

---

## Frontend

1. **Bootstrap** from the capital's canister ID (baked in at build time).
2. **Quarter selection** — the user picks/registers on a quarter; the frontend switches its actor to that quarter's backend.
3. **localStorage cache** — remember the user's quarter canister ID for instant reconnect.

---

## What Changed From the Earlier Design

This document supersedes an earlier, heavier design. Removed or reframed:

- **GuestUser / cross-quarter guest presence** — removed. Participation requires registration on the target quarter.
- **Central tax aggregation** — removed as a built-in; optional tributes can be encoded in the codex.
- **`home_quarter` on User** — removed; users simply register where they choose.
- **Built-in random assignment** — removed as a default; assignment is governed by codex fee policy (supply/demand).
- **Capital as governance coordinator** — reframed: the capital is the codex origin + admission gate + pusher, nothing more.
- **Quantized reputation** — removed; reputation is interpretive and codex/user-driven.
