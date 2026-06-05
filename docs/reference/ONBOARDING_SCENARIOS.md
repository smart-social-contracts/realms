# Onboarding Scenarios & Dashboard Profiles

This document defines **how realms onboard people** and **how public and member dashboards should adapt** to different governance contexts — from a greenfield digital community to digitizing an existing municipality, and from a Swiss commune to a megacity in China.

It complements [Realm Lifecycle Stages](./REALM_LIFECYCLE.md) (what stages exist) with **who may join, how stages advance, and what visitors vs members should see**.

> **Status:** Product specification. Most hooks below are **not yet implemented** in `public_dashboard` / `member_dashboard`; today those extensions use a single layout with hard-coded copy (Syntropia-style greenfield). This doc is the target contract for codex + manifest configuration.

---

## Two foundational scenarios

These are the primary **territory modes**. Every deployed realm should declare one (via manifest / codex init).

| Dimension | **New territory** (`greenfield`) | **Current territory** (`incumbent`) |
|-----------|----------------------------------|-----------------------------------|
| **Starting point** | No existing public administration on Realms; founder bootstraps legitimacy | Existing state/municipal PA; member of that body initiates migration |
| **Admin onboarding** | Founder invites admins — **invitation code only** | Incumbent official invites civil servants / admins — **invitation code only** |
| **Member onboarding** | Invitation code **or** open registration (`open_registration`) | **Invitation code only** — no open access |
| **Alpha → Beta** | Milestones: registered members, deposits/fees paid, other codex-defined gates | Milestones: registered officials/members, operational readiness — often **no** mass refundable-deposit model |
| **Beta → Live (Production)** | Typically **governance vote** (admins and/or all members per codex) | **Founder + founding admins approval**, or vote limited to admin cohort — reflects legal continuity, not crowd-founding |
| **Why the difference** | Legitimacy is **earned** from participants; open signup builds critical mass | Legitimacy is **inherited** from law; gatekeeping prevents impersonation and unauthorized “citizens” |

**Naming in code today:** stages use `production` (UI may label it “Live”). Territory mode is proposed as `manifest_data.onboarding.territory_mode`: `"greenfield"` | `"incumbent"`.

---

## Regional & scale archetypes (brainstorm)

Realms are not only “new vs incumbent.” Operators need **dashboard profiles** that reflect local law, identity systems, fiscal models, language, and citizen expectations. Below are **archetypes** — a realm can pick one profile or blend fields from several.

### Comparison matrix

| Archetype | Scale | Typical mode | Identity / trust | Money & milestones | Public dashboard emphasis | Member dashboard emphasis |
|-----------|-------|--------------|------------------|--------------------|---------------------------|---------------------------|
| **Swiss commune** | 500–15k | Incumbent | e-ID / strong KYC; multilingual (DE/FR/IT/RM) | Tax bills, communal fees; referendum culture | Transparency: budgets, council minutes, open data KPIs | Taxes, permits, local votes, bilingual notices |
| **EU town (e.g. Sotamritca-style)** | 5k–80k | Incumbent or greenfield pilot | EU ID / passport ZK; GDPR-first | VAT-style levies, EU grant reporting | GDPR notice, service catalog, lifecycle for pilot zones | Welfare hooks, case status, invoice payment (SEPA) |
| **African municipality** | 20k–2M | Often incumbent digitization | Mobile-first; SIM/National ID; optional ZK later | Mobile money (M-Pesa, etc.); lower deposit thresholds | SMS/USSD hints, service hours, offline-friendly stats | Mobile payment accounts, service requests, low-bandwidth inbox |
| **Chinese city district** | 100k–10M+ | Incumbent | Real-name verification; mandated ID linkage | Integrated payments; department-centric | Policy announcements, department grid, **no** open join CTA | Appointment slots, permit pipeline, department messaging |
| **Greenfield eco-community** | 1k–50k (target) | Greenfield | ZK passport / personhood (Rarimo) | Refundable deposits, critical mass | Critical mass bar, manifesto, land/zone map | Deposit status, citizenship activation checklist |
| **DAO / digital-only** | Unbounded | Greenfield | Wallet + optional proof-of-person | Token stake, no land checklist | Token metrics, proposal heatmap | Voting weight, treasury, delegation |
| **Megacity (layer-2 quarter)** | Millions via quarters | Incumbent + federation | Federated identity per quarter | Per-quarter tax; capital aggregates | Quarter map, capital vs borough stats | Home quarter, guest access, cross-quarter services |

### Requirement axes (what varies)

Use these axes when configuring a realm — each axis drives **which dashboard blocks appear** and **which onboarding gates apply**.

