# Cedar policy for the realm

Authorization rules as data rather than as Python scattered across verbs, so
that an extension can ship its own rules without shipping host code.

**Not yet live.** Nothing in the realm builds a Cedar request today. The schema,
the guardrails and the call-origin plumbing are all in place and tested, but the
decision point is blocked on
[ic-python-db#13](https://github.com/smart-social-contracts/ic-python-db/issues/13):
Cedar needs to read entities directly from the stable map in Rust, and that
depends on a storage format with field-level random access. Going through Python
costs ~10.1M instructions for 12 records, which is not a real option.

## What's here

| File | |
|---|---|
| `realm.cedarschema` | Generated from the live entity definitions. Do not hand-edit. |
| `guardrails.cedar` | The three rules no installed policy can weaken. |

Regenerate the schema with `scripts/generate_cedar_schema.py --write`; the
`--check` mode fails when it drifts from the entity definitions.

## Writing policies: guard every attribute access

Every generated attribute is optional, because the ORM omits unset fields from a
stored row rather than storing nulls. Cedar's strict validation therefore
rejects any unguarded access. This does not validate:

```cedar
when { resource.vendor_id == principal.id }
```

It has to be written:

```cedar
when {
    resource has vendor_id
    && principal has id
    && resource.vendor_id == principal.id
}
```

The payoff is that a policy cannot fail at decision time on missing data, which
matters when the alternative is an authorization check erroring inside a call
that has already done work. The cost is verbosity, and an error message that
doesn't obviously point at the fix — expect this to be the first thing a policy
author trips over.

## Why an extension's policy can't reach core data

An extension's policy is validated against a schema containing only its own
namespace (`ext_<name>`, matching its storage namespace) plus `Realm::User` as
the principal. Its actions are declared inside that namespace and apply only to
its own resource types.

So containment is the type checker's job, not a reviewer's. A policy naming
`Realm::UserProfile`, or another extension's types, has no applicable action and
fails to validate at install time.

This is also why `permit (principal, action, resource);` from an extension is
harmless: the schema bounds what "everything" refers to, so it grants that
extension full access to its own data and nothing else. We don't need to detect
dangerous policies, because they can't be expressed.

The deliberate exception is role membership — `principal in
Realm::UserProfile::"admin"` does validate, so an extension can say "only realm
admins may do this here" without being able to reach a profile as a resource.
Guardrail G2 still blocks reading profile data at decision time.
