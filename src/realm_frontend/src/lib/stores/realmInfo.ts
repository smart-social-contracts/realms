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
	manifesto: string;
	openRegistration: boolean;
	aiAssistantEnabled: boolean;
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
		manifesto: '',
		openRegistration: false,
		aiAssistantEnabled: true,
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

				// Prefer the lightweight runtime-flags query (fast on large realms).
				// Full status() may exceed the instruction limit; flags alone are enough
				// for the join flow (test mode, open registration, branding).
				let flagsPayload: Record<string, unknown> | null = null;
				try {
					const flagsRaw = await currentActor.get_runtime_flags();
					flagsPayload = typeof flagsRaw === 'string' ? JSON.parse(flagsRaw) : flagsRaw;
				} catch {
					flagsPayload = null;
				}

				let status: Record<string, unknown> | null = null;
				try {
					const response = await currentActor.status();
					if (response.success && response.data.status) {
						status = response.data.status as Record<string, unknown>;
					}
				} catch {
					status = null;
				}

				// status().quarters counts populations by scanning the capital's own
				// user table, which misses members who joined a quarter directly (they
				// live in the quarter's table) — sub-quarters show 0 forever. The
				// join-targets directory carries the synced per-quarter counts plus
				// index/is_capital, so overlay it. Best-effort: the raw status list
				// still renders if this query fails.
				const quarters = (status?.quarters as Array<Record<string, unknown>>) || [];
				if (quarters.length > 0) {
					try {
						const raw = await currentActor.get_join_targets();
						const directory = (JSON.parse(raw)?.quarters || []) as Array<
							Record<string, unknown>
						>;
						for (const q of quarters) {
							const match = directory.find((d) => d.canister_id === q.canister_id);
							if (!match) continue;
							q.population = Math.max(Number(q.population ?? 0), Number(match.population ?? 0));
							if (q.index === undefined && match.index !== undefined) q.index = match.index;
							if (q.is_capital === undefined && match.is_capital !== undefined)
								q.is_capital = match.is_capital;
						}
					} catch {
						// keep the unmodified status list
					}
				}

				if (status || flagsPayload?.success) {
					const fromFlags = flagsPayload?.success ? flagsPayload : null;
					const openFromFlags = fromFlags?.open_registration as boolean | undefined;
					const openFromStatus = status?.open_registration as boolean | undefined;
					update(state => ({
						...state,
						name: (fromFlags?.realm_name as string) || (status?.realm_name as string) || '',
						welcomeMessage: (fromFlags?.realm_welcome_message as string) || (status?.realm_welcome_message as string) || '',
						manifesto: (fromFlags?.realm_manifesto as string) || (status?.realm_manifesto as string) || '',
						openRegistration: openFromFlags ?? openFromStatus ?? false,
						aiAssistantEnabled: (fromFlags?.ai_assistant_enabled as boolean) ?? (status?.ai_assistant_enabled as boolean) !== false,
						registries: (status?.registries as typeof state.registries) || [],
						quarters: (status?.quarters as typeof state.quarters) || [],
						isQuarter: (status?.is_quarter as boolean) || false,
						parentRealmCanisterId: (status?.parent_realm_canister_id as string) || '',
						logoUrl: (fromFlags?.logo_url as string) || (status?.logo_url as string) || '',
						backgroundImageUrl: (fromFlags?.background_image_url as string) || (status?.background_image_url as string) || '',
						testMode: (fromFlags?.test_mode as boolean) ?? (status?.test_mode as boolean) ?? false,
						testModeIIBypass: (fromFlags?.test_mode_ii_bypass as boolean) ?? (status?.test_mode_ii_bypass as boolean) ?? false,
						testModeUserSelfRegistration: (fromFlags?.test_mode_user_self_registration as boolean) ?? (status?.test_mode_user_self_registration as boolean) ?? false,
						testModeDemoData: (fromFlags?.test_mode_demo_data as boolean) ?? (status?.test_mode_demo_data as boolean) ?? false,
						testModeSkipTerms: (fromFlags?.test_mode_skip_terms as boolean) ?? (status?.test_mode_skip_terms as boolean) ?? false,
						testModeSkipPassportZkproof: (fromFlags?.test_mode_skip_passport_zkproof as boolean) ?? (status?.test_mode_skip_passport_zkproof as boolean) ?? false,
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

// Derived store for realm manifesto
export const realmManifesto = derived(realmInfo, $realmInfo => $realmInfo.manifesto);

// Derived store for open registration flag
export const realmOpenRegistration = derived(realmInfo, $realmInfo => $realmInfo.openRegistration);

export const aiAssistantEnabled = derived(realmInfo, $realmInfo => $realmInfo.aiAssistantEnabled);

// Derived stores for test mode flags (source of truth: backend status)
export const testMode = derived(realmInfo, $r => $r.testMode);
export const testModeIIBypass = derived(realmInfo, $r => $r.testModeIIBypass);
export const testModeUserSelfRegistration = derived(realmInfo, $r => $r.testModeUserSelfRegistration);
export const testModeDemoData = derived(realmInfo, $r => $r.testModeDemoData);
export const testModeSkipTerms = derived(realmInfo, $r => $r.testModeSkipTerms);
export const testModeSkipPassportZkproof = derived(realmInfo, $r => $r.testModeSkipPassportZkproof);
