import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
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

function makeActor(overrides: Record<string, unknown> = {}) {
	return {
		get_setup_state: vi.fn().mockResolvedValue(
			JSON.stringify({
				status: 'setup',
				creator: '',
				is_caller_authorized: true,
				codex: null,
				token: null,
				branding: null
			})
		),
		get_available_codices_cached: vi.fn().mockResolvedValue(
			JSON.stringify({ success: false, error: 'empty' })
		),
		list_available_codices: vi.fn().mockResolvedValue(
			JSON.stringify({
				success: true,
				codices: [{ id: 'syntropia', versions: ['1.0.0'], name: 'Syntropia' }]
			})
		),
		setup_install_codex: vi.fn().mockResolvedValue(JSON.stringify({ success: true })),
		...overrides
	};
}

describe('setup api getActor', () => {
	beforeEach(() => {
		backendStore.set(null);
		backendReadySettled = false;
		vi.resetModules();
	});

	it('resolves once backendActorReady settles even if backendReady is still pending', async () => {
		const mockActor = makeActor();
		backendStore.set(mockActor);
		actorReadyResolve();

		const { fetchSetupState } = await import('./api');
		const state = await fetchSetupState();

		expect(state.status).toBe('setup');
		expect(mockActor.get_setup_state).toHaveBeenCalled();
	});
});

