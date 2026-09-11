# Realms YubiKey key ceremony

Air-gapped key generation for dev and prod IC operator identities. **No PEM files leave the ceremony** — keys are imported into YubiKey PIV slot `9c` (PKCS#11 id `02` for `dfx identity --hsm-key-id`).

**Target environment:** Ubuntu **22.04 Desktop** live USB — boot "Try Ubuntu", run the ceremony, power off. Do not install Ubuntu to disk.

## Hardware plan

Configured in **`ceremony-config.json`** (copy from `ceremony-config.example.json` to customize).

Default:

| Environment | Device | Touch policy | Copies |
|---|---|---|---|
| `dev` | YubiKey 5C Nano | `never` | 1 |
| `prod` | YubiKey 5 NFC | `cached` | 3 |

Each environment entry defines: `id`, `signing_key` filename, `yubikey.label` (prompt text),
`yubikey.touch_policy` (`never` \| `cached` \| `always`), and `yubikey.copies` (identical clones).

```bash
sudo ./realms-key-ceremony.sh offline-generate --config ./my-ceremony-config.json
sudo ./realms-key-ceremony.sh provision-env staging   # any id from config
```

CI is unchanged — still uses existing PEM secrets.

## Prepare the ceremony live USB (prep machine)

On a Linux workstation with an **8 GB+ USB stick** and internet:

```bash
cd scripts/ceremony
chmod +x prepare-ceremony-live-usb.sh usb/*.sh
sudo ./prepare-ceremony-live-usb.sh --device /dev/sdX --yes
```

This downloads the official Ubuntu 22.04.5 Desktop ISO (once, into `vm/cache/`), remasters it,
and writes the bootable stick.

**Two embed modes:**

| Mode | Flag | Use |
|------|------|-----|
| **Bootstrap** (default) | `--bootstrap-only` | QEMU dev VM — ISO has only `usb/attach-ceremony-from-host.sh`; live scripts from laptop via virtio-9p |
| **Full** | `--full-embed` | Production airgapped USB — entire ceremony tree baked into the image |

Production USB (full embed):

```bash
sudo ./prepare-ceremony-live-usb.sh --full-embed --device /dev/sdX --yes
```

VM ISO only (bootstrap — rebuild only when `usb/*` bootstrap files change):

```bash
./prepare-ceremony-live-usb.sh --bootstrap-only --iso-only vm/cache/realms-ceremony-live.iso --verify
```

## Ceremony flow (Ubuntu 22.04 Desktop live USB)

1. **Boot the prepared live USB** on the laptop (initially online; choose **Try Ubuntu**).
2. Open a terminal and `cd` to the scripts on the USB:
   ```bash
   cd "$(/bin/bash /cdrom/realms-ceremony/usb/find-ceremony-dir.sh)"
   ```
   Or read `/cdrom/CEREMONY-START-HERE.txt`.
3. **Online:**
   ```bash
   sudo ./realms-key-ceremony.sh online-setup
   ```
4. **Disconnect all network** (Wi‑Fi off, Ethernet unplugged).
5. **Offline** (optional: your own PIV PIN/PUK from a file — see `operator-credentials.example`):
   ```bash
   sudo ./realms-key-ceremony.sh check-offline
   sudo ./realms-key-ceremony.sh offline-generate --credentials-file /path/to/my-piv.txt
   # or random PINs: sudo ./realms-key-ceremony.sh offline-generate
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

### Interactive VM with GUI + real YubiKey (screen-share / debug)

Thin bootstrap ISO + live ceremony tree from your checkout (edit scripts on the host — no ISO rebuild):

```bash
cd scripts/ceremony
# plug YubiKey first; if passthrough fails: sudo systemctl stop pcscd
./vm/run-ubuntu-2204-vm-interactive.sh
```

In the VM: **Try Ubuntu** → double-click **Realms Key Ceremony**. A terminal opens in `/opt/realms-ceremony` (scripts attach from the host automatically). Packages (`ykman`, `ykcs11`, `dfx`) are baked into the live image — `online-setup` is a no-op when they are already present.

In the VM: **Try Ubuntu** → terminal → `cd "$(/bin/bash /cdrom/realms-ceremony/usb/find-ceremony-dir.sh)"` → run the ceremony as on hardware.

`--no-usb` skips YubiKey passthrough (use `CEREMONY_SIMULATE=1` inside the guest for a dry run).

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
  prepare-ceremony-live-usb.sh    # build bootable USB with scripts embedded
  realms-key-ceremony.sh
  lib/
  usb/                            # START-HERE + helpers on the live USB
  vm/run-ubuntu-2204-vm-test.sh   # Desktop live ISO VM test
  vm/guest-run-test.sh
  vm/cloud-init/                # nocloud seed for live SSH in VM
  docker/                       # fast smoke test only
```
