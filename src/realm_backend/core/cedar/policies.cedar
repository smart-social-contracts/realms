// The realm's ordinary policy set: who may do what, as distinct from the
// rules in guardrails.cedar that must hold no matter what.
//
// The distinction matters. A `forbid` in the guardrails cannot be overridden
// by anything, so it is the wrong place for a decision a realm might
// legitimately want to change. These permits are ordinary rules: a realm
// admin tightens them, and when one is wrong the fix is an edit, not a
// canister upgrade.
//
// Cedar is deny-by-default: without a matching permit a call is refused, and
// with no permit at all the realm refuses everything. So this file exists to
// restore the baseline a realm already had before Cedar — users can act, with
// no policy here granting an extension anything the guardrails do not already
// keep it from.

// Host-originated calls carry no `context.extension`, so this covers the host
// and leaves extension calls to the guardrails. The realm's own Python checks
// still run downstream; this is the authorization floor, not the ceiling.
permit (
    principal,
    action,
    resource
)
when { !(context has extension) };

// Extensions may read ordinary realm data. Scoped to `read` on purpose: a
// write from an extension is what guardrail G1 refuses outright, and reads of
// authorization data (profiles, permissions) are what G2 refuses. Everything
// left over is the data a realm exists to share.
//
// This is the baseline, not the end state. A realm that does not want
// extensions browsing its data removes this and grants reads per verb or per
// entity instead.
permit (
    principal,
    action in [Realm::Action::"read"],
    resource
)
when { context has extension };
