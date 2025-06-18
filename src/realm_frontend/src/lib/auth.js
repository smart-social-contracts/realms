// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';

// Import the Internet Identity canister ID from declarations
import { canisterId as iiCanisterId } from '../../../declarations/internet_identity/index.js';

// Flag to determine if we're in local development mode
const isLocalDev = window.location.hostname.includes('localhost') || 
                   window.location.hostname.includes('127.0.0.1');

// Build the appropriate II URL based on environment and canister ID
const II_URL = isLocalDev
  ? `http://${iiCanisterId}.localhost:8000` // Local II canister with dynamic ID
  : 'https://identity.ic0.app';             // Mainnet II

console.log(`Using Identity Provider: ${II_URL} (canister ID: ${iiCanisterId})`);

// Hold the real auth client
let authClient;

// Export the authClient instance for reuse
export { authClient };

export async function initializeAuthClient() {
  if (!authClient) {
    authClient = await AuthClient.create();
    console.log('Auth client initialized');
  }
  return authClient;
}

export async function login() {
  const client = await initializeAuthClient();
  const days = BigInt(30);
  
  return new Promise((resolve) => {
    client.login({
      identityProvider: II_URL,
      onSuccess: async () => {
        console.log('Login successful');
        resolve(true);
      },
      onError: (error) => {
        console.error('Login failed:', error);
        resolve(false);
      },
      maxTimeToLive: days * BigInt(24) * BigInt(3_600_000_000_000),
    });
  });
}

export async function logout() {
  const client = await initializeAuthClient();
  await client.logout();
  console.log('Logout successful');
  return true;
}

export async function isAuthenticated() {
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}

export async function getAuthenticatedPrincipal() {
  const client = await initializeAuthClient();
  if (await client.isAuthenticated()) {
    const identity = client.getIdentity();
    const principal = identity.getPrincipal().toText();
    console.log('Principal at login:', principal);
    return principal;
  }
  return null;
}
