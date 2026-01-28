// src/lib/auth.js - Internet Identity authentication module
import { AuthClient } from '@dfinity/auth-client';
import { CONFIG } from '$lib/config.js';

// Use the Internet Identity URL from config (set during deployment)
const II_URL = CONFIG.internet_identity_url;
console.log(`Using Identity Provider: ${II_URL}`);

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
      identityProvider: II_URL,
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
  const client = await initializeAuthClient();
  await client.logout();
}

export async function isAuthenticated() {
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}

export async function getPrincipal() {
  const client = await initializeAuthClient();
  if (await client.isAuthenticated()) {
    return client.getIdentity().getPrincipal();
  }
  return null;
}
