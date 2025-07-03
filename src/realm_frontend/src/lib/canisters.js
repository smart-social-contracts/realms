console.log('=== MINIMAL CANISTERS.JS TEST ===');

import { writable } from 'svelte/store';
// import { createDummyBackend } from './dummyBackend.js'; // Temporarily disabled

console.log('=== IMPORTS SUCCESSFUL ===');

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

const isDevDummyMode = true;
console.log('=== MINIMAL TEST COMPLETE ===');

// const dummyBackend = createDummyBackend(); // Temporarily disabled
const dummyBackend = { status: async () => ({ success: true, data: { Status: { demo_mode: true } } }) };
export const backendStore = writable(dummyBackend);

console.log('=== INITIALIZATION CHECK ===');

if (typeof window !== 'undefined') {
    console.log('=== CLIENT-SIDE INITIALIZATION STARTING ===');
    
    try {
        const isLocalDevelopment = window.location.hostname.includes('localhost') || 
                                  window.location.hostname.includes('127.0.0.1');
        
        console.log('Running in local development mode:', isLocalDevelopment);
        
        if (isDevDummyMode) {
            console.log('=== USING DUMMY BACKEND FOR DEVELOPMENT ===');
            const dummyBackend = createDummyBackend();
            console.log('Dummy backend created:', dummyBackend);
            backendStore.set(dummyBackend);
        } else {
            console.log('=== LOADING REAL BACKEND DECLARATIONS ===');
            console.log('Real backend mode not available in dev setup');
            console.log('Backend declarations not available, using dummy actor');
            backendStore.set(dummyActor());
        }
    } catch (error) {
        console.error('Error during client-side initialization:', error);
        backendStore.set(dummyActor());
    }
}

// Create a proxy that always uses the latest actor from the store
export const backend = new Proxy({}, {
    get: function(target, prop) {
        // Get the latest actor from the store
        const actor = get(backendStore);
        // Forward the property access to the actor
        return actor[prop];
    }
});

export async function initBackendWithIdentity() {
    try {
        console.log('Initializing backend with authenticated identity...');
        
        if (isDevDummyMode) {
            console.log('Using dummy backend, skipping authentication');
            return get(backendStore);
        }
        
        // const client = authClient || await initializeAuthClient(); // Temporarily disabled
        const client = null;
        
        if (client && await client.isAuthenticated()) {
            const identity = client.getIdentity();
            console.log('Using authenticated identity:', identity.getPrincipal().toText());
            
            const currentActor = get(backendStore);
            if (currentActor && currentActor._agent && currentActor._agent._identity === identity) {
                console.log('Backend already initialized with current identity');
                return currentActor;
            }
            
            const agent = new HttpAgent({ identity });
            
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
