console.log('=== DUMMY CANISTERS MODULE LOADED ===');

const dummyBackend = {
    status: async () => ({ success: true, data: { Status: { demo_mode: true } } }),
    get_my_user_status: async () => ({ success: true, data: { UserGet: { principal: "dummy-principal", profiles: ["member"] } } }),
    join_realm: async (profile) => ({ success: true, data: { message: `Joined as ${profile}` } }),
    get_universe: async () => ({ success: true, data: { universe: "dummy-universe" } }),
    get_snapshots: async () => ({ success: true, data: { snapshots: [] } }),
    
    get_users: async (page_num = 0, page_size = 5) => ({ success: true, data: { UsersList: { users: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_organizations: async (page_num = 0, page_size = 5) => ({ success: true, data: { OrganizationsList: { organizations: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_mandates: async (page_num = 0, page_size = 5) => ({ success: true, data: { MandatesList: { mandates: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_tasks: async (page_num = 0, page_size = 5) => ({ success: true, data: { TasksList: { tasks: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_transfers: async (page_num = 0, page_size = 5) => ({ success: true, data: { TransfersList: { transfers: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_instruments: async (page_num = 0, page_size = 5) => ({ success: true, data: { InstrumentsList: { instruments: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_codexes: async (page_num = 0, page_size = 5) => ({ success: true, data: { CodexesList: { codexes: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_disputes: async (page_num = 0, page_size = 5) => ({ success: true, data: { DisputesList: { disputes: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_licenses: async (page_num = 0, page_size = 5) => ({ success: true, data: { LicensesList: { licenses: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_trades: async (page_num = 0, page_size = 5) => ({ success: true, data: { TradesList: { trades: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_realms: async (page_num = 0, page_size = 5) => ({ success: true, data: { RealmsList: { realms: [{ id: "realm1", name: "Demo Realm" }], pagination: { total: 1, page: page_num, per_page: page_size } } } }),
    get_proposals: async (page_num = 0, page_size = 5) => ({ success: true, data: { ProposalsList: { proposals: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    get_votes: async (page_num = 0, page_size = 5) => ({ success: true, data: { VotesList: { votes: [], pagination: { total: 0, page: page_num, per_page: page_size } } } }),
    
    extension_sync_call: async ({ extension_name, function_name, args }) => {
        console.log(`[DUMMY] Extension call: ${extension_name}.${function_name}`, args);
        return { success: true, data: { message: `Dummy response for ${extension_name}.${function_name}` } };
    },
    
    greet: async (name) => `Hello, ${name}! (dummy response)`,
    get_organization_data: async (id) => ({ success: true, data: { id, name: "Demo Organization" } }),
    get_proposal_data: async (id) => ({ success: true, data: { id, title: "Demo Proposal", status: "active" } }),
    get_stats: async () => ({ success: true, data: [] })
};

export const backend = dummyBackend;

export const backendStore = {
    set: () => {},
    subscribe: (callback) => { 
        callback(dummyBackend); 
        return () => {}; 
    }
};

export async function initBackendWithIdentity() {
    console.log('initBackendWithIdentity - returning dummy backend');
    return dummyBackend;
}

console.log('Dummy canisters module ready for UI/UX development');
