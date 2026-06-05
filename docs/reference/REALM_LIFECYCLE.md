# Realm Lifecycle Stages

Every realm progresses through a defined sequence of lifecycle stages. The current stage is visible to all members on the public dashboard and can be managed by admins from **Administration → Realm Settings**.

For **who may join**, **how stages advance** (vote vs admin approval), and **how dashboards should differ** by territory type (new vs existing public administration) or region, see [Onboarding Scenarios & Dashboard Profiles](./ONBOARDING_SCENARIOS.md).

---

## Stages

| Stage | Name | Description |
|-------|------|-------------|
| 1 | **Alpha** | Gathering interest. Community is forming, deposits are fully refundable. No commitments made. |
| 2 | **Beta** | Preparing for launch. Deposits are locked, land and infrastructure acquisition is underway. Governance is active. |
| 3 | **Production** | Realm is live. Members have moved in, services are operational, the community is self-sustaining. |
| 4 | **Deprecation** | Winding down. No new members accepted. Existing members are transitioning out, deposits are being refunded. |
| 5 | **Terminated** | Realm has closed. All operations have ceased. |

---

## Rules

- **Forward-only**: stages can only advance in order — you cannot go back.
- **No skipping**: you must pass through each stage in sequence (Alpha → Beta → Production → Deprecation → Terminated).
- **Beta locks deposits**: when a realm advances to Beta, member deposits are locked as a signal of commitment to the project.

---

## Advancing a Stage

Realm administrators can advance the stage from **Administration → Realm Settings**, in the **Realm Lifecycle** section.

- If you have direct admin permissions, the advancement executes immediately.
- Otherwise, it creates a **governance proposal** for the realm to vote on, following the standard proposal flow.

When proposing a stage advancement, you can provide a reason that will be recorded in the lifecycle history.

---

## Lifecycle Metrics (Alpha → Beta)

During Alpha, the Lifecycle card tracks readiness indicators:

| Metric | Description |
|--------|-------------|
| **Registered Users** | Current number of registered users in this realm. |
| **Critical Mass** | Target user count the realm aims to reach before advancing. Configurable via `manifest_data.lifecycle.critical_mass`. |
| **Deposits Locked** | Whether member deposits have been locked (set automatically when entering Beta). |
| **Progress** | Registered Users ÷ Critical Mass, expressed as a percentage. |

---

## History

Every stage transition is recorded with a timestamp and reason, accessible via the backend's `get_realm_stage` extension call (`lifecycle.history`).

---

## For Developers

The lifecycle stage is stored in `Realm.status` (a string field on the core GGG entity). Extended metadata (critical mass, history, readiness flags) lives in `Realm.manifest_data` as a JSON string under the `lifecycle` key.

The stage is exposed in:
- `status()` API response as `realm_stage` — used by the realms registry for filtering/display.
- `realm_settings` extension: `get_realm_stage` / `set_realm_stage` methods via `extension_sync_call`.