1. **Territory mode** — `greenfield` | `incumbent` (table above).
2. **Registration policy** — `invite_only` | `open_members` (admins always invite-only in core `join_realm`).
3. **Stage transition policy** — `auto_milestones` | `admin_approval` | `member_vote` | `admin_vote` (combinable per transition).
4. **Milestone set** — e.g. `member_count`, `deposit_total`, `admin_count`, `departments_configured`, `identity_provider_live`, `land_acquired` (see [Realm Lifecycle](./REALM_LIFECYCLE.md)).
5. **Identity stack** — `none` | `invoice_only` | `passport_zk` | `national_id` | `eidas` | `real_name_mandatory`.
6. **Payments** — `ICP` | `SEPA` | `mobile_money` | `fiat_offline` — drives member dashboard payment widgets.
7. **Language** — single vs `manifest_data.languages[]` (hero, welcome, manifesto per locale on public dashboard).
8. **Transparency level** — `full_public_kpis` | `aggregates_only` | `minimal` (incumbent may hide user counts until live).
9. **Geography** — `zones_map` | `single_boundary` | `none` (digital-only).
10. **Governance visibility** — `proposals_public` | `members_only` | `admins_only` during alpha.

---

## Dashboard hooks (proposed contract)

Configuration should live in **`Realm.manifest_data`** under `onboarding` and `dashboard`, set at realm creation (registry wizard) or by codex `init.py`. Extensions read it via `status()` or `get_realm_stage` / a dedicated `get_realm_profile` call.

### Schema sketch

```json
{
  "onboarding": {
    "territory_mode": "greenfield",
    "registration": {
      "open_registration": false,
      "admin_requires_invite": true,
      "member_requires_invite": true
    },
    "lifecycle_transitions": {
      "alpha_to_beta": { "mode": "auto_milestones", "milestones": ["member_count", "deposit_total"] },
      "beta_to_production": { "mode": "member_vote", "quorum": 0.5, "majority": 0.5 }
    },
    "identity_requirements": ["passport_zk", "registration_invoice_paid"]
  },
  "dashboard": {
    "profile": "swiss_commune",
    "public": {
      "hero": { "show_join_cta": true, "join_label": "Join this Realm" },
      "sections": ["lifecycle", "milestones", "kpi_strip", "zones_map", "manifesto", "transparency_feed"],
      "lifecycle": {
        "stage_labels": { "production": "Live" },
        "show_critical_mass": true,
        "show_deposit_checklist": false,
        "show_readiness_checklist": ["departments_configured", "identity_provider_live"]
      },
      "kpi_strip": ["users", "proposals", "votes", "budget_executed"],
      "locale_fallback": "en"
    },
    "member": {
      "sections": ["greeting", "activation_checklist", "notifications", "invoices", "services", "votes_pending"],
      "activation_checklist": ["invoice_paid", "passport_verified", "profile_complete"],
      "hide_payments_until": "beta"
    }
  }
}
```

### Public dashboard (`public_dashboard` extension)

**Today:** Hero (logo, name, welcome, manifesto), fixed lifecycle card (critical mass, deposit/land/infrastructure checklist), KPI strip (users, orgs, proposals, votes, transfers, zones), zones map, “Join this Realm” → `/join`.

**Hook points to add:**

| Block ID | Purpose | Typical greenfield | Typical incumbent |
|----------|---------|--------------------|-------------------|
| `hero` | Branding + CTA | Join CTA visible if alpha/beta + open or “request invite” | “Official portal” — CTA hidden or “Employee / citizen login” only |
| `lifecycle` | Stage track + copy | `show_critical_mass`, deposit checklist | Readiness checklist (departments, legal notice), no deposit bar |
| `milestones` | Custom progress bars | Members + deposits | Admins onboarded + services configured |
| `kpi_strip` | Public stats | All KPIs | Aggregates only; hide user list until production |
| `zones_map` | Geography | Land interest / H3 zones | Administrative boundaries |
| `transparency_feed` | Open data | Optional | Budget summaries, council decisions (links) |
| `trust_notice` | Legal / GDPR | Light | Prominent privacy + official disclaimer |
| `language_switcher` | i18n | If multi | Swiss / EU / China: often mandatory |

**Per-archetype public face (sketch):**

- **Swiss commune:** Hero with coat of arms; lifecycle in **Live** shows budget execution KPI; DE/FR toggle; no member count until policy allows; link to open data.
- **Sotamritca / EU town:** Pilot lifecycle if greenfield zone; GDPR banner; SEPA-relevant copy on join path; welfare/dept links in footer blocks.
- **African municipality:** Mobile-first hero; milestones as “services online”; KPI strip emphasizes **service requests resolved** not on-chain transfers; optional USSD info panel.
- **Chinese city district:** Department grid instead of western “proposals/votes” KPIs; real-name registration notice; no public join — “登录 / Log in” only; policy announcement carousel.
- **Greenfield eco-community:** Current UI is closest — critical mass, deposits, zone map, manifesto, Join CTA.

