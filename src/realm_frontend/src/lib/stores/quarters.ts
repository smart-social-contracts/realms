import { writable, derived, get } from 'svelte/store';
import { backendStore, backendActorReady } from '$lib/canisters';

const STATUS_QUERY_TIMEOUT_MS = 12_000;

function withQueryTimeout<T>(
	promise: Promise<T>,
	ms: number,
	label: string
): Promise<T | null> {
	return new Promise((resolve) => {
		let settled = false;
		const timer = setTimeout(() => {
			if (!settled) {
				console.warn(`[quarters] ${label} timed out after ${ms}ms`);
				settled = true;
				resolve(null);
			}
		}, ms);
		promise
			.then((value) => {
				if (!settled) {
					settled = true;
					clearTimeout(timer);
					resolve(value);
				}
			})
			.catch((err) => {
				if (!settled) {
					settled = true;
					clearTimeout(timer);
					console.warn(`[quarters] ${label} failed:`, err);
					resolve(null);
				}
			});
	});
}

export interface QuarterInfo {
	name: string;
	canister_id: string;
	population: number;
	status: string;
}

export interface QuartersState {
	quarters: QuarterInfo[];
	isQuarter: boolean;
	isCapital: boolean;
	parentRealmCanisterId: string;
	loading: boolean;
	error: string | null;
}

const createQuartersStore = () => {
	const { subscribe, set, update } = writable<QuartersState>({
		quarters: [],
		isQuarter: false,
		isCapital: false,
		parentRealmCanisterId: '',
		loading: true,
		error: null
	});

	return {
		subscribe,
		fetch: async () => {
			update((state: QuartersState) => ({ ...state, loading: true, error: null }));

		try {
			// Await the provisional actor, not backendReady — see realmInfo.ts
			// (backendReady includes auth init, which awaits these fetches).
			await backendActorReady;
			const currentActor = get(backendStore);
				if (!currentActor) {
					throw new Error('Actor not initialized');
				}

				const response = await withQueryTimeout(
					currentActor.status(),
					STATUS_QUERY_TIMEOUT_MS,
					'status'
				);

				if (response?.success && response.data.status) {
					const status = response.data.status;
					update((state: QuartersState) => ({
						...state,
						quarters: status.quarters || [],
						isQuarter: status.is_quarter || false,
						isCapital: status.is_capital || false,
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

// Derived: whether this backend is the capital quarter of a federation
export const isCapital = derived(quartersStore, ($s: QuartersState) => $s.isCapital);
