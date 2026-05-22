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
	welcomeMessage: string;
	description: string;
	openRegistration: boolean;
	registries: CanisterInfo[];
	quarters: QuarterInfo[];
	isQuarter: boolean;
	parentRealmCanisterId: string;
	logoUrl: string;
	backgroundImageUrl: string;
	testMode: boolean;
	testModeIIBypass: boolean;
	testModeUserSelfRegistration: boolean;
	testModeDemoData: boolean;
	testModeSkipTerms: boolean;
	testModeSkipPassportZkproof: boolean;
	loading: boolean;
	error: string | null;
}

const createRealmInfoStore = () => {
	const { subscribe, set, update } = writable<RealmInfo>({
		name: '',
		welcomeMessage: '',
		description: '',
		openRegistration: false,
		registries: [],
		quarters: [],
		isQuarter: false,
		parentRealmCanisterId: '',
		logoUrl: '',
		backgroundImageUrl: '',
		testMode: false,
		testModeIIBypass: false,
		testModeUserSelfRegistration: false,
		testModeDemoData: false,
		testModeSkipTerms: false,
		testModeSkipPassportZkproof: false,
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
						welcomeMessage: status.realm_welcome_message || '',
						description: status.realm_description || '',
						openRegistration: status.open_registration || false,
						registries: status.registries || [],
						quarters: status.quarters || [],
						isQuarter: status.is_quarter || false,
						parentRealmCanisterId: status.parent_realm_canister_id || '',
						logoUrl: status.logo_url || '',
						backgroundImageUrl: status.background_image_url || '',
						testMode: status.test_mode || false,
						testModeIIBypass: status.test_mode_ii_bypass || false,
						testModeUserSelfRegistration: status.test_mode_user_self_registration || false,
						testModeDemoData: status.test_mode_demo_data || false,
						testModeSkipTerms: status.test_mode_skip_terms || false,
						testModeSkipPassportZkproof: status.test_mode_skip_passport_zkproof || false,
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

// Derived store for just the realm name
export const realmName = derived(realmInfo, $realmInfo => $realmInfo.name);

// Derived store for welcome message
export const realmWelcomeMessage = derived(realmInfo, $realmInfo => $realmInfo.welcomeMessage);

// Derived store for realm description
export const realmDescription = derived(realmInfo, $realmInfo => $realmInfo.description);

// Derived store for open registration flag
export const realmOpenRegistration = derived(realmInfo, $realmInfo => $realmInfo.openRegistration);

// Derived stores for test mode flags (source of truth: backend status)
export const testMode = derived(realmInfo, $r => $r.testMode);
export const testModeIIBypass = derived(realmInfo, $r => $r.testModeIIBypass);
export const testModeUserSelfRegistration = derived(realmInfo, $r => $r.testModeUserSelfRegistration);
export const testModeDemoData = derived(realmInfo, $r => $r.testModeDemoData);
export const testModeSkipTerms = derived(realmInfo, $r => $r.testModeSkipTerms);
export const testModeSkipPassportZkproof = derived(realmInfo, $r => $r.testModeSkipPassportZkproof);
