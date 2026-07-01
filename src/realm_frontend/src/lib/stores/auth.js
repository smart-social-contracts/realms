// src/lib/stores/auth.js
import { writable } from 'svelte/store';
import { isEmbeddedInPortal } from '$lib/portal-bridge.ts';

function storageAvailable() {
    if (typeof window === 'undefined') return false;
    try {
        const key = '__realms_storage_test__';
        localStorage.setItem(key, '1');
        localStorage.removeItem(key);
        return true;
    } catch {
        return false;
    }
}

const canPersist = !isEmbeddedInPortal() && storageAvailable();

function createPersistentStore(key, defaultValue) {
    if (!canPersist) {
        return writable(defaultValue);
    }

    const initialValue = localStorage.getItem(key)
        ? JSON.parse(localStorage.getItem(key))
        : defaultValue;

    const store = writable(initialValue);

    store.subscribe(value => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch {
            // sandbox or private mode
        }
    });

    window.addEventListener('storage', (event) => {
        if (event.key !== key || event.newValue === null) return;
        try {
            store.set(JSON.parse(event.newValue));
        } catch {
            // ignore malformed cross-tab payloads
        }
    });

    return store;
}

export const isAuthenticated = createPersistentStore('auth_isAuthenticated', false);
export const userIdentity = createPersistentStore('auth_userIdentity', null);
export const principal = createPersistentStore('auth_principal', '');

export const universe = writable('');
export const snapshots = writable('');
