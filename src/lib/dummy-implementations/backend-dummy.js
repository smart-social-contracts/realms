const mockExtensionData = {
  vault: {
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
    }
  },
  notifications: [
    { id: 1, title: 'System Update', message: 'New features available', read: false },
    { id: 2, title: 'Payment Due', message: 'Tax payment due soon', read: true }
  ]
};

export class DummyBackend {
  async extension_sync_call(extensionName, method, args = []) {
    console.log(`🔧 DEV MODE: extension_sync_call(${extensionName}, ${method})`, args);
    
    switch (extensionName) {
      case 'vault_manager':
        if (method === 'get_balance') return mockExtensionData.vault_manager.balance;
        if (method === 'get_transactions') return mockExtensionData.vault_manager.transactions;
        break;
      case 'citizen_dashboard':
        if (method === 'get_services') return mockExtensionData.citizen_dashboard.services;
        if (method === 'get_personal_data') return mockExtensionData.citizen_dashboard.personalData;
        break;
      case 'notifications':
        if (method === 'get_notifications') return mockExtensionData.notifications;
        break;
    }
    
    return { success: true, data: null };
  }

  async extension_async_call(extensionName, method, args = []) {
    console.log(`🔧 DEV MODE: extension_async_call(${extensionName}, ${method})`, args);
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    return this.extension_sync_call(extensionName, method, args);
  }

  async get_user_profiles() {
    console.log('🔧 DEV MODE: get_user_profiles called');
    return ['admin', 'member'];
  }

  async get_organizations() {
    console.log('🔧 DEV MODE: get_organizations called');
    return [
      { id: 1, name: 'City Council', members: 12, status: 'active' },
      { id: 2, name: 'School Board', members: 8, status: 'active' }
    ];
  }
}

export const dummyBackend = new DummyBackend();
