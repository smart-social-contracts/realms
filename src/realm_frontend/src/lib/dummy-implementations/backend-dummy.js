const mockExtensionData = {
  vault_manager: {
    balance: 150000000, // 1.5 ckBTC in satoshis
    token: 'ckBTC',
    transactions: [
      { id: 1, type: 'receive', amount: 50000000, date: '2024-01-15', from: 'user123' },
      { id: 2, type: 'send', amount: 25000000, date: '2024-01-10', to: 'user456' }
    ]
  },
  citizen_dashboard: {
    services: [
      { id: 1, name: 'Health Insurance', status: 'active', provider: 'City Health Dept' },
      { id: 2, name: 'Vehicle Registration', status: 'pending', provider: 'DMV' }
    ],
    personalData: {
      name: 'John Doe',
      email: 'john.doe@example.com',
      address: '123 Main St, City, State'
    },
    taxInformation: [
      { year: 2023, amount_paid: 15000, amount_owed: 0, status: 'paid', filed_date: '2024-03-15' },
      { year: 2022, amount_paid: 12000, amount_owed: 500, status: 'filed', filed_date: '2023-04-10' }
    ]
  },
  notifications: [
    { id: 1, title: 'System Update', message: 'New features available', read: false, timestamp: '2024-01-15T10:00:00Z' },
    { id: 2, title: 'Payment Due', message: 'Tax payment due soon', read: true, timestamp: '2024-01-10T15:30:00Z' }
  ],
  justice_litigation: {
    litigations: [
      { id: 1, title: 'Contract Dispute', status: 'pending', created_date: '2024-01-01' },
      { id: 2, title: 'Property Claim', status: 'resolved', created_date: '2023-12-15' }
    ]
  },
  land_registry: {
    properties: [
      { id: 1, address: '123 Main St', owner: 'John Doe', status: 'registered' },
      { id: 2, address: '456 Oak Ave', owner: 'Jane Smith', status: 'pending' }
    ]
  }
};

export class DummyBackend {
  async extension_sync_call(params) {
    const { extension_name, function_name, args } = params;
    console.log(`🔧 DEV MODE: extension_sync_call(${extension_name}, ${function_name})`, args);
    
    let parsedArgs = {};
    try {
      parsedArgs = typeof args === 'string' ? JSON.parse(args) : args;
    } catch (e) {
      console.warn('Could not parse args:', args);
    }
    
    switch (extension_name) {
      case 'vault_manager':
        if (function_name === 'get_balance') return { success: true, data: { Balance: { amount: mockExtensionData.vault_manager.balance, principal_id: 'dummy-principal' } } };
        if (function_name === 'get_transactions') return { success: true, data: mockExtensionData.vault_manager.transactions };
        if (function_name === 'transfer') return { success: true, data: { transaction_id: 'dummy-tx-123' } };
        break;
      case 'citizen_dashboard':
        if (function_name === 'get_public_services') return { success: true, data: mockExtensionData.citizen_dashboard.services };
        if (function_name === 'get_personal_data') return { success: true, data: mockExtensionData.citizen_dashboard.personalData };
        if (function_name === 'get_tax_information') return { success: true, data: mockExtensionData.citizen_dashboard.taxInformation };
        if (function_name === 'get_dashboard_summary') return { success: true, data: { services_count: 2, notifications_count: 1 } };
        break;
      case 'notifications':
        if (function_name === 'get_notifications') return { success: true, data: mockExtensionData.notifications };
        if (function_name === 'mark_as_read') return { success: true, data: null };
        break;
      case 'justice_litigation':
        if (function_name === 'get_litigations') return { success: true, data: mockExtensionData.justice_litigation.litigations };
        if (function_name === 'create_litigation') return { success: true, data: { litigation_id: 'dummy-litigation-123' } };
        if (function_name === 'execute_verdict') return { success: true, data: { verdict_executed: true } };
        break;
      case 'land_registry':
        if (function_name === 'get_properties') return { success: true, data: mockExtensionData.land_registry.properties };
        if (function_name === 'register_property') return { success: true, data: { property_id: 'dummy-property-123' } };
        break;
      case 'test_bench':
        if (function_name === 'get_data') return { success: true, data: 'Hello from dummy test bench!' };
        break;
    }
    
    return { success: true, data: null };
  }

