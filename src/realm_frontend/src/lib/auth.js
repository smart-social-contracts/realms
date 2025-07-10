// src/lib/auth.js
import { isDevelopmentMode } from './dev-mode.js';

let AuthClient, Principal;
let DummyAuthClient, dummyPrincipal;
let authImportsInitialized = false;

async function initializeAuthImports() {
  if (authImportsInitialized) return;
  
  if (isDevelopmentMode()) {
    // Import dummy implementations for development
    const dummyModule = await import('./dummy-implementations/auth-dummy.js');
    DummyAuthClient = dummyModule.DummyAuthClient;
    dummyPrincipal = dummyModule.dummyPrincipal;
    console.log('🔧 DEV MODE: Using dummy authentication');
  } else {
    const icModule = await import('@dfinity/auth-client');
    const principalModule = await import('@dfinity/principal');
    AuthClient = icModule.AuthClient;
    Principal = principalModule.Principal;
    console.log('🏭 PROD MODE: Using IC authentication');
  }
  
  authImportsInitialized = true;
}

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

// Export the authClient instance for reuse
export { authClient };

export async function initializeAuthClient() {
  if (!authClient) {
    await initializeAuthImports();
    
    if (isDevelopmentMode()) {
      authClient = await DummyAuthClient.create();
      console.log('🔧 DEV MODE: Dummy auth client initialized');
    } else {
      authClient = await AuthClient.create();
      console.log('🏭 PROD MODE: IC auth client initialized');
    }
  }
  return authClient;
}

export async function login() {
  await initializeAuthImports();
  const client = await initializeAuthClient();
  
  if (isDevelopmentMode()) {
    // Dummy login for development
    const identity = client.getIdentity();
    const principal = identity.getPrincipal();
    console.log(`🔧 DEV MODE: Logged in with dummy principal: ${principal.toText()}`);
    return Promise.resolve({ identity, principal });
  }
  
  return new Promise((resolve) => {
    client.login({
      identityProvider: II_URL, // Use the appropriate II URL
      onSuccess: () => {
        const identity = client.getIdentity();
        const principal = identity.getPrincipal();
        console.log(`🏭 PROD MODE: Logged in with principal: ${principal.toText()}`);
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
  await initializeAuthImports();
  const client = await initializeAuthClient();
  await client.logout();
}

export async function isAuthenticated() {
  await initializeAuthImports();
  const client = await initializeAuthClient();
  return client.isAuthenticated();
}
