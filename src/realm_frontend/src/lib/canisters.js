console.log('=== CANISTERS.JS LOADING ===');

import { building } from '$app/environment';
import { writable } from 'svelte/store';

const isDummyMode = typeof window !== 'undefined' && window.__DUMMY_MODE__;

console.log('Dummy mode detected:', isDummyMode);

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

// Create initial backend
function createInitialBackend() {
    if (building) {
        console.log('Using build-time dummy actor');
        return dummyActor();
    } else if (isDummyMode && window.__DUMMY_BACKEND__) {
        console.log('Using global dummy backend');
        return window.__DUMMY_BACKEND__;
    } else {
        console.log('Loading real backend (not implemented in dummy mode)');
        return window.__DUMMY_BACKEND__ || dummyActor();
    }
}

// Create backend store
const initialBackend = createInitialBackend();
export const backendStore = writable(initialBackend);

// Create backend proxy
export const backend = new Proxy({}, {
    get: function(target, prop) {
        if (isDummyMode && window.__DUMMY_BACKEND__) {
            return window.__DUMMY_BACKEND__[prop];
        }
        return initialBackend[prop];
    }
});

export async function initBackendWithIdentity() {
    console.log('initBackendWithIdentity called');
    if (isDummyMode) {
        console.log('Returning dummy backend for dev mode');
        return window.__DUMMY_BACKEND__;
    }
    return initialBackend;
}

console.log('Canisters module ready');
