import { AuthClient } from '@dfinity/auth-client';
import type { Identity } from '@dfinity/agent';
import type { Principal } from '@dfinity/principal';
import { writable, type Writable } from 'svelte/store';

import { CONFIG } from './config';

let authClient: AuthClient | null = null;

export const isAuthenticated: Writable<boolean> = writable(false);
export const principalStore: Writable<Principal | null> = writable(null);

async function ensureClient(): Promise<AuthClient> {
  if (!authClient) authClient = await AuthClient.create();
  return authClient;
}

export async function bootstrapAuth(): Promise<void> {
  const client = await ensureClient();
  if (await client.isAuthenticated()) {
    const id = client.getIdentity();
    isAuthenticated.set(true);
    principalStore.set(id.getPrincipal());
  }
}

export async function login(): Promise<{ identity: Identity | null; principal: Principal | null }> {
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
  const client = await ensureClient();
  await client.logout();
  isAuthenticated.set(false);
  principalStore.set(null);
}

export async function getIdentity(): Promise<Identity | null> {
  const client = await ensureClient();
  if (await client.isAuthenticated()) return client.getIdentity();
  return null;
}
