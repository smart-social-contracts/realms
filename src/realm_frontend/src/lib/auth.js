// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';
import { getTestModeIIBypass } from '$lib/config.js';
import { isEmbeddedInPortal, getPortalDelegationIdentity } from '$lib/portal-bridge.ts';

const II_URL = globalThis.__CANISTER_IDS?.internet_identity || 'https://identity.ic0.app';
console.log(`Using Identity Provider: ${II_URL}`);

// Canonical Internet Identity derivation origin. II derives a *different*
// principal per frontend origin unless every frontend logs in with the same
// `derivationOrigin` (and that origin serves the realm frontend's origin in its
// `/.well-known/ii-alternative-origins`). Injected at deploy time via
// canister_ids.js so the whole federation (every realm + the registry) resolves
// to ONE principal per human. When unset, login falls back to per-origin
// principals (legacy behaviour). See issue #233 / QUARTERS.md.
const DERIVATION_ORIGIN = globalThis.__CANISTER_IDS?.derivation_origin || '';
if (DERIVATION_ORIGIN) {
  console.log(`Using II derivationOrigin: ${DERIVATION_ORIGIN}`);
}

let authClient;
let authClientMode = null;

function getAuthMode() {
  if (getTestModeIIBypass()) return 'test';
  // Portal iframe uses scoped delegation when available; otherwise II + derivationOrigin.
  if (isEmbeddedInPortal() && getPortalDelegationIdentity()) return 'portal';
  return 'ii';
}

function _createPortalAuthClientMock() {
  return {
    isAuthenticated: async () => !!getPortalDelegationIdentity(),
    getIdentity: () => getPortalDelegationIdentity(),
    logout: async () => {},
    login: async () => {
      const { waitForPortalDelegation, requestAuthRefresh } = await import(
        '$lib/portal-bridge.ts'
      );
      requestAuthRefresh();
      return waitForPortalDelegation();
    }
  };
}

// --- Test mode support ---
// In test mode we bypass Internet Identity entirely and use a deterministic
// Ed25519 identity so Playwright tests can authenticate without WebAuthn.
let _testIdentity = null;
let _testLoggedIn = false;

async function _createTestIdentity(random = false) {
  if (_testIdentity && !random) return _testIdentity;
  const { Ed25519KeyIdentity } = await import('@dfinity/identity');
  const seed = new Uint8Array(32);
  if (random) {
    crypto.getRandomValues(seed);
  } else {
    seed[0] = 0xED; seed[1] = 0x57;
  }
  _testIdentity = Ed25519KeyIdentity.generate(seed);
  console.log(`[TEST MODE] Generated ${random ? 'random' : 'default'} test identity: ${_testIdentity.getPrincipal().toText()}`);
  return _testIdentity;
}

// A minimal mock that satisfies the AuthClient interface used by canisters.js
function _createTestAuthClientMock() {
  return {
    isAuthenticated: async () => _testLoggedIn,
    getIdentity: () => _testIdentity,
    logout: async () => {
      _testLoggedIn = false;
      _testIdentity = null;
    },
  };
}

// Export the authClient instance for reuse
export { authClient };

export async function initializeAuthClient() {
  const mode = getAuthMode();
  if (authClient && authClientMode !== mode) {
    authClient = null;
  }
  authClientMode = mode;

  if (mode === 'portal') {
    if (!authClient) {
      authClient = _createPortalAuthClientMock();
    }
    return authClient;
  }
  if (mode === 'test') {
    if (!authClient) {
      authClient = _createTestAuthClientMock();
      console.log('[TEST MODE] Auth client initialized (mock)');
    }
    return authClient;
  }
  if (!authClient) {
    authClient = await AuthClient.create({
      keyType: 'Ed25519',
      idleOptions: { disableIdle: true }
    });
    console.log('Auth client initialized');
  }
  return authClient;
}

