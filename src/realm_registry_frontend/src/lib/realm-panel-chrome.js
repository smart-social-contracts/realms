import { writable } from 'svelte/store';

/** Whether the registry browse-realms slide-over is open. */
export const realmPanelOpen = writable(false);
