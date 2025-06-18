// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';

// Flag to determine if we're in local development mode
const isLocalDev = true; //process.env.NODE_ENV === 'development';

// Determine the appropriate Identity Provider URL based on environment
const II_URL = isLocalDev
  ? 'http://umunu-kh777-77774-qaaca-cai.localhost:8000' // Local II canister - updated ID
  : 'https://identity.ic0.app';                                    // Mainnet II

console.log(`Using Identity Provider: ${II_URL}`);

// Dummy data for local development
const dummyPrincipals = [
  'rrkah-fqaaa-aaaaa-aaaaq-cai', // Admin
  'renrk-eyaaa-aaaaa-aaada-cai', // Regular user
  'rdmx6-jaaaa-aaaaa-aaadq-cai'  // Another user
];

// Use the first principal by default
let currentPrincipalIndex = 0;
let locallyAuthenticated = false;

// Hold the real or dummy auth client
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
  
  return new Promise((resolve) => {
    client.login({
      identityProvider: II_URL, // Use the appropriate II URL
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

// Function to cycle through different dummy principals (for testing different users)
export function switchDummyPrincipal() {
  if (isLocalDev) {
    currentPrincipalIndex = (currentPrincipalIndex + 1) % dummyPrincipals.length;
    console.log(`Switched to dummy principal: ${dummyPrincipals[currentPrincipalIndex]}`);
    return dummyPrincipals[currentPrincipalIndex];
  }
  return null;
}

export async function logout() {
  const client = await initializeAuthClient();
  await client.logout();
}

export async function isAuthenticated() {
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}
