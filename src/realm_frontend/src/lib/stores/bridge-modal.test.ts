import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { bridgeModalRequest, showBridgeAlert, showBridgeNotice } from './bridge-modal';

describe('showBridgeAlert', () => {
	it('opens modal with default title and close action', async () => {
		const promise = showBridgeAlert({ body: 'Something broke' });
		const request = get(bridgeModalRequest);
		expect(request).not.toBeNull();
		expect(request?.title).toBe('Something went wrong');
		expect(request?.body).toBe('Something broke');
		expect(request?.actions).toEqual([{ id: 'close', label: 'Close', tone: 'secondary' }]);
		request?.resolve('close');
		await promise;
		expect(get(bridgeModalRequest)).toBeNull();
	});

	it('uses custom title when provided', () => {
		void showBridgeAlert({ title: 'Custom', body: 'Details' });
		const request = get(bridgeModalRequest);
		expect(request?.title).toBe('Custom');
		request?.resolve('close');
	});

	it('swallows dismiss', async () => {
		const promise = showBridgeAlert({ body: 'err' });
		const request = get(bridgeModalRequest);
		request?.reject(new Error('Modal dismissed'));
		await promise;
		expect(get(bridgeModalRequest)).toBeNull();
	});
});

describe('showBridgeNotice', () => {
	it('opens a success modal with a primary close action', async () => {
		const promise = showBridgeNotice({
			title: 'Verification code sent',
			body: 'Check your inbox for a 6-digit code.',
		});
		const request = get(bridgeModalRequest);
		expect(request?.title).toBe('Verification code sent');
		expect(request?.body).toBe('Check your inbox for a 6-digit code.');
		expect(request?.actions).toEqual([{ id: 'close', label: 'Close', tone: 'primary' }]);
		request?.resolve('close');
		await promise;
		expect(get(bridgeModalRequest)).toBeNull();
	});
});
