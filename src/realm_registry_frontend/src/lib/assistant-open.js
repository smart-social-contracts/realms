import { writable } from 'svelte/store';

/** Increment to request the mundus assistant open. */
export const assistantOpenRequest = writable(0);

export function requestAssistantOpen() {
	assistantOpenRequest.update((n) => n + 1);
}
