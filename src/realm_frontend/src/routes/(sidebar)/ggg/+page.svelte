<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  
  import GenericEntityTable from '$lib/components/ggg/GenericEntityTable.svelte';
  import CodexViewer from '$lib/components/ggg/CodexViewer.svelte';
  
  let activeTab = 'dashboard';
  let loading = false;
  let error = null;
  let data = {};
  let metrics = {};
  let relationships = [];
  let recentActivity = [];
  let filterQuery = '';
  let selectedFilter = 'all';
  
  // Add pagination state for transfers
  let transfersPage = 0;
  let transfersPerPage = 5;
  let transfersPagination = null;
  let searchTerm = '';
  
  // Handle pagination for transfers
  async function handleTransfersPageChange(page) {
    // page is 0-based from the table, so use as is
    transfersPage = page;
    await fetchEntityData('transfers');
  }
  
  // Static list of all known GGG entity types - always show these tabs
  const allEntityTypes = [
    'users',
    'mandates', 
    'tasks',
    'transfers',
    'instruments',
    'codexes',
    'organizations',
    'disputes',
    'licenses',
    'trades',
    'realms',
    'proposals',
    'votes'
  ];
  
  // Entity type configurations with their API endpoints
  const entityConfigs = [
    { name: 'users', fetch: () => backend.get_users(), dataPath: 'UsersList.users' },
    { name: 'mandates', fetch: () => backend.get_mandates(), dataPath: 'MandatesList.mandates' },
    { name: 'tasks', fetch: () => backend.get_tasks(), dataPath: 'TasksList.tasks' },
    { 
      name: 'transfers', 
      fetch: (page_num = 0, page_size = 5) => backend.get_transfers(page_num, page_size), 
      dataPath: 'TransfersList.transfers',
      paginationPath: 'TransfersList.pagination'
    },
    { name: 'instruments', fetch: () => backend.get_instruments(), dataPath: 'InstrumentsList.instruments' },
    { name: 'codexes', fetch: () => backend.get_codexes(), dataPath: 'CodexesList.codexes' },
    { name: 'organizations', fetch: () => backend.get_organizations(), dataPath: 'OrganizationsList.organizations' },
    { name: 'disputes', fetch: () => backend.get_disputes(), dataPath: 'DisputesList.disputes' },
    { name: 'licenses', fetch: () => backend.get_licenses(), dataPath: 'LicensesList.licenses' },
    { name: 'trades', fetch: () => backend.get_trades(), dataPath: 'TradesList.trades' },
    { name: 'realms', fetch: () => backend.get_realms(), dataPath: 'RealmsList.realms' },
    { name: 'proposals', fetch: () => backend.get_proposals(), dataPath: 'ProposalsList.proposals' },
    { name: 'votes', fetch: () => backend.get_votes(), dataPath: 'VotesList.votes' }
  ];
  
  // Function to fetch data for a specific entity type
  async function fetchEntityData(entityType) {
    try {
      loading = true;
      error = null;
      
      const config = entityConfigs.find(c => c.name === entityType);
      if (!config) {
        error = `No configuration found for entity type: ${entityType}`;
        loading = false;
        return;
      }
      
      console.log(`Fetching data for ${entityType}...`);
      
      // Handle special case for transfers with pagination
      let result;
      if (entityType === 'transfers') {
        result = await config.fetch(transfersPage, transfersPerPage);
      } else {
        result = await config.fetch();
      }
      
      if (result && result.success && result.data) {
        // Navigate to the data using the dataPath
        const pathParts = config.dataPath.split('.');
        let entityData = result.data;
        
        for (const part of pathParts) {
          if (entityData && entityData[part]) {
            entityData = entityData[part];
          } else {
            entityData = null;
            break;
          }
        }
        
        if (entityData && Array.isArray(entityData) && entityData.length > 0) {
          // Parse JSON strings if needed
          const parsedData = entityData.map(item => {
            if (typeof item === 'string') {
              try {
                return JSON.parse(item);
              } catch (e) {
                return item;
              }
            }
            return item;
          });
          
          // Update only this specific entity type in the data object
          data = {...data, [entityType]: parsedData};
          console.log(`✅ ${entityType}: ${parsedData.length} items`);
          
          // Get pagination info for transfers
          if (entityType === 'transfers' && config.paginationPath) {
            const paginationParts = config.paginationPath.split('.');
            let paginationData = result.data;
            
            for (const part of paginationParts) {
              if (paginationData && paginationData[part]) {
                paginationData = paginationData[part];
              } else {
                paginationData = null;
                break;
              }
            }
            
            if (paginationData) {
              transfersPagination = paginationData;
              console.log(`✅ Transfers pagination:`, transfersPagination);
            }
          }
        } else {
          console.log(`⚠️ ${entityType}: No valid data found`);
          // Initialize with empty array to prevent undefined errors
          data = {...data, [entityType]: []};
        }
      } else {
        console.log(`❌ ${entityType}: ${result?.error || 'Failed to fetch'}`);
        data = {...data, [entityType]: []};
      }
      
    } catch (err) {
      console.error(`Error fetching ${entityType} data:`, err);
      error = `Data fetch error for ${entityType}: ${err.message}`;
    } finally {
      loading = false;
    }
  }
  
  async function fetchAllData() {
    try {
      loading = true;
      error = null;
      data = {};
      
      console.log("Fetching all GGG data in parallel...");
      
      // Prepare all fetch promises
      const fetchPromises = entityConfigs.map(config => {
        // Handle special case for transfers with pagination
        if (config.name === 'transfers') {
          return config.fetch(transfersPage, transfersPerPage);
        } else {
          return config.fetch();
        }
      });
      
      // Execute all API calls in parallel
      const results = await Promise.all(fetchPromises);
      
      // Process the results in the same order as the configs
      for (let i = 0; i < results.length; i++) {
        const config = entityConfigs[i];
        const result = results[i];
        
        if (result && result.success && result.data) {
          // Navigate to the data using the dataPath
          const pathParts = config.dataPath.split('.');
          let entityData = result.data;
          
          for (const part of pathParts) {
            if (entityData && entityData[part]) {
              entityData = entityData[part];
            } else {
              entityData = null;
              break;
            }
          }
          
          if (entityData && Array.isArray(entityData) && entityData.length > 0) {
            // Parse JSON strings if needed
            const parsedData = entityData.map(item => {
              if (typeof item === 'string') {
                try {
                  return JSON.parse(item);
                } catch (e) {
                  return item;
                }
              }
              return item;
            });
            
            data[config.name] = parsedData;
            console.log(`✅ ${config.name}: ${parsedData.length} items`);
            
            // Get pagination info for transfers
            if (config.name === 'transfers' && config.paginationPath) {
              const paginationParts = config.paginationPath.split('.');
              let paginationData = result.data;
              
              for (const part of paginationParts) {
                if (paginationData && paginationData[part]) {
                  paginationData = paginationData[part];
                } else {
                  paginationData = null;
                  break;
                }
              }
              
              if (paginationData) {
                transfersPagination = paginationData;
                console.log(`✅ Transfers pagination:`, transfersPagination);
              }
            }
          } else {
            console.log(`⚠️ ${config.name}: No valid data found`);
          }
        } else {
          console.log(`❌ ${config.name}: ${result?.error || 'Failed to fetch'}`);
        }
      }
      
      console.log("Data loaded:", Object.keys(data));
      
      // Only calculate metrics and relationships if we have data
      if (Object.keys(data).length > 0) {
        calculateMetrics();
        findRelationships();
        getRecentActivity();
      } else {
        console.log("No data loaded, skipping calculations");
      }
      
    } catch (err) {
      console.error("Error fetching data:", err);
      error = `Data fetch error: ${err.message}`;
    } finally {
      loading = false;
    }
  }
  
  // Function to handle tab changes
  async function handleTabChange(tabName) {
    activeTab = tabName;
    
    // For overview tab, load only essential data needed for the dashboard
    if (tabName === 'overview') {
      loading = true;
      error = null;
      
      console.log("Loading essential data for Overview dashboard...");
      
      // Identify which entities are needed for the overview
      const essentialEntities = ['realms', 'mandates', 'instruments', 'transfers'];
      
      // Load only these essential entities in sequence
      try {
        for (const entityType of essentialEntities) {
          await fetchEntityData(entityType);
        }
        
        // Calculate metrics and relationships only with the available data
        calculateMetrics();
        findRelationships();
        getRecentActivity();
        
      } catch (err) {
        console.error("Error loading essential data for Overview:", err);
        error = `Error loading Overview data: ${err.message}`;
      } finally {
        loading = false;
      }
    } 
    // For entity-specific tabs, just load the data for that entity
    else if (allEntityTypes.includes(tabName)) {
      await fetchEntityData(tabName);
    }
  }
  
  function filterData(data, searchTerm) {
    if (!searchTerm) return data;
    
    const filtered = {};
    Object.entries(data).forEach(([entityType, entities]) => {
      if (Array.isArray(entities)) {
        filtered[entityType] = entities.filter(entity =>
          Object.values(entity).some(value =>
            String(value).toLowerCase().includes(searchTerm.toLowerCase())
          )
        );
      } else {
        filtered[entityType] = entities;
      }
    });
    return filtered;
  }
  
  $: filteredData = filterData(data, searchTerm);
  
  onMount(() => {
  // On initial load, only fetch for the active tab
    if (activeTab === 'overview') {
      handleTabChange('overview');
    } else if (allEntityTypes.includes(activeTab)) {
      fetchEntityData(activeTab);
    }
  });
