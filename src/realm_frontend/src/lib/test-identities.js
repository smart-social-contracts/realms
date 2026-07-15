/**
 * Deterministic test identities for II-bypass mode.
 *
 * Seed layout (32 bytes): [0xED, 0x57, index, 0, …]
 *   - Index 0 = Identity 1 (Creator); indices 1…3 = Identity 2–4.
 *
 * Optional deploy-time overrides (via /canister_ids.js):
 *   - globalThis.__TEST_IDENTITY_PEms = string[] — PEM strings (or base64) used
 *     for login at that index instead of the deterministic seed.
 *   - globalThis.__TEST_IDENTITY_PRINCIPALS = string[] — documented roster
 *     principals (display/sanity only; login never requires them).
 */

import { Ed25519KeyIdentity, Secp256k1KeyIdentity } from '@dfinity/identity';

export const TEST_IDENTITY_MAGIC = [0xed, 0x57];
/** Highest index shown in the join-page picker (inclusive). Four personas: 0…3. */
export const TEST_IDENTITY_PICKER_MAX_INDEX = 3;
/** Highest index for programmatic use (E2E may use more). */
export const DEFAULT_TEST_IDENTITY_MAX_INDEX = 8;

/** Human-facing identity number (1-based). Index 0 → Identity 1. */
export function testIdentityNumber(index) {
  return index + 1;
}

/** Picker label for internal index (0-based). */
export function testIdentityLabel(index) {
  if (index === 0) return 'Identity 1 (Creator)';
  return `Identity ${index + 1}`;
}

/** @param {number} index */
export function testIdentitySeed(index) {
  const seed = new Uint8Array(32);
  seed[0] = TEST_IDENTITY_MAGIC[0];
  seed[1] = TEST_IDENTITY_MAGIC[1];
  seed[2] = index & 0xff;
  return seed;
}

/** @param {string} raw */
function decodePem(raw) {
  const trimmed = String(raw || '').trim();
  if (!trimmed) return '';
  if (trimmed.includes('BEGIN')) return trimmed;
  try {
    return atob(trimmed.replace(/-/g, '+').replace(/_/g, '/'));
  } catch {
    return trimmed;
  }
}

function expectedPrincipal(index) {
  const principals = globalThis.__TEST_IDENTITY_PRINCIPALS;
  if (!Array.isArray(principals) || !principals[index]) return '';
  return String(principals[index]);
}

/**
 * Create the identity used for login at `index`.
 * Uses __TEST_IDENTITY_PEms[index] when set, otherwise the deterministic Ed25519 seed.
 * @param {number} index
 */
export function createTestIdentityFromIndex(index) {
  const pems = globalThis.__TEST_IDENTITY_PEms;
  const pemRaw = Array.isArray(pems) && pems[index] ? String(pems[index]) : '';
  if (pemRaw) {
    const pem = decodePem(pemRaw);
    const identity = Secp256k1KeyIdentity.fromPem(pem);
    const expected = expectedPrincipal(index);
    if (expected && identity.getPrincipal().toText() !== expected) {
      throw new Error(
        `${testIdentityLabel(index)} PEM principal ${identity.getPrincipal().toText()} does not match configured ${expected}`,
      );
    }
    return identity;
  }
  return Ed25519KeyIdentity.generate(testIdentitySeed(index));
}

/** @param {number} index */
export function testIdentityPrincipal(index) {
  return createTestIdentityFromIndex(index).getPrincipal().toText();
}

/** @param {string} principal */
export function shortPrincipal(principal) {
  if (!principal || principal.length < 12) return principal || '';
  return `${principal.slice(0, 8)}…${principal.slice(-8)}`;
}

/**
 * Labels and principals for the join-page picker.
 * The principal shown is always the one login will actually produce.
 * @returns {{ index: number, label: string, principal: string, description: string, hasPem: boolean }[]}
 */
export function listTestIdentities(maxIndex = TEST_IDENTITY_PICKER_MAX_INDEX) {
  const pems = globalThis.__TEST_IDENTITY_PEms;
  const items = [];
  for (let index = 0; index <= maxIndex; index++) {
    const hasPem = Array.isArray(pems) && !!pems[index];
    let loginPrincipal = '';
    try {
      loginPrincipal = testIdentityPrincipal(index);
    } catch {
      loginPrincipal = '';
    }
    items.push({
      index,
      label: testIdentityLabel(index),
      principal: loginPrincipal,
      hasPem,
      description:
        index === 0
          ? 'Realm founder persona — use admin invite code "admin" if not yet registered'
          : `Deterministic test member ${testIdentityNumber(index)}`,
    });
  }
  return items;
}