  async extension_async_call(params) {
    console.log(`🔧 DEV MODE: extension_async_call`, params);
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    return this.extension_sync_call(params);
  }

  async get_user_profiles() {
    console.log('🔧 DEV MODE: get_user_profiles called');
    return ['admin', 'member'];
  }

  async get_my_user_status() {
    console.log('🔧 DEV MODE: get_my_user_status called');
    return {
      success: true,
      data: {
        UserGet: {
          principal: 'dummy-principal-123456789',
          profiles: ['admin', 'member']
        }
      }
    };
  }

  // Entity fetch methods for Admin Dashboard
  async get_users(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_users called', { page_num, page_size });
    const mockUsers = [
      '{"_id": "1", "id": "system", "profile_picture_url": "", "_type": "User", "timestamp_created": "2025-09-07 16:08:44.940"}',
      '{"_id": "2", "id": "laura_foster_000", "profile_picture_url": "https://api.dicebear.com/7.x/personas/svg?seed=LauraFoster", "_type": "User", "timestamp_created": "2025-09-07 16:08:46.475"}',
      '{"_id": "3", "id": "edward_clark_001", "profile_picture_url": "https://api.dicebear.com/7.x/personas/svg?seed=EdwardClark", "_type": "User", "timestamp_created": "2025-09-07 16:08:46.475"}',
      '{"_id": "4", "id": "carlos_young_002", "profile_picture_url": "https://api.dicebear.com/7.x/personas/svg?seed=CarlosYoung", "_type": "User", "timestamp_created": "2025-09-07 16:08:46.475"}',
      '{"_id": "5", "id": "rachel_fisher_006", "profile_picture_url": "https://api.dicebear.com/7.x/personas/svg?seed=RachelFisher", "_type": "User", "timestamp_created": "2025-09-07 16:08:49.444"}'
    ];
    
    return {
      success: true,
      data: {
        UsersList: {
          users: mockUsers,
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 52,
            total_pages: Math.ceil(52 / page_size)
          }
        }
      }
    };
  }

  async get_mandates(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_mandates called', { page_num, page_size });
    const mockMandates = [
      '{"_id": "1", "name": "Tax Collection", "metadata": null, "_type": "Mandate", "timestamp_created": "2025-09-07 16:10:57.089"}',
      '{"_id": "2", "name": "Social Benefits", "metadata": null, "_type": "Mandate", "timestamp_created": "2025-09-07 16:10:57.089"}',
      '{"_id": "3", "name": "License Management", "metadata": null, "_type": "Mandate", "timestamp_created": "2025-09-07 16:10:58.503"}',
      '{"_id": "4", "name": "Land Registry", "metadata": null, "_type": "Mandate", "timestamp_created": "2025-09-07 16:10:58.503"}',
      '{"_id": "5", "name": "Voting System", "metadata": null, "_type": "Mandate", "timestamp_created": "2025-09-07 16:10:58.503"}',
      '{"_id": "6", "name": "Healthcare Services", "metadata": null, "_type": "Mandate", "timestamp_created": "2025-09-07 16:10:59.930"}'
    ];
    
    return {
      success: true,
      data: {
        MandatesList: {
          mandates: mockMandates,
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 6,
            total_pages: Math.ceil(6 / page_size)
          }
        }
      }
    };
  }

  async get_tasks(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_tasks called', { page_num, page_size });
    return {
      success: true,
      data: {
        TasksList: {
          tasks: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_transfers(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_transfers called', { page_num, page_size });
    return {
      success: true,
      data: {
        TransfersList: {
          transfers: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_instruments(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_instruments called', { page_num, page_size });
    return {
      success: true,
      data: {
        InstrumentsList: {
          instruments: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_codexes(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_codexes called', { page_num, page_size });
    return {
      success: true,
      data: {
        CodexesList: {
          codexes: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_organizations(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_organizations called', { page_num, page_size });
    return {
      success: true,
      data: {
        OrganizationsList: {
          organizations: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_disputes(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_disputes called', { page_num, page_size });
    return {
      success: true,
      data: {
        DisputesList: {
          disputes: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_licenses(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_licenses called', { page_num, page_size });
    return {
      success: true,
      data: {
        LicensesList: {
          licenses: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_trades(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_trades called', { page_num, page_size });
    return {
      success: true,
      data: {
        TradesList: {
          trades: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_realms(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_realms called', { page_num, page_size });
    const mockRealms = [
      '{"_id": "1", "name": "Nova Republic", "description": "A progressive digital sovereign realm", "_type": "Realm", "timestamp_created": "2025-09-07 16:08:44.940"}'
    ];
    
    return {
      success: true,
      data: {
        RealmsList: {
          realms: mockRealms,
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 1,
            total_pages: 1
          }
        }
      }
    };
  }

  async get_proposals(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_proposals called', { page_num, page_size });
    return {
      success: true,
      data: {
        ProposalsList: {
          proposals: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_votes(page_num = 0, page_size = 10) {
    console.log('🔧 DEV MODE: get_votes called', { page_num, page_size });
    return {
      success: true,
      data: {
        VotesList: {
          votes: [],
          pagination: {
            page_num: page_num,
            page_size: page_size,
            total_items_count: 0,
            total_pages: 0
          }
        }
      }
    };
  }

  async get_organizations() {
    console.log('🔧 DEV MODE: get_organizations called');
    return [
      { id: 1, name: 'City Council', members: 12, status: 'active' },
      { id: 2, name: 'School Board', members: 8, status: 'active' }
    ];
  }

  async get_universe() {
    console.log('🔧 DEV MODE: get_universe called');
    return { name: 'Dummy Universe', version: '1.0.0', extensions: ['vault_manager', 'citizen_dashboard'] };
  }

  async get_snapshots() {
    console.log('🔧 DEV MODE: get_snapshots called');
    return [
      { id: 1, name: 'Snapshot 1', timestamp: '2024-01-15T10:00:00Z' },
      { id: 2, name: 'Snapshot 2', timestamp: '2024-01-10T15:30:00Z' }
    ];
  }

  async greet(name) {
    console.log('🔧 DEV MODE: greet called with:', name);
    return `Hello, ${name}! This is a dummy greeting from dev mode.`;
  }

  async get_extensions() {
    console.log('🔧 DEV MODE: get_extensions called');
    const mockExtensions = [
      {
        name: 'citizen_dashboard',
        description: 'Citizen Dashboard for public services',
        version: '1.0.0',
        author: 'Realms Team',
        categories: ['public_services'],
        profiles: ['citizen', 'admin'],
        icon: 'dashboard',
        url: '/extensions/citizen_dashboard'
      },
      {
        name: 'vault_manager',
        description: 'Manage your digital vault and tokens',
        version: '1.0.0',
        author: 'Realms Team',
        categories: ['finances'],
        profiles: ['citizen', 'admin'],
        icon: 'wallet',
        url: '/extensions/vault_manager'
      },
      {
        name: 'passport_verification',
        description: 'Verify and manage digital identity',
        version: '1.0.0',
        author: 'Realms Team',
        categories: ['identity'],
        profiles: ['citizen', 'admin'],
        icon: 'id-card',
        url: '/extensions/passport_verification'
      },
      {
        name: 'notifications',
        description: 'System notifications and alerts',
        version: '1.0.0',
        author: 'Realms Team',
        categories: ['other'],
        profiles: ['citizen', 'admin'],
        icon: 'bell',
        url: '/extensions/notifications'
      }
    ];

    return {
      success: true,
      data: {
        ExtensionsList: {
          extensions: mockExtensions.map(ext => JSON.stringify(ext))
        }
      }
    };
  }
}

export const dummyBackend = new DummyBackend();
