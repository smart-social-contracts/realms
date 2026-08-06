import { writable } from 'svelte/store';

export interface BridgeModalAction {
	id: string;
	label: string;
	tone?: 'primary' | 'secondary' | 'danger';
}

export interface BridgeModalRequest {
	title: string;
	body: string;
	actions: BridgeModalAction[];
	resolve: (actionId: string) => void;
	reject: (err: Error) => void;
}

export const bridgeModalRequest = writable<BridgeModalRequest | null>(null);

export function requestBridgeModal(payload: {
	title: string;
	body: string;
	actions: BridgeModalAction[];
}): Promise<{ actionId: string }> {
	return new Promise((resolve, reject) => {
		bridgeModalRequest.set({
			...payload,
			resolve: (actionId) => {
				bridgeModalRequest.set(null);
				resolve({ actionId });
			},
			reject: (err) => {
				bridgeModalRequest.set(null);
				reject(err);
			},
		});
	});
}

export function dismissBridgeModal(): void {
	bridgeModalRequest.update((current) => {
		current?.reject(new Error('Modal dismissed'));
		return null;
	});
}
