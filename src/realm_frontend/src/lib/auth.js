// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';

// Flag to determine if we're in local development mode
const isLocalDev = false; // Changed to false for IC deployment

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

export async function initializeAuthClient() {
  if (isLocalDev) {
    // In local dev, we just return a dummy client with basic functionality
    if (!authClient) {
      authClient = {
        isAuthenticated: () => Promise.resolve(locallyAuthenticated),
        getIdentity: () => ({
          getPrincipal: () => Principal.fromText(dummyPrincipals[currentPrincipalIndex])
        }),
        logout: () => {
          locallyAuthenticated = false;
          return Promise.resolve();
        }
      };
    }
    return authClient;
  } else {
    // Real IC implementation
    if (!authClient) {
      authClient = await AuthClient.create();
    }
    return authClient;
  }
}

export async function login() {
  if (isLocalDev) {
    // In local dev, we simulate a login with a dummy principal
    locallyAuthenticated = true;
    console.log(`Logged in with dummy principal: ${dummyPrincipals[currentPrincipalIndex]}`);
    const identity = {
      getPrincipal: () => Principal.fromText(dummyPrincipals[currentPrincipalIndex])
    };
    const principal = identity.getPrincipal();
    return { identity, principal };
  } else {
    // Real IC implementation
    const client = await initializeAuthClient();
    return new Promise((resolve) => {
      client.login({
        identityProvider: 'https://identity.ic0.app/#authorize',
        onSuccess: () => {
          const identity = client.getIdentity();
          const principal = identity.getPrincipal();
          resolve({ identity, principal });
        },
      });
    });
  }
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
