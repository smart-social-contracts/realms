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

## Operator credentials & YubiKey prep

### Your own PIV PIN / PUK (optional)

By default `offline-generate` creates random `PIV_PIN`, `PIV_PUK`, and `PIV_MANAGEMENT_KEY`
in `secrets/operator-credentials.txt`. To choose your own values, create a file **before**
`offline-generate` (see `operator-credentials.example`):

```bash
cp operator-credentials.example /tmp/my-piv.txt
chmod 600 /tmp/my-piv.txt
# edit: PIV_PIN and PIV_PUK (6–8 chars each); PIV_MANAGEMENT_KEY optional (48 hex)
sudo ./realms-key-ceremony.sh offline-generate --credentials-file /tmp/my-piv.txt
```

The same PIN/PUK/management key is programmed onto every prod clone (and dev). Record them on
paper at `finalize`; shred the file at `destroy`. Never commit real credentials.

### YubiKey hardware

| Situation | What to do |
|---|---|
| **Factory-fresh key** | Normal `provision-dev` / `provision-prod` |
| **Key already has a custom PIV PIN** | `CEREMONY_PIV_RESET=1 sudo -E ./realms-key-ceremony.sh provision-prod` — wipes PIV only (slots + PIN/PUK/mgmt); does **not** need the old PIN; FIDO/OTP unchanged |
| **Keep existing PIN, migrate to ceremony PIN** | `CEREMONY_CURRENT_PIV_PIN='…'` (+ `CEREMONY_CURRENT_PIV_MANAGEMENT_KEY` if not factory) |
| **QEMU dev VM** | Plug YubiKey on host **before** starting VM; `sudo systemctl stop pcscd` on host; restart VM if you forgot (USB passthrough is set at boot) |

`piv reset` (via `CEREMONY_PIV_RESET=1`) restores factory PIV defaults, then the ceremony
sets your ceremony PIN/PUK from `operator-credentials.txt` and imports the signing key.

After the imported key is verified, the ceremony writes a self-signed X.509
certificate into slot `9c`. `ykcs11` — and therefore `dfx --hsm` and `icp` HSM
signing — only exposes PIV slots that hold a certificate, so an imported key is
invisible to PKCS#11 without one. The certificate is built off-card from the
offline PEM, so it needs the management key but no touch.

## Prepare the ceremony live USB (prep machine)

On a Linux workstation with an **8 GB+ USB stick** and internet:

```bash
cd scripts/ceremony
chmod +x prepare-ceremony-live-usb.sh usb/*.sh
sudo ./prepare-ceremony-live-usb.sh --device /dev/sdX --yes
```

This downloads the official Ubuntu 22.04.5 Desktop ISO (once, into `vm/cache/`), remasters it,
then **wipes the stick** (partition tables at both ends of the disk) and writes:

| Volume | Filesystem | Role |
|--------|------------|------|
| **CEREMONY OS** | ISO9660 | Live Ubuntu image. Read-only — required for `dd` of an isohybrid ISO; you cannot accidentally change the ceremony OS. |
| *(ESP)* | FAT32 | UEFI boot (created by the ISO, leave it alone). |
| **CEREMONY DATA** | exFAT | Writable remainder of the stick. `finalize` writes the verification bundle here. Readable on Linux, Windows, and macOS without extra drivers. |

ISO9660 is the right OS filesystem (Ubuntu live USB). NTFS was a weaker choice for the data volume: it needs `ntfs-3g`, and this bundle is small public files, not a Windows system disk. **exFAT** is the USB interchange format. FAT32 would also work but caps files at 4 GiB and labels at 11 characters. ext4 would be Linux-only.

To rename an already-flashed stick (no remaster): `sudo ./usb/relabel-ceremony-usb.sh --device /dev/sdX`.

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
4. **Network off.** `check-offline` does this for you — it turns off
   NetworkManager, blocks all radios with `rfkill`, and takes every non-loopback
   interface down, then re-probes and refuses to continue if anything still
   reaches the internet. Pull the Ethernet cable too if you want the physical
   guarantee. Set `CEREMONY_NO_AUTO_OFFLINE=1` to disconnect by hand instead.
