// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';

// More reliable local development detection
// This checks both the hostname and NODE_ENV (where available)
const isLocalDev = (
  window.location.hostname.includes('localhost') || 
  window.location.hostname.includes('127.0.0.1') ||
  process.env.NODE_ENV === 'development'
);

console.log(`Environment: ${isLocalDev ? 'Local Development' : 'Production'}`);

// Determine the appropriate Identity Provider URL based on environment
const II_URL = isLocalDev
  ? 'http://umunu-kh777-77774-qaaca-cai.localhost:8000' // Local II canister - updated ID
  : 'https://identity.ic0.app';                                    // Mainnet II

console.log(`Using Identity Provider: ${II_URL}`);

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

export async function logout() {
  const client = await initializeAuthClient();
  await client.logout();
}

export async function isAuthenticated() {
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}
