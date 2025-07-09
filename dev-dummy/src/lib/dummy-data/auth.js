import { writable } from 'svelte/store';

export const isAuthenticated = writable(true);
export const userIdentity = writable({
  getPrincipal: () => ({ toText: () => 'dummy-principal-123' })
});
export const principal = writable('dummy-principal-123');
export const universe = writable('dummy-universe');
export const snapshots = writable('dummy-snapshots');
