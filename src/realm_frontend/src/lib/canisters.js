console.log('=== CANISTERS.JS LOADING START ===');

import { building } from '$app/environment';
import { createDummyBackend } from './dummyBackend.js';

console.log('=== DUMMY BACKEND IMPORTED SUCCESSFULLY ===');

const buildingOrTesting = building || process.env.NODE_ENV === "test";
const isDevDummyMode = import.meta.env.DEV_DUMMY_MODE === 'true';

console.log('Building/Testing:', buildingOrTesting);
console.log('Dev dummy mode enabled:', isDevDummyMode);

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

// Create the backend - always use dummy in dev mode
let backend;
if (buildingOrTesting) {
    console.log('Using build-time dummy actor');
    backend = dummyActor();
} else if (isDevDummyMode) {
    console.log('Creating dummy backend for dev mode');
    backend = createDummyBackend();
} else {
    console.log('No real backend available, using dummy');
    backend = createDummyBackend();
}

console.log('Backend created:', backend);

export { backend };

export async function initBackendWithIdentity() {
    console.log('initBackendWithIdentity called - returning dummy backend');
    return backend;
}
