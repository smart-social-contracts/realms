
console.log('=== ULTRA MINIMAL CANISTERS LOADING ===');

const dummyBackend = {
    status: async () => ({ success: true, data: { Status: { demo_mode: true } } }),
    get_my_user_status: async () => ({ success: true, data: { UserGet: { principal: "demo-user", profiles: ["member"] } } }),
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

// Simple store implementation without importing svelte/store
let storeValue = dummyBackend;
const subscribers = [];

const backendStore = {
    subscribe: (callback) => {
        subscribers.push(callback);
        callback(storeValue);
        return () => {
            const index = subscribers.indexOf(callback);
            if (index !== -1) subscribers.splice(index, 1);
        };
    },
    set: (value) => {
        storeValue = value;
        subscribers.forEach(callback => callback(value));
    },
    update: (updater) => {
        storeValue = updater(storeValue);
        subscribers.forEach(callback => callback(storeValue));
    }
};

export const backend = dummyBackend;
export { backendStore };

export async function initBackendWithIdentity() {
    console.log('=== INIT BACKEND WITH IDENTITY (DUMMY) ===');
    return dummyBackend;
}

console.log('=== ULTRA MINIMAL CANISTERS LOADED ===');
