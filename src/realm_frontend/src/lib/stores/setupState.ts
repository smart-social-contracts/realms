import { writable } from 'svelte/store';
import { fetchSetupState } from '$lib/setup/api';
import type { SetupState } from '$lib/setup/types';

interface SetupStateStore {
	loading: boolean;
	error: string | null;
	state: SetupState | null;
}

const initial: SetupStateStore = {
	loading: true,
	error: null,
	state: null
};

function createSetupStateStore() {
	const { subscribe, update, set } = writable<SetupStateStore>(initial);

	return {
		subscribe,
		refresh: async () => {
			update((s) => ({ ...s, loading: true, error: null }));
			try {
				const state = await fetchSetupState();
				set({ loading: false, error: null, state });
				return state;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to load setup state';
				update((s) => ({ ...s, loading: false, error: message }));
				throw error;
			}
		}
	};
}

export const setupStateStore = createSetupStateStore();
