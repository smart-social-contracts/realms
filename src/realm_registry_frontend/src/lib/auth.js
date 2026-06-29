// src/lib/auth.js - Internet Identity authentication module
import { AuthClient } from '@dfinity/auth-client';
import { CONFIG, TEST_MODE_II_BYPASS } from '$lib/config.js';

const II_URL = CONFIG.internet_identity_url;
console.log(`Using Identity Provider: ${II_URL}`);

// Canonical II derivation origin (the registry's own public origin). Pinning it
// here — and listing every realm frontend in this origin's
// `/.well-known/ii-alternative-origins` — makes one human resolve to ONE
// principal across the registry and every realm. See issue #233.
const DERIVATION_ORIGIN = CONFIG.ii_derivation_origin || '';
if (DERIVATION_ORIGIN) {
  console.log(`Using II derivationOrigin: ${DERIVATION_ORIGIN}`);
}

let authClient;

// --- Test mode support ---
let _testIdentity = null;
let _testLoggedIn = false;

async function _createTestIdentity() {
  if (_testIdentity) return _testIdentity;
  const { Ed25519KeyIdentity } = await import('@dfinity/identity');
  const seed = new Uint8Array(32);
  seed[0] = 0xED; seed[1] = 0x57;
  _testIdentity = Ed25519KeyIdentity.generate(seed);
  console.log(`[TEST MODE] Generated test identity: ${_testIdentity.getPrincipal().toText()}`);
  return _testIdentity;
}

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

export async function initializeAuthClient() {
  if (TEST_MODE_II_BYPASS) {
    if (!authClient) {
      authClient = _createTestAuthClientMock();
      console.log('[TEST MODE] Auth client initialized (mock)');
    }
    return authClient;
  }
  if (!authClient) {
    authClient = await AuthClient.create();
  }
  return authClient;
}

export async function login() {
  if (TEST_MODE_II_BYPASS) {
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
      identity = await _createTestIdentity();
    }
    _testLoggedIn = true;
    authClient = _createTestAuthClientMock();
    const principal = identity.getPrincipal();
    console.log(`[TEST MODE] Logged in with principal: ${principal.toText()}`);
    return { identity, principal };
  }

  const client = await initializeAuthClient();
  
  return new Promise((resolve) => {
    client.login({
      identityProvider: II_URL,
      // Pin derivation origin so the registry-issued principal matches the one
      // every realm frontend gets (they list this origin as canonical).
      ...(DERIVATION_ORIGIN ? { derivationOrigin: DERIVATION_ORIGIN } : {}),
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
  if (TEST_MODE_II_BYPASS) {
    _testLoggedIn = false;
    _testIdentity = null;
    console.log('[TEST MODE] Logged out');
    return;
  }
  const client = await initializeAuthClient();
  await client.logout();
}

export async function isAuthenticated() {
  if (TEST_MODE_II_BYPASS) {
    return _testLoggedIn;
  }
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}

export async function getPrincipal() {
  const client = await initializeAuthClient();
  if (TEST_MODE_II_BYPASS) {
    return _testLoggedIn && _testIdentity ? _testIdentity.getPrincipal() : null;
  }
  if (await client.isAuthenticated()) {
    return client.getIdentity().getPrincipal();
  }
  return null;
}

/** @returns {Promise<import('@dfinity/agent').Identity | null>} */
export async function getIdentity() {
  if (TEST_MODE_II_BYPASS) {
    return _testLoggedIn && _testIdentity ? _testIdentity : null;
  }
  const client = await initializeAuthClient();
  if (await client.isAuthenticated()) {
    return client.getIdentity();
  }
  return null;
}
