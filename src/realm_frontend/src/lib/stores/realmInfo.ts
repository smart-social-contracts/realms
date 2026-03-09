import { writable, derived, get } from 'svelte/store';
import { backendStore } from '$lib/canisters';

interface CanisterInfo {
	canister_id: string;
	canister_type: string;
}

interface QuarterInfo {
	name: string;
	canister_id: string;
	population: number;
	status: string;
}

interface RealmInfo {
	name: string;
	logo: string;
	welcomeImage: string;
	welcomeMessage: string;
	description: string;
	registries: CanisterInfo[];
	quarters: QuarterInfo[];
	isQuarter: boolean;
	parentRealmCanisterId: string;
	loading: boolean;
	error: string | null;
}

const createRealmInfoStore = () => {
	const { subscribe, set, update } = writable<RealmInfo>({
		name: '',
		logo: '',
		welcomeImage: '',
		welcomeMessage: '',
		description: '',
		registries: [],
		quarters: [],
		isQuarter: false,
		parentRealmCanisterId: '',
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
						welcomeImage: status.realm_welcome_image || '',
						welcomeMessage: status.realm_welcome_message || '',
						description: status.realm_description || '',
						registries: status.registries || [],
						loading: false
					}));

					// Fetch quarter info from dedicated endpoint
					// (workaround: Basilisk doesn't regenerate StatusRecord fields)
					try {
						const qResponse = await currentActor.get_quarter_info();
						if (qResponse.success && qResponse.data.message) {
							const qData = JSON.parse(qResponse.data.message);
							update(state => ({
								...state,
								quarters: qData.quarters || [],
								isQuarter: qData.is_quarter || false,
								parentRealmCanisterId: qData.parent_realm_canister_id || '',
							}));
						}
					} catch (qErr) {
						console.warn('Could not fetch quarter info:', qErr);
					}
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

// Derived store for welcome image
export const realmWelcomeImage = derived(realmInfo, $realmInfo => $realmInfo.welcomeImage);

// Derived store for welcome message
export const realmWelcomeMessage = derived(realmInfo, $realmInfo => $realmInfo.welcomeMessage);

// Derived store for realm description
export const realmDescription = derived(realmInfo, $realmInfo => $realmInfo.description);
