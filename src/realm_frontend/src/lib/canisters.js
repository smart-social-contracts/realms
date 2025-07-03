console.log('=== CANISTERS.JS LOADING START ===');

import { building } from '$app/environment';
import { writable, get } from 'svelte/store';
import { createDummyBackend } from './dummyBackend.js';

console.log('=== DUMMY BACKEND IMPORTED SUCCESSFULLY ===');

const buildingOrTesting = building || process.env.NODE_ENV === "test";

console.log('Building/Testing:', buildingOrTesting);
console.log('Forcing dummy mode for debugging');

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

// Create initial backend actor - FORCE DUMMY MODE FOR DEBUGGING
function createInitialBackend() {
    if (buildingOrTesting) {
        console.log('Using build-time dummy actor');
        return dummyActor();
    } else {
        console.log('FORCED: Creating dummy backend for debugging');
        return createDummyBackend();
    }
}

// Create a writable store for the backend actor (required by existing components)
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

console.log('Backend created and exported');

export async function initBackendWithIdentity() {
    console.log('initBackendWithIdentity called - returning dummy backend');
    return get(backendStore);
}
