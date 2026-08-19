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

function showCloseModal(
	title: string,
	body: string,
	tone: BridgeModalAction['tone']
): Promise<void> {
	return requestBridgeModal({
		title,
		body,
		actions: [{ id: 'close', label: 'Close', tone }],
	})
		.then(() => {})
		.catch(() => {});
}

export function showBridgeAlert(payload: { title?: string; body: string }): Promise<void> {
	return showCloseModal(payload.title ?? 'Something went wrong', payload.body, 'secondary');
}

export function showBridgeNotice(payload: { title?: string; body: string }): Promise<void> {
	return showCloseModal(payload.title ?? 'Done', payload.body, 'primary');
}
