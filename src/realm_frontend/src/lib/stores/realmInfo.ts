import { writable, derived, get } from 'svelte/store';
import { backendStore } from '$lib/canisters';

interface RealmInfo {
	name: string;
	logo: string;
	loading: boolean;
	error: string | null;
}

const createRealmInfoStore = () => {
	const { subscribe, set, update } = writable<RealmInfo>({
		name: '',
		logo: '',
		loading: true,
		error: null
	});

	return {
		subscribe,
		fetch: async () => {
			update(state => ({ ...state, loading: true, error: null }));
			
			try {
				const currentActor = get(backendStore);
				if (!currentActor) {
					throw new Error('Actor not initialized');
				}

				const response = await currentActor.status();
				
				if (response.success && response.data.status) {
					const status = response.data.status;
					update(state => ({
						...state,
						name: status.realm_name || '',
						logo: status.realm_logo || '',
						loading: false
					}));
				} else {
					throw new Error('Failed to fetch realm info');
				}
			} catch (error) {
				console.error('Error fetching realm info:', error);
				update(state => ({
					...state,
					loading: false,
					error: error instanceof Error ? error.message : 'Unknown error'
				}));
			}
		}
	};
};

export const realmInfo = createRealmInfoStore();

// Derived store for just the logo URL
export const realmLogo = derived(realmInfo, $realmInfo => $realmInfo.logo);

// Derived store for just the realm name
export const realmName = derived(realmInfo, $realmInfo => $realmInfo.name);