</script>

<div class="container mx-auto p-4">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
      <p class="text-gray-600 mt-1">Generalized Global Governance System</p>
    </div>
  </div>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-4" role="alert">
      <div class="flex items-center">
        <span class="mr-2">⚠️</span>
      <p>{error}</p>
      </div>
    </div>
  {/if}
  
  <!-- Universal Search -->
  <div class="mb-6">
    <div class="relative">
      <input 
        type="text" 
        placeholder="Search across all entities..." 
        class="w-full border border-gray-300 rounded-lg px-4 py-3 pl-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        bind:value={searchTerm}
      >
      <span class="absolute left-3 top-3 text-gray-400">🔍</span>
    </div>
  </div>
  
  <!-- Navigation Tabs -->
  <div class="mb-6 border-b border-gray-200">
    <div class="flex flex-wrap">
      <button 
        class="px-4 py-2 mr-1 {activeTab === 'overview' ? 'border-b-2 border-blue-500 font-medium text-blue-600' : 'text-gray-600 hover:text-gray-900'}"
        on:click={() => handleTabChange('overview')}
      >
        📊 Overview
      </button>
      {#each allEntityTypes as entityType}
      <button 
          class="px-4 py-2 mr-1 {activeTab === entityType ? 'border-b-2 border-blue-500 font-medium text-blue-600' : 'text-gray-600 hover:text-gray-900'}"
          on:click={() => handleTabChange(entityType)}
      >
          {entityType.charAt(0).toUpperCase() + entityType.slice(1)}
      </button>
      {/each}
    </div>
  </div>
  
  <!-- Content Area -->
  <div class="bg-white shadow-sm rounded-lg">
    {#if activeTab === 'overview'}
      <!-- Metrics Dashboard -->
      <div class="p-6">
        <!-- Realm Header -->
        {#if data.realms && data.realms.length > 0}
          <div class="mb-8 text-center">
            <h1 class="text-4xl font-bold text-gray-900 mb-2">
              🏛️ {data.realms[0].name || 'Nova Republic'}
            </h1>
            <p class="text-lg text-gray-600 max-w-2xl mx-auto">
              {JSON.parse(data.realms[0].description || '{}').description || data.realms[0].description || 'A progressive digital sovereign realm pioneering governance of digital assets, identity, and social contracts'}
            </p>
          </div>
        {:else}
          <h2 class="text-2xl font-bold mb-6">System Overview</h2>
        {/if}
        
        <!-- Treasury Budget Chart -->
        {#if data.instruments && data.transfers}
          <div class="mb-8 bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-200">
            <h3 class="text-xl font-bold text-gray-900 mb-4 flex items-center">
              🏦 <span class="ml-2">Treasury Portfolio</span>
            </h3>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Asset Holdings -->
              <div>
                <h4 class="font-semibold text-gray-700 mb-3">Asset Holdings</h4>
                <div class="space-y-3">
                  {#each data.instruments as instrument}
                    {@const metadata = JSON.parse(instrument.metadata || '{}')}
                    {@const balance = metadata.treasury_balance || 0}
                    {@const symbol = metadata.symbol || instrument._id}
                    {@const decimals = metadata.decimal_places || 0}
                    {#if balance > 0}
                      <div class="flex items-center justify-between bg-white rounded-lg p-3 border">
                        <div class="flex items-center">
                          <div class="w-3 h-3 rounded-full mr-3" 
                               style="background-color: {symbol === 'NVC' ? '#3B82F6' : symbol === 'ckBTC' ? '#F59E0B' : '#10B981'}"></div>
                          <div>
                            <p class="font-medium">{symbol}</p>
                            <p class="text-xs text-gray-500">{metadata.description || metadata.type}</p>
                          </div>
                        </div>
                        <div class="text-right">
                          {#if symbol === 'ckBTC' && decimals === 8}
                            <p class="font-bold">{(balance / 100000000).toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 4})}</p>
                            <p class="text-xs text-gray-500">≈ {((balance / 100000000) * 45000).toLocaleString()} NVC</p>
                          {:else}
                            <p class="font-bold">{balance.toLocaleString()}</p>
                            {#if symbol === 'ckBTC'}
                              <p class="text-xs text-gray-500">≈ {(balance * 45000).toLocaleString()} NVC</p>
                            {/if}
                          {/if}
                        </div>
                      </div>
                    {/if}
                  {/each}
                </div>
              </div>
              
              <!-- Cash Flow Summary -->
              <div>
                <h4 class="font-semibold text-gray-700 mb-3">Monthly Cash Flow</h4>
                <div class="space-y-3">
                  <!-- Income -->
                  <div class="bg-white rounded-lg p-3 border">
                    <div class="flex items-center justify-between mb-2">
                      <span class="text-sm font-medium text-green-700">📈 Income</span>
                      <span class="text-lg font-bold text-green-600">+{(3450 + 350 + 180 + 750).toLocaleString()} NVC</span>
                    </div>
                    <div class="text-xs text-gray-600 space-y-1">
                      <div class="flex justify-between"><span>Tax Revenue</span><span>3,450 NVC</span></div>
                      <div class="flex justify-between"><span>License Fees</span><span>350 NVC</span></div>
                      <div class="flex justify-between"><span>Healthcare Contributions</span><span>180 NVC</span></div>
                      <div class="flex justify-between"><span>Housing Payments</span><span>750 NVC</span></div>
                    </div>
                  </div>
                  
                  <!-- Expenses -->
                  <div class="bg-white rounded-lg p-3 border">
                    <div class="flex items-center justify-between mb-2">
                      <span class="text-sm font-medium text-red-700">📉 Expenses</span>
                      <span class="text-lg font-bold text-red-600">-{(1200 + 5000 + 125).toLocaleString()} NVC</span>
                    </div>
                    <div class="text-xs text-gray-600 space-y-1">
                      <div class="flex justify-between"><span>UBI Payments</span><span>1,200 NVC</span></div>
                      <div class="flex justify-between"><span>Innovation Grants</span><span>5,000 NVC</span></div>
                      <div class="flex justify-between"><span>Tax Refunds</span><span>125 NVC</span></div>
                    </div>
                  </div>
                  
                  <!-- Net Flow -->
                  <div class="bg-blue-50 rounded-lg p-3 border border-blue-200">
                    <div class="flex items-center justify-between">
                      <span class="text-sm font-medium text-blue-700">💰 Net Monthly Flow</span>
                      <span class="text-lg font-bold text-blue-600">+{((3450 + 350 + 180 + 750) - (1200 + 5000 + 125)).toLocaleString()} NVC</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        {/if}
        
        <!-- Metrics Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <div class="bg-gradient-to-r from-blue-50 to-blue-100 p-6 rounded-lg border border-blue-200">
            <h3 class="text-lg font-semibold text-blue-800">Total Entities</h3>
            <p class="text-3xl font-bold text-blue-600">{metrics.totalEntities || 0}</p>
            <p class="text-sm text-blue-600 mt-1">Across all types</p>
          </div>
          
          <div class="bg-gradient-to-r from-green-50 to-green-100 p-6 rounded-lg border border-green-200">
            <h3 class="text-lg font-semibold text-green-800">Transfer Volume</h3>
            <p class="text-3xl font-bold text-green-600">{metrics.totalTransferVolume?.toLocaleString() || 0}</p>
            <p class="text-sm text-green-600 mt-1">{metrics.totalTransfers || 0} transfers</p>
          </div>
          
          <div class="bg-gradient-to-r from-purple-50 to-purple-100 p-6 rounded-lg border border-purple-200">
            <h3 class="text-lg font-semibold text-purple-800">Active Mandates</h3>
            <p class="text-3xl font-bold text-purple-600">{metrics.activeMandates || 0}</p>
            <p class="text-sm text-purple-600 mt-1">Governance policies</p>
          </div>
          
          {#if metrics.scheduledTasks > 0}
            <div class="bg-gradient-to-r from-orange-50 to-orange-100 p-6 rounded-lg border border-orange-200">
              <h3 class="text-lg font-semibold text-orange-800">Scheduled Tasks</h3>
              <p class="text-3xl font-bold text-orange-600">{metrics.scheduledTasks}</p>
              <p class="text-sm text-orange-600 mt-1">Automated processes</p>
            </div>
          {/if}
          
          {#if metrics.openDisputes > 0}
            <div class="bg-gradient-to-r from-red-50 to-red-100 p-6 rounded-lg border border-red-200">
              <h3 class="text-lg font-semibold text-red-800">Open Disputes</h3>
              <p class="text-3xl font-bold text-red-600">{metrics.openDisputes}</p>
              <p class="text-sm text-red-600 mt-1">Requiring attention</p>
            </div>
          {/if}
          
          {#if metrics.activeProposals > 0}
            <div class="bg-gradient-to-r from-indigo-50 to-indigo-100 p-6 rounded-lg border border-indigo-200">
              <h3 class="text-lg font-semibold text-indigo-800">Active Proposals</h3>
              <p class="text-3xl font-bold text-indigo-600">{metrics.activeProposals}</p>
              <p class="text-sm text-indigo-600 mt-1">Open for voting</p>
            </div>
          {/if}
          
          {#if metrics.totalVotes > 0}
            <div class="bg-gradient-to-r from-teal-50 to-teal-100 p-6 rounded-lg border border-teal-200">
              <h3 class="text-lg font-semibold text-teal-800">Citizen Votes</h3>
              <p class="text-3xl font-bold text-teal-600">{metrics.totalVotes}</p>
              <p class="text-sm text-teal-600 mt-1">Democratic participation</p>
            </div>
          {/if}
        </div>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Relationships -->
          {#if relationships.length > 0}
            <div class="bg-gray-50 rounded-lg p-6">
              <h3 class="text-lg font-bold mb-4">Entity Relationships</h3>
              <div class="space-y-3">
                {#each relationships as relationship}
                  <div class="flex items-center justify-between p-3 bg-white rounded border">
                    <div class="flex-1">
                      <p class="font-medium text-sm">{relationship.label}</p>
                      <p class="text-xs text-gray-600 capitalize">{relationship.type.replace('-', ' → ')}</p>
                    </div>
                    <button class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                      Explore
                    </button>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
          
          <!-- Recent Activity -->
          {#if recentActivity.length > 0}
            <div class="bg-gray-50 rounded-lg p-6">
              <h3 class="text-lg font-bold mb-4">Recent Activity</h3>
              <div class="space-y-3">
                {#each recentActivity as activity}
                  <div class="flex items-start p-3 bg-white rounded border">
                    <div class="flex-1">
                      <p class="font-medium text-sm">{activity.description}</p>
                      <div class="flex items-center mt-1">
                        <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded mr-2">
                          {activity.type}
                        </span>
                        <p class="text-xs text-gray-600">{new Date(activity.timestamp).toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
        
        {#if Object.keys(data).length === 0 && !loading}
          <div class="text-center py-12">
            <span class="text-6xl block mb-4">🏛️</span>
            <h3 class="text-xl font-semibold text-gray-700 mb-2">No GGG Data Found</h3>
            <p class="text-gray-600 mb-4">Click "Load Demo Data" to populate the system with sample governance data</p>
          </div>
        {/if}
      </div>
    {:else}
      <!-- Entity Table View -->
      <div class="p-6">
        {#if activeTab === 'codexes'}
          <CodexViewer 
            codexes={filteredData[activeTab] || data[activeTab] || []} 
            {loading} 
          />
        {:else}
          {#if activeTab === 'transfers'}
            <GenericEntityTable 
              entityType="transfers"
              items={data.transfers || []}
              loading={loading}
              pagination={transfersPagination}
              onPageChange={handleTransfersPageChange}
            />
          {:else}
            <GenericEntityTable 
              entityType={activeTab}
              items={filteredData[activeTab] || data[activeTab] || []}
              loading={loading}
            />
          {/if}
        {/if}
      </div>
    {/if}
  </div>
</div> 