export async function login({ random = false } = {}) {
  // Federation portal embed: same single II login as direct icp0.io when
  // derivationOrigin is configured (staging/demo/prod). Portal delegation
  // is only used when no canonical derivation origin exists.
  if (isEmbeddedInPortal() && !DERIVATION_ORIGIN) {
    let identity = getPortalDelegationIdentity();
    if (!identity) {
      const client = await initializeAuthClient();
      if (await client.isAuthenticated()) {
        identity = client.getIdentity();
      }
    }
    if (!identity) {
      const { waitForPortalDelegation, requestAuthRefresh } = await import(
        '$lib/portal-bridge.ts'
      );
      requestAuthRefresh();
      // Brief wait for portal delegation when no canonical derivationOrigin is configured.
      const delegationTimeoutMs = DERIVATION_ORIGIN ? 1500 : 60_000;
      identity = await waitForPortalDelegation({ timeoutMs: delegationTimeoutMs });
    }
    if (identity) {
      authClient = _createPortalAuthClientMock();
      authClientMode = 'portal';
      const principal = identity.getPrincipal();
      console.log(`[portal] Authenticated via delegation: ${principal.toText()}`);
      return { identity, principal };
    }
    if (!DERIVATION_ORIGIN) {
      return { identity: null, principal: null };
    }
    console.log('[portal] No delegation yet — using Internet Identity with derivationOrigin');
  }
  if (getTestModeIIBypass()) {
    // If ?as=swarm_agent_NNN and ?pem=<urlencoded-pem> are both present,
    // create a Secp256k1 identity from the provided PEM so tests can log in
    // as a specific geister member. If ?as= is present without ?pem=, warn
    // and fall through to the default Ed25519 seed identity.
    const urlParams = new URLSearchParams(window.location.search);
    const asParam = urlParams.get('as');
    const pemParam = urlParams.get('pem');

    let identity;
    if (asParam && pemParam) {
      const { Secp256k1KeyIdentity } = await import('@dfinity/identity');
      const decodedPem = decodeURIComponent(pemParam);
      identity = Secp256k1KeyIdentity.fromPem(decodedPem);
      _testIdentity = identity;
      console.log(`[TEST MODE] Logged in as ${asParam} with Secp256k1 PEM: ${identity.getPrincipal().toText()}`);
    } else {
      if (asParam) {
        console.warn(`[TEST MODE] ?as=${asParam} present but ?pem= missing — using default Ed25519 seed identity`);
      }
      identity = await _createTestIdentity(random);
    }
    _testLoggedIn = true;
    authClient = _createTestAuthClientMock();
    const principal = identity.getPrincipal();
    console.log(`[TEST MODE] Logged in with principal: ${principal.toText()}`);
    return { identity, principal };
  }

  const client = await initializeAuthClient();

  // Reuse an existing IC session — critical in portal iframes where auth stores
  // do not persist across remounts but AuthClient/IndexedDB still holds II.
  if (await client.isAuthenticated()) {
    const identity = client.getIdentity();
    const principal = identity.getPrincipal();
    console.log(`Reusing existing IC session: ${principal.toText()}`);
    return { identity, principal };
  }

  return new Promise((resolve) => {
    client.login({
      identityProvider: II_URL,
      // Pin the derivation origin so this realm frontend yields the SAME
      // principal as every other Realms frontend + the registry. Omitted when
      // unset to preserve legacy per-origin behaviour.
      ...(DERIVATION_ORIGIN ? { derivationOrigin: DERIVATION_ORIGIN } : {}),
      maxTimeToLive: BigInt(7 * 24 * 60 * 60 * 1_000_000_000), // 7 days
      onSuccess: () => {
        const identity = client.getIdentity();
        const principal = identity.getPrincipal();
        console.log(`Logged in with principal: ${principal.toText()}`);
        resolve({ identity, principal });
      },
      onError: (error) => {
        console.error("Login failed:", error);
        resolve({ identity: null, principal: null });
      }
    });
  });
}

export async function logout() {
  resetAuthSessionRestore();
  if (getTestModeIIBypass()) {
    _testLoggedIn = false;
    _testIdentity = null;
    console.log('[TEST MODE] Logged out');
    return;
  }
  const client = await initializeAuthClient();
  await client.logout();
}

export async function isAuthenticated() {
  if (isEmbeddedInPortal() && getPortalDelegationIdentity()) {
    return true;
  }
  if (getTestModeIIBypass()) {
    return _testLoggedIn;
  }
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}

let restorePromise = null;

/** Reset so a later call re-checks IC session (e.g. after logout). */
export function resetAuthSessionRestore() {
  restorePromise = null;
}

/**
 * Restore auth from the IC AuthClient (shared across tabs) and hydrate app stores.
 * Safe to call from multiple components; runs once until reset.
 */
export async function restoreAuthSession() {
  if (!restorePromise) {
    restorePromise = _restoreAuthSession().catch((error) => {
      restorePromise = null;
      throw error;
    });
  }
  return restorePromise;
}

async function _restoreAuthSession() {
  if (isEmbeddedInPortal()) {
    const portalId = getPortalDelegationIdentity();
    if (portalId) {
      const { isAuthenticated: isAuthenticatedStore, userIdentity, principal } = await import(
        '$lib/stores/auth.js'
      );
      const principalText = portalId.getPrincipal().toText();
      isAuthenticatedStore.set(true);
      userIdentity.set(principalText);
      principal.set(principalText);
      try {
        const { initBackendWithIdentity } = await import('$lib/canisters.js');
        await initBackendWithIdentity(portalId);
        const { loadUserProfiles } = await import('$lib/stores/profiles.js');
        await loadUserProfiles();
      } catch (e) {
        console.warn('[portal] backend init deferred:', e);
      }
      return { authenticated: true, principal: principalText };
    }
  }

  const authenticated = await isAuthenticated();
  const { isAuthenticated: isAuthenticatedStore, userIdentity, principal } = await import(
    '$lib/stores/auth.js'
  );

  if (!authenticated) {
    isAuthenticatedStore.set(false);
    return { authenticated: false, principal: '' };
  }

  const client = await initializeAuthClient();
  const identity = client.getIdentity();
  const principalText = identity.getPrincipal().toText();

  isAuthenticatedStore.set(true);
  userIdentity.set(principalText);
  principal.set(principalText);

  const { initBackendWithIdentity } = await import('$lib/canisters.js');
  await initBackendWithIdentity();

  const { loadUserProfiles } = await import('$lib/stores/profiles.js');
  await loadUserProfiles();

  return { authenticated: true, principal: principalText };
}
