// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';

let authClient;

export async function initializeAuthClient() {
  if (!authClient) {
    authClient = await AuthClient.create();
  }
  return authClient;
}

export async function login() {
  const client = await initializeAuthClient();
  return new Promise((resolve) => {
    client.login({
      identityProvider: 'https://identity.ic0.app/#authorize',
      onSuccess: () => {
        const identity = client.getIdentity();
        const principal = identity.getPrincipal(); // Get the principal here
        resolve({ identity, principal });
      },
    });
  });
}

export async function logout() {
  const client = await initializeAuthClient();
  await client.logout();
}

export async function isAuthenticated() {
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}
