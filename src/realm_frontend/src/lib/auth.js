// src/lib/auth.js
import { AuthClient } from '@dfinity/auth-client';
import { Principal } from '@dfinity/principal';

const isDevDummyMode = import.meta.env.VITE_DEV_DUMMY_MODE === 'true' || 
                      import.meta.env.DEV_DUMMY_MODE === 'true' ||
                      (typeof window !== 'undefined' && window.location.search.includes('dummy=true'));


// More reliable local development detection
// This checks both the hostname and NODE_ENV (where available)
const isLocalDev = (
  window.location.hostname.includes('localhost') || 
  window.location.hostname.includes('127.0.0.1') ||
  process.env.NODE_ENV === 'development'
);

console.log(`Environment: ${isLocalDev ? 'Local Development' : 'Production'}`);

// Get the Internet Identity canister URL
function getInternetIdentityUrl() {
  // For local development, use the known Internet Identity canister ID
  if (isLocalDev) {
    const canisterId = 'uxrrr-q7777-77774-qaaaq-cai'; // Internet Identity canister ID from dfx deploy
    const port = 8000; // Default DFX port
    
    return `http://${canisterId}.localhost:${port}`;
  } 
  
  // For production, use the standard II URL
  return 'https://identity.ic0.app';
}

// This may throw an error if II canister ID cannot be found in local development
const II_URL = getInternetIdentityUrl();
console.log(`Using Identity Provider: ${II_URL}`);

let authClient;

function createMockAuthClient() {
  return {
    isAuthenticated: () => false,
    getIdentity: () => ({
      getPrincipal: () => ({
        toText: () => 'dummy-principal-123',
        isAnonymous: () => true
      })
    }),
    login: (options) => {
      console.log('[DEV DUMMY] Mock login called');
      setTimeout(() => {
        if (options.onSuccess) {
          console.log('[DEV DUMMY] Mock login success');
          options.onSuccess();
        }
      }, 100);
    },
    logout: () => {
      console.log('[DEV DUMMY] Mock logout called');
      return Promise.resolve();
    }
  };
}

// Export the authClient instance for reuse
export { authClient };

export async function initializeAuthClient() {
  if (!authClient) {
    if (isDevDummyMode) {
      authClient = createMockAuthClient();
      console.log('[DEV DUMMY] Mock auth client initialized');
    } else {
      authClient = await AuthClient.create();
      console.log('Auth client initialized');
    }
  }
  return authClient;
}

export async function login() {
  const client = await initializeAuthClient();
  
  if (isDevDummyMode) {
    console.log('[DEV DUMMY] Mock login function called');
    return new Promise((resolve) => {
      client.login({
        onSuccess: () => {
          const identity = client.getIdentity();
          const principal = identity.getPrincipal();
          console.log(`[DEV DUMMY] Mock logged in with principal: ${principal.toText()}`);
          resolve({ identity, principal });
        },
        onError: (error) => {
          console.error("[DEV DUMMY] Mock login failed:", error);
          resolve({ identity: null, principal: null });
        }
      });
    });
  }
  
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
  if (isDevDummyMode) {
    console.log('[DEV DUMMY] Mock logout function called');
  }
  await client.logout();
}

export async function isAuthenticated() {
  const client = await initializeAuthClient();
  const result = client.isAuthenticated();
  if (isDevDummyMode) {
    console.log('[DEV DUMMY] Mock isAuthenticated called, returning:', result);
  }
  return result;
}
