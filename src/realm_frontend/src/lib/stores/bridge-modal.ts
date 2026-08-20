import { get, writable } from 'svelte/store';
import type { NotifyLevel } from '@realmsgos/extension-bridge';

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

const modalQueue: BridgeModalRequest[] = [];

function finishCurrentModal(): void {
	bridgeModalRequest.set(null);
	pumpModalQueue();
}

function pumpModalQueue(): void {
	if (get(bridgeModalRequest) !== null) return;
	const next = modalQueue.shift();
	if (next) {
		bridgeModalRequest.set(next);
	}
}

export function requestBridgeModal(payload: {
	title: string;
	body: string;
	actions: BridgeModalAction[];
}): Promise<{ actionId: string }> {
	return new Promise((resolve, reject) => {
		const entry: BridgeModalRequest = {
			...payload,
			resolve: (actionId) => {
				resolve({ actionId });
				finishCurrentModal();
			},
			reject: (err) => {
				reject(err);
				finishCurrentModal();
			},
		};

		if (get(bridgeModalRequest) !== null) {
			modalQueue.push(entry);
		} else {
			bridgeModalRequest.set(entry);
		}
	});
}

export function dismissBridgeModal(): void {
	get(bridgeModalRequest)?.reject(new Error('Modal dismissed'));
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

export function showBridgeNotify(
	level: NotifyLevel | 'warning',
	message: string,
): Promise<void> {
	switch (level) {
		case 'error':
			return showBridgeAlert({ body: message });
		case 'success':
			return showBridgeNotice({ body: message });
		default:
			return showBridgeNotice({ title: 'Notice', body: message });
	}
}

/** Clears queue state between tests. */
export function resetBridgeModalQueueForTests(): void {
	modalQueue.length = 0;
	bridgeModalRequest.set(null);
}
