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
