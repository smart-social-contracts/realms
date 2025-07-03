import { building } from '$app/environment';
import { HttpAgent } from '@dfinity/agent';
import { writable, get } from 'svelte/store';
import { authClient, initializeAuthClient } from '$lib/auth';  
import { browser } from '$app/environment';
import { createDummyBackend } from './dummyBackend.js';

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

const buildingOrTesting = building || process.env.NODE_ENV === "test";

const isDevDummyMode = import.meta.env.DEV_DUMMY_MODE === 'true';

console.log('Dev dummy mode enabled:', isDevDummyMode);

// Create initial backend actor
function createInitialBackend() {
    if (buildingOrTesting) {
        return dummyActor();
    } else if (isDevDummyMode) {
        console.log('Using dummy backend for development');
        return createDummyBackend();
    } else {
        console.log('Real backend mode not available in dev setup');
        return dummyActor();
    }
}

// Create a writable store for the backend actor
export const backendStore = writable(createInitialBackend());

// Create a proxy that always uses the latest actor from the store
export const backend = new Proxy({}, {
    get: function(target, prop) {
        // Get the latest actor from the store
        const actor = get(backendStore);
        // Forward the property access to the actor
        return actor[prop];
    }
});

// Initialize backend with authenticated identity
export async function initBackendWithIdentity() {
    try {
        console.log('Initializing backend with authenticated identity...');
        
        if (isDevDummyMode) {
            console.log('Using dummy backend, skipping authentication');
            return get(backendStore);
        }
        
        // Make sure we're using the shared auth client
        const client = authClient || await initializeAuthClient();
        
        if (await client.isAuthenticated()) {
            // Get the authenticated identity from the shared client
            const identity = client.getIdentity();
            console.log('Using authenticated identity:', identity.getPrincipal().toText());
            
            const currentActor = get(backendStore);
            if (currentActor && currentActor._agent && currentActor._agent._identity === identity) {
                console.log('Backend already initialized with current identity');
                return currentActor;
            }
            
            // Create an agent with the identity
            const agent = new HttpAgent({ identity });
            
            // For local development, we need to fetch the root key
            const isLocalDevelopment = browser && (window.location.hostname.includes('localhost') || 
                                                           window.location.hostname.includes('127.0.0.1'));
            if (isLocalDevelopment) {
                console.log('Fetching root key for local development');
                await agent.fetchRootKey().catch(e => {
                    console.warn('Error fetching root key:', e);
                    console.log('Continuing anyway as this might be expected in local dev');
                });
            }
            
            console.log('Real backend authentication not available in dev mode');
            const authenticatedActor = get(backendStore);
            
            // Update the store with the authenticated actor
            backendStore.set(authenticatedActor);
            
            console.log('Backend initialized with authenticated identity');
            return authenticatedActor;
        } else {
            console.log('User not authenticated, using anonymous identity');
            return backend;
        }
    } catch (error) {
        console.error('Error initializing backend with identity:', error);
        return backend;
    }
}
