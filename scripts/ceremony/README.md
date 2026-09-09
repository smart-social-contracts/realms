# Realms YubiKey key ceremony

Air-gapped key generation for dev and prod IC operator identities. **No PEM files leave the ceremony** — keys are imported into YubiKey PIV slot `9c` (PKCS#11 id `02` for `dfx identity --hsm-key-id`).

**Target environment:** Ubuntu **22.04 Desktop** live USB — boot "Try Ubuntu", run the ceremony, power off. Do not install Ubuntu to disk.

## Hardware plan

| Environment | Device | Touch policy |
|---|---|---|
| test / staging / demo | YubiKey 5C Nano | `never` |
| production | 3× YubiKey 5 NFC (clones) | `cached` (touch required, buffered per session) |

CI is unchanged — still uses existing PEM secrets.

## Ceremony flow (Ubuntu 22.04 Desktop live USB)

1. **Boot the Desktop live USB** on the laptop (initially online; choose **Try Ubuntu**).
2. Copy `scripts/ceremony/` onto the live session (second USB stick or `scp`).
3. **Online:**
   ```bash
   sudo ./realms-key-ceremony.sh online-setup
   ```
4. **Disconnect all network** (Wi‑Fi off, Ethernet unplugged).
5. **Offline:**
   ```bash
   sudo ./realms-key-ceremony.sh check-offline
   sudo ./realms-key-ceremony.sh offline-generate
   sudo ./realms-key-ceremony.sh provision-dev      # insert dev Nano
   sudo ./realms-key-ceremony.sh provision-prod      # insert each prod NFC (3×)
   sudo ./realms-key-ceremony.sh finalize
   ```
6. **Copy out** (second USB stick):
   - `artifacts/manifest.json` (public principals + metadata)
   - Record `secrets/operator-credentials.txt` on paper (PIN / PUK / management key).
7. **Destroy:**
   ```bash
   sudo ./realms-key-ceremony.sh destroy
   ```
8. Power off — **do not install** Ubuntu to the laptop disk.

Or run steps 5–6 in one shot after `check-offline`:

```bash
sudo ./realms-key-ceremony.sh run-offline
```

### Optional: export a dfx-style PEM (dev only, transitional)

The default ceremony **never** leaves PEMs on disk — keys go to YubiKey and `destroy` shreds the workspace. If you need a plaintext `identity.pem` (e.g. `~/.config/dfx/identity/non_production_controller_identity/`) for a transitional dev controller, opt in **after** `offline-generate` and **before** `destroy`:

```bash
export CEREMONY_EXPORT_PEM_I_UNDERSTAND=1
sudo -E ./realms-key-ceremony.sh export-pem dev ~/.config/dfx/identity/non_production_controller_identity
# or: export-pem dev /path/to/identity.pem
icp identity import non_production_controller_identity \
  --from-pem ~/.config/dfx/identity/non_production_controller_identity/identity.pem \
  --storage plaintext
```

**Do not use this for production.** Prefer YubiKey HSM identities from `artifacts/operator-dfx-identity.txt`.

## Testing before the real ceremony

### Recommended: Ubuntu 22.04 Desktop official ISO in a VM

Boots the same **Desktop live ISO** you will use on the USB stick (not Server, not Docker).

```bash
cd scripts/ceremony
chmod +x vm/run-ubuntu-2204-vm-test.sh vm/guest-run-test.sh realms-key-ceremony.sh
./vm/run-ubuntu-2204-vm-test.sh
```

First run downloads [ubuntu-22.04.5-desktop-amd64.iso](https://releases.ubuntu.com/22.04/ubuntu-22.04.5-desktop-amd64.iso) (~5 GB) into `vm/cache/`, boots **Try Ubuntu** in QEMU, enables SSH via cloud-init, then runs:

- `online-setup` (real `apt` packages: `ykman`, `ykcs11`, `icp-cli`, …)
- network gate (`check-offline` must fail while online)
- simulate offline ceremony (no YubiKey required)
- manifest validation

Typical runtime: **20–35 minutes**. Use `--keep-vm` to inspect the live session:

```bash
ssh -i vm/cache/test_id_rsa -p 2222 ubuntu@127.0.0.1
```

### Quick smoke test (Docker)

Faster but **not** a substitute for the Desktop VM test — script logic only:

```bash
docker build -t realms-ceremony-test -f docker/Dockerfile .
docker run --rm realms-ceremony-test
```

## Operator workstation (after ceremony)

```bash
dfx identity new realms-dev \
  --hsm-key-id 02 \
  --hsm-pkcs11-lib-path /usr/lib/x86_64-linux-gnu/libykcs11.so
export DFX_HSM_PIN='<PIV PIN>'
dfx identity get-principal --identity realms-dev
```

Use `realms-prod` for production keys. Principals must match `manifest.json`.

## Environment variables

| Variable | Purpose |
|---|---|
| `CEREMONY_SIMULATE=1` | Software-only (tests without YubiKey) |
| `CEREMONY_FORCE_OFFLINE=1` | Skip network-off check |
| `CEREMONY_PIV_RESET=1` | Factory-reset PIV before import (destructive) |
| `CEREMONY_ROOT` | Workspace path (default `/run/realms-ceremony`) |
| `CEREMONY_EXPORT_PEM_I_UNDERSTAND=1` | Required to run `export-pem` |

## Layout

```
scripts/ceremony/
  realms-key-ceremony.sh
  lib/
  vm/run-ubuntu-2204-vm-test.sh   # Desktop live ISO VM test
  vm/guest-run-test.sh
  vm/cloud-init/                # nocloud seed for live SSH in VM
  docker/                       # fast smoke test only
```
