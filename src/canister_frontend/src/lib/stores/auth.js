// src/lib/stores/auth.js
import { writable } from 'svelte/store';

export const isAuthenticated = writable(false);
export const userIdentity = writable(null); // Stores the principal text

// Add a dedicated store for principal value if it's not already defined
export const principal = writable(''); // Stores the principal string for global access

export const universe = writable('');
export const snapshots = writable('');