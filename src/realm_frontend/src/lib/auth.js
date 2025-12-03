// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';

// Environment detection
const hostname = window.location.hostname;
const isLocalDev = (
  hostname.includes('localhost') || 
  hostname.includes('127.0.0.1') ||
  process.env.NODE_ENV === 'development'
);

console.log(`Environment: ${isLocalDev ? 'Local Development' : 'Production'}`);

// Internet Identity canister ID - injected by deploy script for local development
const INTERNET_IDENTITY_CANISTER_ID = '__INTERNET_IDENTITY_CANISTER_ID__';

// Get the Internet Identity canister URL
function getInternetIdentityUrl() {
  // For local development, use the injected II canister ID with localhost
  if (isLocalDev) {
    const currentPort = window.location.port || '8000';
    return `http://${INTERNET_IDENTITY_CANISTER_ID}.localhost:${currentPort}`;
  }
  
  // For staging and mainnet, use the standard II URL
  return 'https://identity.ic0.app';
}

// This may throw an error if II canister ID cannot be found in local development
const II_URL = getInternetIdentityUrl();
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
