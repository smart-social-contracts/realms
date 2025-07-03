const DUMMY_USER_PRINCIPAL = "rdmx6-jaaaa-aaaah-qcaiq-cai";
const DUMMY_REALM_NAME = "Demo Realm";

const mockUsers = [
  { id: "user1", principal: DUMMY_USER_PRINCIPAL, profiles: ["member"], name: "Demo User" },
  { id: "user2", principal: "admin-principal", profiles: ["admin"], name: "Admin User" }
];

const mockOrganizations = [
  { id: "org1", name: "Demo Organization", members: 5, tokens: [] }
];

const extensionMocks = {
  notifications: {
    get_notifications: { success: true, data: { notifications: [] } },
    mark_as_read: { success: true, data: {} }
  },
  vault_manager: {
    get_balance: { success: true, data: { balance: 1000 } },
    get_transactions: { success: true, data: { transactions: [] } }
  },
  justice_litigation: {
    get_litigations: { success: true, data: { litigations: [] } },
    create_litigation: { success: true, data: { id: "lit1" } },
    execute_verdict: { success: true, data: {} }
  },
  land_registry: {
    get_lands: { success: true, data: { lands: [] } },
    create_land: { success: true, data: { id: "land1" } },
    update_land_ownership: { success: true, data: {} }
  },
  citizen_dashboard: {
    get_dashboard_summary: { success: true, data: { summary: {} } },
    get_personal_data: { success: true, data: { personal_data: {} } },
    get_public_services: { success: true, data: { services: [] } },
    get_tax_information: { success: true, data: { tax_info: {} } }
  }
};

export function createDummyBackend() {
  console.log('[DUMMY] Creating dummy backend');
  return {
    status: async () => ({
      success: true,
      data: {
        Status: {
          demo_mode: true,
          version: "dev-dummy",
          canister_id: "dummy-canister"
        }
      }
    }),

    get_my_user_status: async () => ({
      success: true,
      data: {
        UserGet: {
          principal: DUMMY_USER_PRINCIPAL,
          profiles: ["member"]
        }
      }
    }),

    join_realm: async (profile) => ({
      success: true,
      data: {
        message: `Successfully joined realm as ${profile}`
      }
    }),

    get_universe: async () => ({
      success: true,
      data: { universe: "dummy-universe" }
    }),

    get_snapshots: async () => ({
      success: true,
      data: { snapshots: [] }
    }),

    get_users: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        UsersList: {
          users: mockUsers.slice(page_num * page_size, (page_num + 1) * page_size),
          pagination: { total: mockUsers.length, page: page_num, per_page: page_size }
        }
      }
    }),

    get_mandates: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        MandatesList: {
          mandates: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_tasks: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        TasksList: {
          tasks: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_transfers: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        TransfersList: {
          transfers: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_instruments: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        InstrumentsList: {
          instruments: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_codexes: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        CodexesList: {
          codexes: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_organizations: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        OrganizationsList: {
          organizations: mockOrganizations.slice(page_num * page_size, (page_num + 1) * page_size),
          pagination: { total: mockOrganizations.length, page: page_num, per_page: page_size }
        }
      }
    }),

    get_disputes: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        DisputesList: {
          disputes: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_licenses: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        LicensesList: {
          licenses: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_trades: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        TradesList: {
          trades: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_realms: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        RealmsList: {
          realms: [{ id: "realm1", name: DUMMY_REALM_NAME }],
          pagination: { total: 1, page: page_num, per_page: page_size }
        }
      }
    }),

    get_proposals: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        ProposalsList: {
          proposals: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_votes: async (page_num = 0, page_size = 5) => ({
      success: true,
      data: {
        VotesList: {
          votes: [],
          pagination: { total: 0, page: page_num, per_page: page_size }
        }
      }
    }),

    get_organization_data: async (id) => ({
      success: true,
      data: mockOrganizations.find(org => org.id === id) || mockOrganizations[0]
    }),

    get_proposal_data: async (id) => ({
      success: true,
      data: { id, title: "Demo Proposal", status: "active" }
    }),

    extension_sync_call: async ({ extension_name, function_name, args }) => {
      console.log(`[DUMMY] Extension call: ${extension_name}.${function_name}`, args);
      
      const extensionMock = extensionMocks[extension_name];
      if (extensionMock && extensionMock[function_name]) {
        return extensionMock[function_name];
      }
      
      return {
        success: true,
        data: { message: `Dummy response for ${extension_name}.${function_name}` }
      };
    }
  };
}
