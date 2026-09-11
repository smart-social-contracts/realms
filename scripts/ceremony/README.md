# Key ceremony — moved

The air-gapped YubiKey PIV key ceremony now lives in its own **private** repo:

**https://github.com/smart-social-contracts/key-ceremony**

```bash
git clone git@github.com:smart-social-contracts/key-ceremony.git
```

Nothing about the ceremony is Realms-specific — environments, device models,
touch policies and copy counts all come from `ceremony-config.json` — so it was
extracted and made project-agnostic. The git history of this directory came
along with it.

## What the ceremony produces

IC operator identities held in YubiKey PIV slot `9c`, usable as HSM-backed dfx
identities. No PEM ever leaves the ceremony:

```bash
dfx identity new ceremony-prod \
  --hsm-key-id 02 \
  --hsm-pkcs11-lib-path /usr/lib/x86_64-linux-gnu/libykcs11.so
export DFX_HSM_PIN='<PIV PIN>'
```

The resulting principal must match the `principal` recorded in the ceremony's
`manifest.json`. Verify a key with `verify-yubikeys.sh` from that repo.

## Renamed entry points

| Was (here) | Now (key-ceremony repo) |
|---|---|
| `realms-key-ceremony.sh` | `key-ceremony.sh` |
| `/opt/realms-ceremony` | `/opt/key-ceremony` |
| `/run/realms-ceremony` | `/run/key-ceremony` |
| 9p mount tag `realms_ceremony` | `key_ceremony` |

Those values are baked into any ISO built from the old tree, so rebuild the
bootstrap ISO once after switching.
