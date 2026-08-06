import { writable } from 'svelte/store';
import type { NotifyLevel } from '@realms/extension-bridge';

export interface BridgeToast {
	id: number;
	level: NotifyLevel;
	message: string;
}

let seq = 0;

export const bridgeToasts = writable<BridgeToast[]>([]);

const AUTO_DISMISS_MS = 5_000;

export function showBridgeToast(level: NotifyLevel, message: string): void {
	const id = ++seq;
	bridgeToasts.update((items) => [...items, { id, level, message }]);
	setTimeout(() => {
		dismissBridgeToast(id);
	}, AUTO_DISMISS_MS);
}

export function dismissBridgeToast(id: number): void {
	bridgeToasts.update((items) => items.filter((t) => t.id !== id));
}
