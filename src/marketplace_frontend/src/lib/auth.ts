// Internet Identity authentication for the marketplace.
import { AuthClient } from '@dfinity/auth-client';
import type { Identity } from '@dfinity/agent';
import type { Principal } from '@dfinity/principal';
import { writable, type Writable } from 'svelte/store';

import { CONFIG, TEST_MODE_II_BYPASS } from './config';

let authClient: AuthClient | null = null;

export const isAuthenticated: Writable<boolean> = writable(false);
export const principalStore: Writable<Principal | null> = writable(null);

// --- Test mode support ---
let _testIdentity: any = null;
let _testLoggedIn = false;

async function _createTestIdentity(): Promise<any> {
  if (_testIdentity) return _testIdentity;
  const { Ed25519KeyIdentity } = await import('@dfinity/identity');
  const seed = new Uint8Array(32);
  seed[0] = 0xED; seed[1] = 0x57;
  _testIdentity = Ed25519KeyIdentity.generate(seed);
  console.log(`[TEST MODE] Generated test identity: ${_testIdentity.getPrincipal().toText()}`);
  return _testIdentity;
}

async function ensureClient(): Promise<AuthClient> {
  if (!authClient) authClient = await AuthClient.create();
  return authClient;
}

export async function bootstrapAuth(): Promise<void> {
  if (TEST_MODE_II_BYPASS) {
    console.log('[TEST MODE] bootstrapAuth — II bypass active, auto-login');
    await login();
    return;
  }
  const client = await ensureClient();
  if (await client.isAuthenticated()) {
    const id = client.getIdentity();
    isAuthenticated.set(true);
    principalStore.set(id.getPrincipal());
  }
}

export async function login(): Promise<{ identity: Identity | null; principal: Principal | null }> {
  if (TEST_MODE_II_BYPASS) {
    const identity = await _createTestIdentity();
    _testLoggedIn = true;
    const principal = identity.getPrincipal();
    isAuthenticated.set(true);
    principalStore.set(principal);
    console.log(`[TEST MODE] Logged in with principal: ${principal.toText()}`);
    return { identity, principal };
  }

  const client = await ensureClient();
  return new Promise((resolve) => {
    client.login({
      identityProvider: CONFIG.internet_identity_url,
      onSuccess: () => {
        const identity = client.getIdentity();
        const principal = identity.getPrincipal();
        isAuthenticated.set(true);
        principalStore.set(principal);
        resolve({ identity, principal });
      },
      onError: (err) => {
        console.error('II login failed:', err);
        resolve({ identity: null, principal: null });
      },
    });
  });
}

export async function logout(): Promise<void> {
  if (TEST_MODE_II_BYPASS) {
    _testLoggedIn = false;
    _testIdentity = null;
    isAuthenticated.set(false);
    principalStore.set(null);
    console.log('[TEST MODE] Logged out');
    return;
  }
  const client = await ensureClient();
  await client.logout();
  isAuthenticated.set(false);
  principalStore.set(null);
}

export async function getPrincipal(): Promise<Principal | null> {
  if (TEST_MODE_II_BYPASS) {
    return _testLoggedIn && _testIdentity ? _testIdentity.getPrincipal() : null;
  }
  const client = await ensureClient();
  if (await client.isAuthenticated()) return client.getIdentity().getPrincipal();
  return null;
}

export async function getIdentity(): Promise<Identity | null> {
  if (TEST_MODE_II_BYPASS) {
    return _testLoggedIn && _testIdentity ? _testIdentity : null;
  }
  const client = await ensureClient();
  if (await client.isAuthenticated()) return client.getIdentity();
  return null;
}
