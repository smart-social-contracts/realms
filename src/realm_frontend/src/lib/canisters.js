
import { building } from '$app/environment';
import { writable, get } from 'svelte/store';

const isDevDummyMode = typeof window !== 'undefined' && import.meta.env.DEV_DUMMY_MODE === 'true';
const buildingOrTesting = building || process.env.NODE_ENV === "test";

console.log('Canisters loading - DEV_DUMMY_MODE:', isDevDummyMode, 'Building:', buildingOrTesting);

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

const dummyBackend = {
    status: async () => ({ success: true, data: { Status: { demo_mode: true } } }),
    get_my_user_status: async () => ({ success: true, data: { UserGet: { principal: "dummy-user", profiles: ["admin", "member"] } } }),
    join_realm: async (profile) => ({ success: true, data: { message: `Joined as ${profile}` } }),
    get_users: async (page = 0, size = 5) => ({ success: true, data: { UsersList: { users: [], pagination: { total: 0, page, per_page: size } } } }),
    get_organizations: async (page = 0, size = 5) => ({ success: true, data: { OrganizationsList: { organizations: [], pagination: { total: 0, page, per_page: size } } } }),
    get_proposals: async (page = 0, size = 5) => ({ success: true, data: { ProposalsList: { proposals: [], pagination: { total: 0, page, per_page: size } } } }),
    get_mandates: async (page = 0, size = 5) => ({ success: true, data: { MandatesList: { mandates: [], pagination: { total: 0, page, per_page: size } } } }),
    get_tasks: async (page = 0, size = 5) => ({ success: true, data: { TasksList: { tasks: [], pagination: { total: 0, page, per_page: size } } } }),
    get_transfers: async (page = 0, size = 5) => ({ success: true, data: { TransfersList: { transfers: [], pagination: { total: 0, page, per_page: size } } } }),
    get_instruments: async (page = 0, size = 5) => ({ success: true, data: { InstrumentsList: { instruments: [], pagination: { total: 0, page, per_page: size } } } }),
    get_codexes: async (page = 0, size = 5) => ({ success: true, data: { CodexesList: { codexes: [], pagination: { total: 0, page, per_page: size } } } }),
    get_disputes: async (page = 0, size = 5) => ({ success: true, data: { DisputesList: { disputes: [], pagination: { total: 0, page, per_page: size } } } }),
    get_licenses: async (page = 0, size = 5) => ({ success: true, data: { LicensesList: { licenses: [], pagination: { total: 0, page, per_page: size } } } }),
    get_trades: async (page = 0, size = 5) => ({ success: true, data: { TradesList: { trades: [], pagination: { total: 0, page, per_page: size } } } }),
    get_realms: async (page = 0, size = 5) => ({ success: true, data: { RealmsList: { realms: [], pagination: { total: 0, page, per_page: size } } } }),
    get_votes: async (page = 0, size = 5) => ({ success: true, data: { VotesList: { votes: [], pagination: { total: 0, page, per_page: size } } } }),
    get_organization_data: async (id) => ({ success: true, data: { id, name: "Demo Organization" } }),
    get_proposal_data: async (id) => ({ success: true, data: { id, title: "Demo Proposal" } }),
    extension_sync_call: async ({ extension_name, function_name, args }) => ({ success: true, data: { message: `Dummy ${extension_name}.${function_name}` } }),
    extension_async_call: async ({ extension_name, function_name, args }) => ({ success: true, data: { message: `Dummy async ${extension_name}.${function_name}` } }),
    get_universe: async () => ({ success: true, data: { universe: "dummy" } }),
    get_snapshots: async () => ({ success: true, data: { snapshots: [] } }),
    greet: async (name) => `Hello, ${name}! (dummy)`,
    get_stats: async () => ({ success: true, data: [] })
};

let initialBackend;
if (buildingOrTesting) {
    initialBackend = dummyActor();
} else if (isDevDummyMode) {
    console.log('DEV_DUMMY_MODE: Using dummy backend');
    initialBackend = dummyBackend;
} else {
    console.log('Normal mode: Starting with dummy backend, will attempt to load real backend');
    initialBackend = dummyBackend;
}

export const backendStore = writable(initialBackend);

// Create a proxy that always uses the latest actor from the store
export const backend = new Proxy({}, {
    get: function(target, prop) {
        const actor = get(backendStore);
        return actor[prop];
    }
});

if (!buildingOrTesting && !isDevDummyMode) {
    setTimeout(async () => {
        try {
            const modulePath = 'declarations/realm_backend';
            const backendModule = await import(/* @vite-ignore */ modulePath);
            const { createActor, canisterId } = backendModule;
            
            console.log('Normal mode: Successfully loaded backend declarations');
            const realBackend = createActor(canisterId);
            backendStore.set(realBackend);
            console.log('Normal mode: Initialized real backend');
        } catch (error) {
            console.warn('Normal mode: Failed to load backend declarations, using dummy backend:', error);
            console.warn('This is expected if dfx generate realm_backend has not been run');
        }
    }, 0);
}

export async function initBackendWithIdentity() {
    if (isDevDummyMode) {
        console.log('DEV_DUMMY_MODE: Using dummy backend for authentication');
        return dummyBackend;
    }
    
    try {
        console.log('Initializing backend with authenticated identity...');
        
        const authModulePath = '$lib/auth';
        const backendModulePath = 'declarations/realm_backend';
        const agentModulePath = '@dfinity/agent';
        
        const [authModule, backendModule, agentModule] = await Promise.all([
            import(/* @vite-ignore */ authModulePath).catch(() => null),
            import(/* @vite-ignore */ backendModulePath).catch(() => null),
            import(/* @vite-ignore */ agentModulePath).catch(() => null)
        ]);
        
        if (!authModule || !backendModule || !agentModule) {
            console.warn('Failed to load required modules for authentication, using current backend');
            return backend;
        }
        
        const { authClient, initializeAuthClient } = authModule;
        const { createActor, canisterId } = backendModule;
        const { HttpAgent } = agentModule;
        
        const client = authClient || await initializeAuthClient();
        
        if (await client.isAuthenticated()) {
            const identity = client.getIdentity();
            console.log('Using authenticated identity:', identity.getPrincipal().toText());
            
            const currentActor = get(backendStore);
            if (currentActor && currentActor._agent && currentActor._agent._identity === identity) {
                console.log('Backend already initialized with current identity');
                return currentActor;
            }
            
            const agent = new HttpAgent({ identity });
            
            const isLocalDevelopment = typeof window !== 'undefined' && 
                (window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1'));
            
            if (isLocalDevelopment) {
                console.log('Fetching root key for local development');
                await agent.fetchRootKey().catch(e => {
                    console.warn('Error fetching root key:', e);
                });
            }
            
            const authenticatedActor = createActor(canisterId, { agent });
            backendStore.set(authenticatedActor);
            
            console.log('Backend initialized with authenticated identity');
            return authenticatedActor;
        } else {
            console.log('User not authenticated, using anonymous identity');
            return backend;
        }
    } catch (error) {
        console.error('Error initializing backend with identity:', error);
        return backend;
    }
}
