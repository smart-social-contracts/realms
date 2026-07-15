/**
 * Deterministic test identities for II-bypass mode.
 *
 * Seed layout (32 bytes): [0xED, 0x57, index, 0, …]
 *   - Identity 0 ("Creator") is the legacy default test user.
 *   - Indices 1…N are stable joiner / staff personas for E2E and manual QA.
 *
 * Optional deploy-time overrides (via /canister_ids.js):
 *   - globalThis.__TEST_IDENTITY_PRINCIPALS = string[] — display labels only
 *     when no PEM is configured for that index.
 *   - globalThis.__TEST_IDENTITY_PEms = string[] — PEM strings (or base64) used
 *     for login at that index (e.g. realm founder / deployer Secp256k1 key).
 */

import { Ed25519KeyIdentity, Secp256k1KeyIdentity } from '@dfinity/identity';

export const TEST_IDENTITY_MAGIC = [0xed, 0x57];
/** Highest index shown in the join-page picker (inclusive). Identity 0…3 = four personas. */
export const TEST_IDENTITY_PICKER_MAX_INDEX = 3;
/** Highest index for programmatic use (E2E may use more). */
export const DEFAULT_TEST_IDENTITY_MAX_INDEX = 8;

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
    return Secp256k1KeyIdentity.fromPem(pem);
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
 * @returns {{ index: number, label: string, principal: string, description: string }[]}
 */
export function listTestIdentities(maxIndex = TEST_IDENTITY_PICKER_MAX_INDEX) {
  const principalOverrides = globalThis.__TEST_IDENTITY_PRINCIPALS;
  const pems = globalThis.__TEST_IDENTITY_PEms;
  const items = [];
  for (let index = 0; index <= maxIndex; index++) {
    const hasPem = Array.isArray(pems) && !!pems[index];
    const loginPrincipal = testIdentityPrincipal(index);
    const registeredFounder =
      index === 0 && Array.isArray(principalOverrides) && principalOverrides[0]
        ? String(principalOverrides[0])
        : '';
    items.push({
      index,
      label: index === 0 ? 'Creator' : `Identity ${index}`,
      principal: loginPrincipal,
      registeredFounder,
      description:
        index === 0
          ? hasPem
            ? 'Realm founder / deployer (PEM-backed test login)'
            : registeredFounder && registeredFounder !== loginPrincipal
              ? `Registered founder is ${shortPrincipal(registeredFounder)} — this test key logs in separately; use invite code "admin" for admin access`
              : 'Realm founder persona — use admin invite code "admin" if not yet registered'
          : `Deterministic test member ${index}`,
    });
  }
  return items;
}
