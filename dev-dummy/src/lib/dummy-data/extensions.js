export const mockVaultData = {
  balance: 150000000,
  token: 'ckBTC',
  vaultStatus: { 
    name: 'Demo Vault', 
    principalId: 'vault-dummy-123456789abcdef' 
  }
};

export const mockCitizenServices = [
  {
    id: '1',
    name: 'Business License',
    description: 'Annual business operation license',
    status: 'active',
    due_date: '2025-12-31',
    provider: 'City Hall',
    link: '#'
  },
  {
    id: '2',
    name: 'Property Tax',
    description: 'Annual property tax payment',
    status: 'pending',
    due_date: '2025-08-15',
    provider: 'Tax Department',
    link: '#'
  },
  {
    id: '3',
    name: 'Health Permit',
    description: 'Food service health permit',
    status: 'expired',
    due_date: '2025-01-01',
    provider: 'Health Department',
    link: '#'
  }
];

export const mockPersonalData = {
  name: 'John Doe',
  email: 'john.doe@example.com',
  phone: '+1-555-0123',
  address: '123 Main St, Anytown, ST 12345',
  dateOfBirth: '1990-01-01',
  citizenship: 'US',
  verified: true
};

export const mockTaxInformation = [
  {
    year: '2024',
    status: 'filed',
    amount_owed: 0,
    amount_paid: 5500,
    due_date: '2024-04-15',
    filed_date: '2024-03-15'
  },
  {
    year: '2023',
    status: 'paid',
    amount_owed: 0,
    amount_paid: 5200,
    due_date: '2023-04-15',
    filed_date: '2023-03-10'
  }
];

export const mockNotifications = [
  {
    id: '1',
    title: 'Business License Renewal',
    message: 'Your business license expires in 30 days. Please renew to avoid penalties.',
    type: 'warning',
    timestamp: '2025-07-09T10:00:00Z',
    read: false,
    action_url: '#'
  },
  {
    id: '2',
    title: 'Tax Payment Confirmed',
    message: 'Your property tax payment of $2,500 has been processed successfully.',
    type: 'success',
    timestamp: '2025-07-08T14:30:00Z',
    read: true,
    action_url: '#'
  },
  {
    id: '3',
    title: 'New Service Available',
    message: 'Online permit applications are now available for construction projects.',
    type: 'info',
    timestamp: '2025-07-07T09:15:00Z',
    read: false,
    action_url: '#'
  }
];

export const mockLitigations = [
  {
    id: '1',
    title: 'Property Dispute Case #2024-001',
    description: 'Boundary dispute with neighboring property',
    status: 'pending',
    created_date: '2024-06-15',
    plaintiff: 'John Doe',
    defendant: 'Jane Smith',
    judge: 'Judge Wilson'
  },
  {
    id: '2',
    title: 'Contract Violation Case #2024-002',
    description: 'Breach of service contract terms',
    status: 'resolved',
    created_date: '2024-05-20',
    plaintiff: 'ABC Corp',
    defendant: 'XYZ Services',
    judge: 'Judge Martinez'
  }
];

export const mockLandRegistry = [
  {
    id: '1',
    parcel_id: 'LAND-001',
    address: '123 Oak Street',
    size: '0.25 acres',
    owner_type: 'individual',
    owner_name: 'John Doe',
    value: 250000,
    last_updated: '2024-01-15'
  },
  {
    id: '2',
    parcel_id: 'LAND-002',
    address: '456 Pine Avenue',
    size: '0.5 acres',
    owner_type: 'organization',
    owner_name: 'Green Valley LLC',
    value: 450000,
    last_updated: '2024-02-20'
  }
];

export const mockTransactions = [
  {
    id: '1',
    type: 'deposit',
    amount: 50000000,
    token: 'ckBTC',
    timestamp: '2025-07-09T08:30:00Z',
    status: 'completed',
    hash: 'tx_dummy_123456789'
  },
  {
    id: '2',
    type: 'withdrawal',
    amount: 25000000,
    token: 'ckBTC',
    timestamp: '2025-07-08T15:45:00Z',
    status: 'completed',
    hash: 'tx_dummy_987654321'
  }
];