### Member dashboard (`member_dashboard` extension)

**Today:** Greeting, citizenship status (invoice + passport), notifications, invoices, payment accounts, services — largely **one-size-fits-all**.

**Hook points to add:**

| Block ID | Purpose | Varies by |
|----------|---------|-----------|
| `activation_checklist` | Steps before “active citizen” | Identity stack (invoice only vs ZK vs national ID) |
| `role_banner` | Admin vs member vs guest | Profile |
| `invoices` / `payments` | Registration fee, taxes | Payment rails |
| `services` | Assigned public services | Department/codex |
| `votes_pending` | Governance tasks | Only if `governance_visibility` allows |
| `deposit_wallet` | Refundable alpha deposit | Greenfield only |
| `department_inbox` | Internal PA messaging | Incumbent large orgs |
| `quarter_switcher` | Home vs guest quarter | Federation |

**Per-archetype member face (sketch):**

- **Swiss commune:** Tax record summary, communal invoice (SEPA), referendum alerts, citizenship = active when municipal ID linked.
- **EU town:** GDPR consent step in checklist; welfare/justice cards if extensions installed.
- **African municipality:** Mobile money as default payment network; service request status prominent; SMS notification preference.
- **Chinese city district:** Real-name verification gate; appointment booking widget; minimal governance voting in UI until policy allows.
- **Greenfield:** Deposit status + critical mass contribution; passport ZK; path to vote on go-live.

---

## Lifecycle transitions by scenario

| Transition | Greenfield (default) | Incumbent (default) |
|------------|----------------------|---------------------|
| **Alpha → Beta** | Auto at `critical_mass` and/or deposit threshold; optional member vote | Admin-defined milestones (e.g. N admins, core departments created) |
| **Beta → Production** | Governance proposal — all members or all admins per codex | Founder + super-admin quorum OR designated civil-service board |
| **Copy on public dashboard** | “Path to next phase: X of Y members” | “Readiness: 4/5 departments connected” |

Codices (Syntropia, Dominion, Agora) remain the **execution layer** for milestones and votes; `dashboard.profile` only controls **presentation**.

---

## Implementation roadmap (suggested)

1. **Document & manifest** — Set `onboarding` + `dashboard` in realm creation manifest (registry wizard presets per archetype).
2. **`get_realm_profile` API** — Expose merged manifest + status in `status()` or realm_settings.
3. **Public dashboard** — Read `dashboard.public.sections` and stage config; conditional render; i18n for `stage_labels` and hero CTA.
4. **Member dashboard** — Read `dashboard.member.sections` and `activation_checklist`; codex can extend checklist via extension callback.
5. **Join flow** — `/join` reads `onboarding.registration` (already partially via `open_registration`).
6. **Preset library** — `greenfield_default`, `incumbent_municipality`, `swiss_commune`, `china_district`, … in docs and registry UI.

---

## Related documentation & code

| Topic | Location |
|-------|----------|
| Lifecycle stages | [REALM_LIFECYCLE.md](./REALM_LIFECYCLE.md) |
| Open vs invite registration | `join_realm` in `src/realm_backend/main.py`; create-realm wizard `open_registration` |
| Public dashboard UI | `extensions/extensions/public_dashboard/frontend-rt/src/PublicDashboard.svelte` |
| Member citizenship checks | `extensions/extensions/member_dashboard/backend/entry.py` → `get_citizenship_status` |
| Codex lifecycle logic | `codices/codices/*/realm_lifecycle.py` |
| Genesis founder onboarding (planned) | [ROADMAP.md](../../ROADMAP.md) — one-click realm creation |

---

## Open questions (for product review)

1. Should **incumbent** realms ever allow `open_registration` for a subset of services (e.g. tax filing only) while keeping governance invite-only?
2. Is **“Sotamritca”** a codename for a specific pilot (EU + greenfield zone), or always incumbent?
3. For **China-scale** realms, is Realms the system of record or a transparency layer on top of existing stacks — affects which KPIs are honest to show publicly.
4. Should dashboard profiles be **marketplace codex metadata** (install Syntropia → get Syntropia dashboard defaults) or independent manifest overrides?

---

## Summary

- **Two territory modes** explain *why* invite rules and go-live votes differ (legitimacy earned vs inherited).
- **Regional archetypes** explain *what* citizens expect to see (taxes vs deposits vs departments vs mobile money).
- **Dashboard hooks** let each realm compose public and member UIs without forking the extensions — configuration drives sections, labels, milestones, and CTAs.

Next implementation step: add manifest presets to the create-realm flow and teach `public_dashboard` / `member_dashboard` to read `manifest_data.dashboard` (fallback to today’s layout when absent).