5. **Offline** (see [Operator credentials & YubiKey prep](#operator-credentials--yubikey-prep)):
   ```bash
   sudo ./realms-key-ceremony.sh check-offline   # disconnects, then verifies
   sudo ./realms-key-ceremony.sh offline-generate --credentials-file /path/to/my-piv.txt
   # or random PINs: sudo ./realms-key-ceremony.sh offline-generate
   sudo ./realms-key-ceremony.sh provision-dev      # insert dev Nano
   CEREMONY_PIV_RESET=1 sudo -E ./realms-key-ceremony.sh provision-prod   # if keys not factory-fresh
   sudo ./realms-key-ceremony.sh finalize
   ```
6. **Copy out:** `finalize` writes the [verification bundle](#verifying-the-yubikeys-afterwards)
   automatically — to the USB `CEREMONY DATA` volume when that partition is
   present, otherwise to the host share (`scripts/ceremony/artifacts/` via 9p
   in the test VM). Record `secrets/operator-credentials.txt` on paper
   (PIN / PUK / management key) — it is deliberately **not** in the bundle.
7. **Destroy:**
   ```bash
   sudo ./realms-key-ceremony.sh destroy
   ```
8. Power off — **do not install** Ubuntu to the laptop disk.

Or run steps 5–6 in one shot after `check-offline`:

```bash
sudo ./realms-key-ceremony.sh run-offline
```

## Verifying the YubiKeys afterwards

The ceremony laptop is destroyed, so verification happens **later, elsewhere**.
`finalize` therefore writes a self-contained bundle automatically:

- **Ceremony USB:** `CEREMONY DATA` / `realms-key-verification/` (exFAT, mounted if needed)
- **Test VM (no USB data volume):** the 9p share at `scripts/ceremony/artifacts/` on the host

The bundle layout:

```
<CEREMONY DATA>/realms-key-verification/
  README-VERIFY.md            # procedure + expected principals/serials per env
  manifest.json               # principals, public keys, serials, touch policies
  ceremony-config.json
  operator-dfx-identity.txt   # dfx HSM identity commands
  <env>-public.pem, <env>-principal.txt, <env>-serials.txt
  verify-yubikeys.sh          # the checker
  lib/ic_principal.py         # PEM/SPKI → IC principal
  lib/piv_slot_info.py        # PIV slot metadata reader
```

**Public material only.** The export refuses to run if a private key or a
`PIV_PIN` / `PIV_PUK` / management key would land on the USB. Re-save at any
time before `destroy`:

```bash
sudo ./realms-key-ceremony.sh export-verification            # auto-detect CEREMONY DATA
sudo ./realms-key-ceremony.sh export-verification --dest /mnt/other
```

### On the verification laptop

Plug in the ceremony USB, then per key:

```bash
sudo apt install yubikey-manager python3 jq openssl exfatprogs
# yubico-piv-tool is optional: verify-yubikeys.sh signs pre-5.3 keys via yubikit
# If `No module named 'ykman'`: deactivate any project venv (realms/basilisk)
# and retry — verification uses /usr/bin/python3 so the apt package is visible.

cd "/media/$USER/CEREMONY DATA/realms-key-verification"
./verify-yubikeys.sh --manifest manifest.json --env dev     # insert dev Nano
./verify-yubikeys.sh --manifest manifest.json --env prod    # then each prod key
```

The script handles its own prerequisites: if the ceremony VM is still running it
stops it (QEMU holds the YubiKey through USB passthrough), and it unmasks and
starts `pcscd` on the host. `CEREMONY_VERIFY_NO_PREFLIGHT=1` disables both.

Insert **one** key at a time (the script refuses if it sees several). Expect:

```
[verify] YubiKey 34994786 (firmware 5.7.4) — checking dev in PIV slot 9c
[verify]   PASS  key type: ECCP256
[verify]   PASS  PIN policy: ONCE
[verify]   PASS  touch policy: NEVER
[verify]   PASS  serial listed for dev
[verify]   PASS  IC principal: 26ms5-…-zae
[verify] YubiKey 34994786: OK — holds the dev signing key
```

Exit status is non-zero if any check fails, so this is safe to script.

**No PIN and no touch are needed** on firmware ≥ 5.3: the policies and the
slot's public key come from PIV slot metadata, and the principal is re-derived
from that public key and compared with the manifest.

**Firmware < 5.3 has no slot metadata**, so the card will not report its own
public key. The script cannot read the policies and instead asks for the **PIV
PIN**, has the card sign a challenge, and verifies that signature against the
manifest public key. A touch is required when the policy is `cached`/`always`,
and the card waits about 15 seconds before giving up — touch the metal contact
while the LED blinks. The script retries three times and prints the card's own
error if it still refuses.

This is why one key may ask for a touch during provisioning while the others do
not: it is a property of the verification path, not of the key's configuration.
Signing is the *only* way to prove an **imported** key, because PIV attestation
covers on-card key generation only. The slot certificate the ceremony installs
cannot substitute for it — that certificate is built off-card from the same PEM,
so reading it back would confirm our own input rather than what the card holds.

> `ykman piv info` on ykman 4.x (Ubuntu 22.04) prints **no** slot section, and
> `ykman piv keys info` does not exist there. That is why the policies are read
> through the ykman Python library rather than the CLI.

The checker is manifest-driven, so it is not tied to this ceremony's layout: the
environment names, number of YubiKeys, PIV slot, touch policy, **PIN policy**,
**key type** and whether a **slot certificate** is expected all come from
`manifest.json`. Set `piv.pin_policy` in `ceremony-config.json` to change what is
provisioned and recorded; the key type is detected from the key itself, so
another curve or RSA is recorded as provisioned. Override per run with
`--key-type`, `--pin-policy`, `--no-cert-check` when checking a key from a
different ceremony. Manifests written before these fields existed fall back to
`ECCP256` / `once` / certificate required.

### Optional: export a dfx-style PEM (dev only, transitional)

Set `"export_private_pem": true` on an environment in `ceremony-config.json` (dev
only). `finalize` / `destroy` then writes `<env>-identity.pem` **next to** the
public bundle, never inside it:

- USB: `<CEREMONY DATA>/realms-key-secrets/dev-identity.pem`
- Test VM: `scripts/ceremony/artifacts/private/dev-identity.pem` on the host

The output `manifest.json` records `export_private_pem` and the path — not the
key. Production export is refused unless `CEREMONY_EXPORT_PROD_PEM_I_UNDERSTAND=1`.

Manual one-off (still requires the env var):

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

- `online-setup` (real `apt` packages: `ykman`, `ykcs11`, `python3`, …; `icp-cli` is an optional cross-check)
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

In the VM: **Try Ubuntu** → double-click **Realms Key Ceremony**. A terminal opens in `/opt/realms-ceremony` (scripts attach from the host automatically). See `usb/CEREMONY-START-HERE.txt` for credentials and YubiKey prep. Run `online-setup` if `ykman` is missing.

`--no-usb` skips YubiKey passthrough (use `CEREMONY_SIMULATE=1` inside the guest for a dry run).

**Getting `manifest.json` onto this laptop:** `finalize` writes it to `scripts/ceremony/artifacts/` on the host (the VM's `/opt/realms-ceremony` is that 9p share). No extra copy step.

Then **shut down the VM** (so QEMU releases the YubiKey), start `pcscd` on the host, and verify:

```bash
# on the host
sudo systemctl start pcscd
cd scripts/ceremony
./verify-yubikeys.sh --manifest artifacts/manifest.json --env dev
./verify-yubikeys.sh --manifest artifacts/manifest.json --env prod
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

### How principals are derived

The IC principal in `manifest.json` is computed **offline** from the signing key's
public part (`openssl` + `lib/ic_principal.py`): `sha224(SPKI DER) || 0x02`, then
CRC32 + base32. This deliberately avoids depending on `dfx` or `icp-cli` during the
airgapped phase — `dfx` cannot import OpenSSL `prime256v1` PEMs at all. When
`icp-cli` happens to be installed, the ceremony cross-checks against it and aborts
on any mismatch.

## Environment variables

| Variable | Purpose |
|---|---|
| `CEREMONY_OPERATOR_CREDENTIALS_FILE` | Path to PIV_PIN/PIV_PUK file (alternative to `--credentials-file`) |
| `CEREMONY_SIMULATE=1` | Software-only (tests without YubiKey) |
| `CEREMONY_FORCE_OFFLINE=1` | Skip network-off check |
| `CEREMONY_PIV_RESET=1` | Factory-reset PIV before import (wipes PIV PIN/slots; FIDO/OTP kept) |
| `CEREMONY_CURRENT_PIV_PIN` | Existing PIV PIN, if the key is not factory-fresh (then changed to ceremony PIN) |
| `CEREMONY_CURRENT_PIV_MANAGEMENT_KEY` | Existing PIV management key (default: factory) |
| `CEREMONY_ROOT` | Workspace path (default `/run/realms-ceremony`) |
| `CEREMONY_EXPORT_PEM_I_UNDERSTAND=1` | Required to run `export-pem` |
| `CEREMONY_BUNDLE_DIR` | Write the verification bundle here instead of auto-detecting `CEREMONY DATA` |
| `CEREMONY_DATA_LABEL` | USB data partition label (default `CEREMONY DATA`; alias `REALMS_DATA`) |
| `CEREMONY_DATA_FSTYPE` | Data filesystem (default `exfat`) |
| `CEREMONY_OS_LABEL` | Live ISO volume ID (default `CEREMONY OS`) |
| `CEREMONY_VERIFY_PIN` | PIV PIN for `verify-yubikeys.sh` on pre-5.3 firmware (else prompted) |
| `CEREMONY_NO_AUTO_OFFLINE=1` | Do not disconnect the network automatically in `check-offline` |
| `CEREMONY_VERIFY_NO_PREFLIGHT=1` | `verify-yubikeys.sh`: do not stop the ceremony VM or start `pcscd` |
| `CEREMONY_COLOR=0` / `NO_COLOR=1` | Plain output, no ANSI colour |

## Layout

```
scripts/ceremony/
  prepare-ceremony-live-usb.sh    # build bootable USB with scripts embedded
  realms-key-ceremony.sh
  verify-yubikeys.sh              # post-ceremony key check (also shipped in the bundle)
  lib/
  usb/                            # START-HERE + helpers on the live USB
  vm/run-ubuntu-2204-vm-test.sh   # Desktop live ISO VM test
  vm/guest-run-test.sh
  vm/cloud-init/                # nocloud seed for live SSH in VM
  docker/                       # fast smoke test only
```
