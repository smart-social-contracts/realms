import { derived, writable } from 'svelte/store';

/** @type {import('svelte/store').Writable<{ open: boolean, width: number, resizing: boolean }>} */
export const realmPanelChrome = writable({ open: false, width: 360, resizing: false });

/** Whether the registry browse-realms slide-over is open. */
export const realmPanelOpen = derived(realmPanelChrome, ($c) => $c.open);
