/**
 * Deterministic test identities for II-bypass mode.
 *
 * Seed layout (32 bytes): [0xED, 0x57, index₀, index₁, index₂, index₃, 0, …]
 *
 * Optional deploy-time overrides (via /canister_ids.js):
 *   - globalThis.__TEST_IDENTITY_PEms = string[] — PEM strings used for login
 *
 * Reference roster (indices 0–9): config/deterministic-test-identity-principals.json
 */

import { Ed25519KeyIdentity, Secp256k1KeyIdentity } from '@dfinity/identity';

export const TEST_IDENTITY_SESSION_KEY = 'test_identity_index';
export const TEST_IDENTITY_MAGIC = [0xed, 0x57];
/** Highest index shown in the picker (inclusive). Four personas: 0…3. */
export const TEST_IDENTITY_PICKER_MAX_INDEX = 3;

export function testIdentityNumber(index) {
  return index + 1;
}

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
  seed[3] = (index >>> 8) & 0xff;
  seed[4] = (index >>> 16) & 0xff;
  seed[5] = (index >>> 24) & 0xff;
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

/** @param {number} index */
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

export function getStoredTestIdentityIndex() {
  if (typeof sessionStorage === 'undefined') return 0;
  const raw = sessionStorage.getItem(TEST_IDENTITY_SESSION_KEY);
  if (raw == null) return 0;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(255, parsed));
}

export function setStoredTestIdentityIndex(index) {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(TEST_IDENTITY_SESSION_KEY, String(Math.max(0, Math.min(255, index))));
}

export function clearStoredTestIdentityIndex() {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(TEST_IDENTITY_SESSION_KEY);
}

/**
 * @returns {{ index: number, label: string, principal: string, loginPrincipal: string, description: string, hasPem: boolean }[]}
 */
export function listTestIdentities(maxIndex = TEST_IDENTITY_PICKER_MAX_INDEX) {
  const pems = globalThis.__TEST_IDENTITY_PEms;
  const items = [];
  for (let index = 0; index <= maxIndex; index++) {
    const hasPem = Array.isArray(pems) && !!pems[index];
    const configured = expectedPrincipal(index);
    let loginPrincipal = '';
    try {
      loginPrincipal = testIdentityPrincipal(index);
    } catch {
      loginPrincipal = '';
    }
    items.push({
      index,
      label: testIdentityLabel(index),
      principal: configured || loginPrincipal,
      loginPrincipal,
      hasPem,
      description:
        index === 0
          ? 'Default registry persona (Identity 1)'
          : `Deterministic test member ${testIdentityNumber(index)}`,
    });
  }
  return items;
}
