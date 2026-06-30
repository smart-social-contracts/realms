# Principal delegation (Power of Attorney)

Scoped **act-on-behalf** grants between two registered realm users. Distinct from
**role delegation** in [ACCESS_CONTROL.md](./ACCESS_CONTROL.md) (department heads
assigning profiles via `delegate:<profile>` permissions).

## Model

| Field | Meaning |
|---|---|
| **Grantor** | User whose rights are exercised (`User.id` = principal) |
| **Delegate** | User who signs calls (`ic.caller()`) |
| **Scope** | JSON: `{"operations": ["proposal.vote", …]}` or `{"all": true}` |
| **Status** | `pending` → `active` → `revoked` / `expired` |

Authentication is always the delegate's Internet Identity (or agent key). The
backend validates an active delegation and applies business logic to the
**grantor's** `User` when `on_behalf_of` is set in JSON args.

## API (realm backend)

| Method | Type | Description |
|---|---|---|
| `grant_delegation_json` | update | Create delegation; caller = grantor or admin |
| `accept_delegation_json` | update | Delegate accepts `pending` grant |
| `revoke_delegation_json` | update | Grantor, delegate, or admin revokes |
| `list_delegations_json` | query | Lists for caller as grantor/delegate |

Grant payload example:

```json
{
  "grantor": "ufptc-evwin-…",
  "delegate": "abc12-…",
  "scope": { "operations": ["proposal.vote", "proposal.create"] },
  "label": "Alice operates swarm_agent_001",
  "expires_in_hours": 168,
  "requires_acceptance": true
}
```

Delegated extension call (voting):

```json
{
  "proposal_id": "…",
  "vote": "yes",
  "on_behalf_of": "ufptc-evwin-…"
}
```

## Frontend

- `/delegations` — inbox, accept/decline, revoke
- Navbar **DelegationSwitcher** — session-scoped acting context
- **DelegationBanner** when not acting as self
- `withDelegationArgs()` / `withDelegationJson()` in `$lib/stores/delegation.js`

## Geister

```python
grant_delegation(
    grantor="<agent-principal>",
    delegate="<your-II-principal>",
    scope={"operations": ["proposal.vote", "proposal.create"]},
    identity="swarm_agent_001",
    realm_principal="3eotx-…",
)
```

## Rules

1. Delegation cannot exceed grantor's permissions at grant time.
2. Grantor and delegate must both be registered users.
3. Votes and other writes record grantor as subject; delegate in vote `metadata`.
4. Token transfers require separate ICRC-2 allowance (not covered by realm delegation).

## Test mode

`test_mode_ii_bypass` / PEM URL login is **not** used for production delegation.
Use real II for the delegate and grant from the agent via `grant_delegation`.
