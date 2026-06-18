// src/lib/stores/auth.js
import { writable } from 'svelte/store';

const isBrowser = typeof window !== 'undefined' && typeof localStorage !== 'undefined';

function createPersistentStore(key, defaultValue) {
    const initialValue = isBrowser && localStorage.getItem(key) 
        ? JSON.parse(localStorage.getItem(key)) 
        : defaultValue;
    
    const store = writable(initialValue);
    
    if (isBrowser) {
        store.subscribe(value => {
            localStorage.setItem(key, JSON.stringify(value));
        });

        window.addEventListener('storage', (event) => {
            if (event.key !== key || event.newValue === null) return;
            try {
                store.set(JSON.parse(event.newValue));
            } catch {
                // ignore malformed cross-tab payloads
            }
        });
    }
    
    return store;
}

export const isAuthenticated = createPersistentStore('auth_isAuthenticated', false);
export const userIdentity = createPersistentStore('auth_userIdentity', null);
export const principal = createPersistentStore('auth_principal', '');

export const universe = writable('');
export const snapshots = writable('');
