import { createActor, canisterId } from 'declarations/realm_backend';
import { building } from '$app/environment';
import { HttpAgent } from '@dfinity/agent';
import { writable, get } from 'svelte/store';
import { authClient, initializeAuthClient } from '$lib/auth';  

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

const buildingOrTesting = building || process.env.NODE_ENV === "test";

// Detect if we're running in local development
// Use a more reliable method than process.env which might not work in browser
const isLocalDevelopment = window.location.hostname.includes('localhost') || 
                          window.location.hostname.includes('127.0.0.1');

console.log('Running in local development mode:', isLocalDevelopment);

// Create a writable store for the backend actor
export const backendStore = writable(buildingOrTesting ? dummyActor() : createActor(canisterId));

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
            if (isLocalDevelopment) {
                console.log('Fetching root key for local development');
                await agent.fetchRootKey().catch(e => {
                    console.warn('Error fetching root key:', e);
                    console.log('Continuing anyway as this might be expected in local dev');
                });
            }
            
            // Create a new actor with the authenticated identity
            const authenticatedActor = createActor(canisterId, {
                agent
            });
            
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