describe('listAvailableCodices', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.resetModules();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('returns cached codices without firing the slow update', async () => {
		const mockActor = makeActor({
			get_available_codices_cached: vi.fn().mockResolvedValue(
				JSON.stringify({
					success: true,
					codices: [{ id: 'cached', versions: ['2.0.0'], name: 'Cached' }]
				})
			)
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { listAvailableCodices } = await import('./api');
		const codices = await listAvailableCodices();

		expect(codices).toEqual([{ id: 'cached', versions: ['2.0.0'], name: 'Cached' }]);
		expect(mockActor.list_available_codices).not.toHaveBeenCalled();
	});

	it('fires update and polls cache when empty', async () => {
		let cacheReads = 0;
		const mockActor = makeActor({
			get_available_codices_cached: vi.fn().mockImplementation(async () => {
				cacheReads += 1;
				if (cacheReads >= 2) {
					return JSON.stringify({
						success: true,
						codices: [{ id: 'fresh', versions: ['1.0.0'], name: 'Fresh' }]
					});
				}
				return JSON.stringify({ success: false, error: 'empty' });
			}),
			list_available_codices: vi.fn().mockResolvedValue(undefined)
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { listAvailableCodices } = await import('./api');
		const promise = listAvailableCodices();
		await vi.advanceTimersByTimeAsync(2_500);
		const codices = await promise;

		expect(mockActor.list_available_codices).toHaveBeenCalledTimes(1);
		expect(codices).toEqual([{ id: 'fresh', versions: ['1.0.0'], name: 'Fresh' }]);
	});
});

describe('installSetupCodex', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.resetModules();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('polls setup state when the raw install call never settles', async () => {
		let setupReads = 0;
		const mockActor = makeActor({
			setup_install_codex: vi.fn().mockReturnValue(new Promise(() => {})),
			get_setup_state: vi.fn().mockImplementation(async () => {
				setupReads += 1;
				const codex =
					setupReads >= 2
						? { package: 'syntropia', version: '1.0.0' }
						: null;
				return JSON.stringify({
					status: 'setup',
					creator: '',
					is_caller_authorized: true,
					codex,
					token: null,
					branding: null
				});
			})
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { installSetupCodex } = await import('./api');
		const promise = installSetupCodex(
			{ package: 'syntropia', version: '1.0.0' },
			{ rawCallGraceMs: 100, pollIntervalMs: 50 }
		);
		await Promise.resolve();
		await vi.advanceTimersByTimeAsync(100);
		await vi.advanceTimersByTimeAsync(50);
		const result = await promise;

		expect(result.success).toBe(true);
		expect(mockActor.get_setup_state).toHaveBeenCalled();
	});

	it('polls setup state when the raw install call throws an ambiguous error', async () => {
		let setupReads = 0;
		const mockActor = makeActor({
			setup_install_codex: vi
				.fn()
				.mockRejectedValue(new Error('Call was returned undefined')),
			get_setup_state: vi.fn().mockImplementation(async () => {
				setupReads += 1;
				const codex =
					setupReads >= 2
						? { package: 'syntropia', version: '1.0.0' }
						: null;
				return JSON.stringify({
					status: 'setup',
					creator: '',
					is_caller_authorized: true,
					codex,
					token: null,
					branding: null
				});
			})
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { installSetupCodex } = await import('./api');
		const promise = installSetupCodex(
			{ package: 'syntropia', version: '1.0.0' },
			{ rawCallGraceMs: 100, pollIntervalMs: 50 }
		);
		await Promise.resolve();
		await vi.advanceTimersByTimeAsync(100);
		await vi.advanceTimersByTimeAsync(50);
		const result = await promise;

		expect(result.success).toBe(true);
		expect(mockActor.get_setup_state).toHaveBeenCalled();
	});

	it('surfaces fast failures without polling', async () => {
		const mockActor = makeActor({
			setup_install_codex: vi
				.fn()
				.mockResolvedValue(JSON.stringify({ success: false, error: 'approval denied' })),
			get_setup_state: vi.fn()
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { installSetupCodex } = await import('./api');
		const result = await installSetupCodex(
			{ package: 'syntropia', version: '1.0.0' },
			{ rawCallGraceMs: 100 }
		);
		await Promise.resolve();
		await vi.advanceTimersByTimeAsync(100);

		expect(result).toEqual({ success: false, error: 'approval denied' });
		expect(mockActor.get_setup_state).not.toHaveBeenCalled();
	});

	it('throws on non-ambiguous install errors without polling', async () => {
		const mockActor = makeActor({
			setup_install_codex: vi.fn().mockImplementation(() => {
				throw new Error('Network error');
			}),
			get_setup_state: vi.fn()
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { installSetupCodex } = await import('./api');

		await expect(
			installSetupCodex({ package: 'syntropia', version: '1.0.0' }, { rawCallGraceMs: 100 })
		).rejects.toThrow('Network error');
		expect(mockActor.get_setup_state).not.toHaveBeenCalled();
	});
});

describe('completeSetup', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.resetModules();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('polls setup state when the raw complete call never settles', async () => {
		let setupReads = 0;
		const mockActor = makeActor({
			complete_setup: vi.fn().mockReturnValue(new Promise(() => {})),
			get_setup_state: vi.fn().mockImplementation(async () => {
				setupReads += 1;
				return JSON.stringify({
					status: setupReads >= 2 ? 'alpha' : 'setup',
					creator: '',
					is_caller_authorized: true,
					codex: { package: 'syntropia', version: '1.0.0' },
					token: null,
					branding: null
				});
			})
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { completeSetup } = await import('./api');
		const promise = completeSetup({ rawCallGraceMs: 100, pollIntervalMs: 50 });
		await Promise.resolve();
		await vi.advanceTimersByTimeAsync(100);
		await vi.advanceTimersByTimeAsync(50);
		const result = await promise;

		expect(result).toEqual({ success: true });
		expect(mockActor.get_setup_state).toHaveBeenCalled();
	});

	it('returns fast failures without polling', async () => {
		const mockActor = makeActor({
			complete_setup: vi
				.fn()
				.mockResolvedValue(JSON.stringify({ success: false, error: 'Not authorized' })),
			get_setup_state: vi.fn()
		});
		backendStore.set(mockActor);
		actorReadyResolve();

		const { completeSetup } = await import('./api');
		const result = await completeSetup({ rawCallGraceMs: 100 });
		await Promise.resolve();
		await vi.advanceTimersByTimeAsync(100);

		expect(result).toEqual({ success: false, error: 'Not authorized' });
		expect(mockActor.get_setup_state).not.toHaveBeenCalled();
	});
});

describe('isAmbiguousInstallError', () => {
	it('detects agent-js ambiguous sync-call failures', async () => {
		const { isAmbiguousInstallError } = await import('./api');
		expect(isAmbiguousInstallError(new Error('Call was returned undefined'))).toBe(true);
		expect(
			isAmbiguousInstallError(new Error('Cannot determine if the call was successful'))
		).toBe(true);
		expect(isAmbiguousInstallError(new Error('Network error'))).toBe(false);
	});
});
