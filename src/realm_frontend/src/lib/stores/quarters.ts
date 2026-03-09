import { writable, derived, get } from 'svelte/store';
import { backendStore } from '$lib/canisters';

export interface QuarterInfo {
	name: string;
	canister_id: string;
	population: number;
	status: string;
}

export interface QuartersState {
	quarters: QuarterInfo[];
	isQuarter: boolean;
	parentRealmCanisterId: string;
	loading: boolean;
	error: string | null;
}

const createQuartersStore = () => {
	const { subscribe, set, update } = writable<QuartersState>({
		quarters: [],
		isQuarter: false,
		parentRealmCanisterId: '',
		loading: true,
		error: null
	});

	return {
		subscribe,
		fetch: async () => {
			update((state: QuartersState) => ({ ...state, loading: true, error: null }));

			try {
				const currentActor = get(backendStore);
				if (!currentActor) {
					throw new Error('Actor not initialized');
				}

				const response = await currentActor.status();

				if (response.success && response.data.status) {
					const status = response.data.status;
					update((state: QuartersState) => ({
						...state,
						quarters: status.quarters || [],
						isQuarter: status.is_quarter || false,
						parentRealmCanisterId: status.parent_realm_canister_id || '',
						loading: false
					}));
				} else {
					throw new Error('Failed to fetch quarter info');
				}
			} catch (error) {
				console.error('Error fetching quarters:', error);
				update((state: QuartersState) => ({
					...state,
					loading: false,
					error: error instanceof Error ? error.message : 'Unknown error'
				}));
			}
		}
	};
};

export const quartersStore = createQuartersStore();

// Active quarter canister ID (null = use parent backend directly)
export const activeQuarterId = writable<string | null>(null);

// Derived: list of quarters only
export const quartersList = derived(quartersStore, ($s: QuartersState) => $s.quarters);

// Derived: whether this realm has quarters
export const hasQuarters = derived(quartersStore, ($s: QuartersState) => $s.quarters.length > 0);

// Derived: whether this backend is itself a quarter
export const isQuarter = derived(quartersStore, ($s: QuartersState) => $s.isQuarter);
