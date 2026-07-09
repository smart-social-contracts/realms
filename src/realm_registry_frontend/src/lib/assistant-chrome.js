import { writable } from 'svelte/store';

/** @type {import('svelte/store').Writable<{ open: boolean, docked: boolean, width: number }>} */
export const assistantChrome = writable({ open: false, docked: false, width: 380 });
