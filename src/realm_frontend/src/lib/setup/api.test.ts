import { describe, expect, it, vi, beforeEach } from 'vitest';
import { writable, get } from 'svelte/store';

const backendStore = writable<unknown>(null);
let actorReadyResolve: () => void;
const backendActorReady = new Promise<void>((resolve) => {
	actorReadyResolve = resolve;
});
let backendReadySettled = false;
const backendReady = new Promise<void>((resolve) => {
	queueMicrotask(() => {
		if (!backendReadySettled) {
			// Simulate the production hang: backendReady never settles during boot.
			return;
		}
		resolve();
	});
});

vi.mock('$lib/canisters', () => ({
	backendStore,
	backendActorReady,
	backendReady
}));

describe('setup api getActor', () => {
	beforeEach(() => {
		backendStore.set(null);
		backendReadySettled = false;
	});

	it('resolves once backendActorReady settles even if backendReady is still pending', async () => {
		const mockActor = {
			get_setup_state: vi.fn().mockResolvedValue(
				JSON.stringify({
					status: 'setup',
					creator: '',
					is_caller_authorized: true,
					codex: null,
					token: null,
					branding: null
				})
			)
		};
		backendStore.set(mockActor);
		actorReadyResolve();

		const { fetchSetupState } = await import('./api');
		const state = await fetchSetupState();

		expect(state.status).toBe('setup');
		expect(mockActor.get_setup_state).toHaveBeenCalled();
	});
});
