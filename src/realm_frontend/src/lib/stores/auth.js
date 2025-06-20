// src/lib/stores/auth.js
import { writable } from 'svelte/store';

const isBrowser = typeof window !== 'undefined' && typeof sessionStorage !== 'undefined';

function createPersistentStore(key, defaultValue) {
    const initialValue = isBrowser && sessionStorage.getItem(key) 
        ? JSON.parse(sessionStorage.getItem(key)) 
        : defaultValue;
    
    const store = writable(initialValue);
    
    if (isBrowser) {
        store.subscribe(value => {
            sessionStorage.setItem(key, JSON.stringify(value));
        });
    }
    
    return store;
}

export const isAuthenticated = createPersistentStore('auth_isAuthenticated', false);
export const userIdentity = createPersistentStore('auth_userIdentity', null);
export const principal = createPersistentStore('auth_principal', '');

export const universe = writable('');
export const snapshots = writable('');
