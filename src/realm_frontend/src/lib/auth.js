// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';
import { CONFIG, TEST_MODE_II_BYPASS } from '$lib/config.js';

// Use the Internet Identity URL from config (set during deployment)
const II_URL = CONFIG.internet_identity_url;
console.log(`Using Identity Provider: ${II_URL}`);

let authClient;

// --- Test mode support ---
// In test mode we bypass Internet Identity entirely and use a deterministic
// Ed25519 identity so Playwright tests can authenticate without WebAuthn.
let _testIdentity = null;
let _testLoggedIn = false;

async function _createTestIdentity() {
  if (_testIdentity) return _testIdentity;
  const { Ed25519KeyIdentity } = await import('@dfinity/identity');
  // Deterministic 32-byte seed → always produces the same principal
  const seed = new Uint8Array(32);
  seed[0] = 0xED; seed[1] = 0x57; // deterministic marker bytes
  _testIdentity = Ed25519KeyIdentity.generate(seed);
  console.log(`[TEST MODE] Generated test identity: ${_testIdentity.getPrincipal().toText()}`);
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
  if (TEST_MODE_II_BYPASS) {
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

export async function login() {
  if (TEST_MODE_II_BYPASS) {
    const identity = await _createTestIdentity();
    _testLoggedIn = true;
    // Re-create mock so getIdentity() returns the new identity
    authClient = _createTestAuthClientMock();
    const principal = identity.getPrincipal();
    console.log(`[TEST MODE] Logged in with principal: ${principal.toText()}`);
    return { identity, principal };
  }

  const client = await initializeAuthClient();
  
  return new Promise((resolve) => {
    client.login({
      identityProvider: II_URL,
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
