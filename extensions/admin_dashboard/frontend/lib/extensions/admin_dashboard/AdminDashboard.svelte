<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  import { _ } from 'svelte-i18n';
  
  import GenericEntityTable from '$lib/components/ggg/GenericEntityTable.svelte';
  import CodexViewer from '$lib/components/ggg/CodexViewer.svelte';
  import MetricsComponent from '$lib/extensions/metrics/Metrics.svelte';
  import RegistrationUrlManager from './RegistrationUrlManager.svelte';
  
  let activeTab = 'overview';
  let loading = false;
  let error = null;
  let data = {};
  let metrics = {};
  let relationships = [];
  let recentActivity = [];
  let searchTerm = '';
  
  // Bulk import state
  let selectedEntityType = 'users';
  let selectedFormat = 'csv';
  let importData = '';
  let importResults = null;
  let importLoading = false;
  let templates = {};
  
  // Pagination state for all entities
  let usersPage = 0, usersPerPage = 5, usersPagination = null;
  let mandatesPage = 0, mandatesPerPage = 5, mandatesPagination = null;
  let tasksPage = 0, tasksPerPage = 5, tasksPagination = null;
  let transfersPage = 0, transfersPerPage = 5, transfersPagination = null;
  let instrumentsPage = 0, instrumentsPerPage = 5, instrumentsPagination = null;
  let codexesPage = 0, codexesPerPage = 5, codexesPagination = null;
  let organizationsPage = 0, organizationsPerPage = 5, organizationsPagination = null;
  let disputesPage = 0, disputesPerPage = 5, disputesPagination = null;
  let licensesPage = 0, licensesPerPage = 5, licensesPagination = null;
  let tradesPage = 0, tradesPerPage = 5, tradesPagination = null;
  let realmsPage = 0, realmsPerPage = 5, realmsPagination = null;
  let proposalsPage = 0, proposalsPerPage = 5, proposalsPagination = null;
  let votesPage = 0, votesPerPage = 5, votesPagination = null;
  
  // Pagination handlers
  async function handleUsersPageChange(page) { usersPage = page; await fetchEntityData('users'); }
  async function handleMandatesPageChange(page) { mandatesPage = page; await fetchEntityData('mandates'); }
  async function handleTasksPageChange(page) { tasksPage = page; await fetchEntityData('tasks'); }
  async function handleTransfersPageChange(page) { transfersPage = page; await fetchEntityData('transfers'); }
  async function handleInstrumentsPageChange(page) { instrumentsPage = page; await fetchEntityData('instruments'); }
  async function handleCodexesPageChange(page) { codexesPage = page; await fetchEntityData('codexes'); }
  async function handleOrganizationsPageChange(page) { organizationsPage = page; await fetchEntityData('organizations'); }
  async function handleDisputesPageChange(page) { disputesPage = page; await fetchEntityData('disputes'); }
  async function handleLicensesPageChange(page) { licensesPage = page; await fetchEntityData('licenses'); }
  async function handleTradesPageChange(page) { tradesPage = page; await fetchEntityData('trades'); }
  async function handleRealmsPageChange(page) { realmsPage = page; await fetchEntityData('realms'); }
  async function handleProposalsPageChange(page) { proposalsPage = page; await fetchEntityData('proposals'); }
  async function handleVotesPageChange(page) { votesPage = page; await fetchEntityData('votes'); }
  
  // Static list of all known GGG entity types
  const allEntityTypes = [
    'users', 'mandates', 'tasks', 'transfers', 'instruments', 'codexes',
    'organizations', 'disputes', 'licenses', 'trades', 'realms', 'proposals', 'votes'
  ];
  
  // Entity type configurations with their API endpoints
  const entityConfigs = [
    { name: 'users', fetch: (page_num = 0, page_size = 5) => backend.get_users(page_num, page_size), dataPath: 'UsersList.users', paginationPath: 'UsersList.pagination', page: () => usersPage, perPage: () => usersPerPage, pagination: () => usersPagination, onPageChange: handleUsersPageChange },
    { name: 'mandates', fetch: (page_num = 0, page_size = 5) => backend.get_mandates(page_num, page_size), dataPath: 'MandatesList.mandates', paginationPath: 'MandatesList.pagination', page: () => mandatesPage, perPage: () => mandatesPerPage, pagination: () => mandatesPagination, onPageChange: handleMandatesPageChange },
    { name: 'tasks', fetch: (page_num = 0, page_size = 5) => backend.get_tasks(page_num, page_size), dataPath: 'TasksList.tasks', paginationPath: 'TasksList.pagination', page: () => tasksPage, perPage: () => tasksPerPage, pagination: () => tasksPagination, onPageChange: handleTasksPageChange },
    { name: 'transfers', fetch: (page_num = 0, page_size = 5) => backend.get_transfers(page_num, page_size), dataPath: 'TransfersList.transfers', paginationPath: 'TransfersList.pagination', page: () => transfersPage, perPage: () => transfersPerPage, pagination: () => transfersPagination, onPageChange: handleTransfersPageChange },
    { name: 'instruments', fetch: (page_num = 0, page_size = 5) => backend.get_instruments(page_num, page_size), dataPath: 'InstrumentsList.instruments', paginationPath: 'InstrumentsList.pagination', page: () => instrumentsPage, perPage: () => instrumentsPerPage, pagination: () => instrumentsPagination, onPageChange: handleInstrumentsPageChange },
    { name: 'codexes', fetch: (page_num = 0, page_size = 5) => backend.get_codexes(page_num, page_size), dataPath: 'CodexesList.codexes', paginationPath: 'CodexesList.pagination', page: () => codexesPage, perPage: () => codexesPerPage, pagination: () => codexesPagination, onPageChange: handleCodexesPageChange },
    { name: 'organizations', fetch: (page_num = 0, page_size = 5) => backend.get_organizations(page_num, page_size), dataPath: 'OrganizationsList.organizations', paginationPath: 'OrganizationsList.pagination', page: () => organizationsPage, perPage: () => organizationsPerPage, pagination: () => organizationsPagination, onPageChange: handleOrganizationsPageChange },
    { name: 'disputes', fetch: (page_num = 0, page_size = 5) => backend.get_disputes(page_num, page_size), dataPath: 'DisputesList.disputes', paginationPath: 'DisputesList.pagination', page: () => disputesPage, perPage: () => disputesPerPage, pagination: () => disputesPagination, onPageChange: handleDisputesPageChange },
    { name: 'licenses', fetch: (page_num = 0, page_size = 5) => backend.get_licenses(page_num, page_size), dataPath: 'LicensesList.licenses', paginationPath: 'LicensesList.pagination', page: () => licensesPage, perPage: () => licensesPerPage, pagination: () => licensesPagination, onPageChange: handleLicensesPageChange },
    { name: 'trades', fetch: (page_num = 0, page_size = 5) => backend.get_trades(page_num, page_size), dataPath: 'TradesList.trades', paginationPath: 'TradesList.pagination', page: () => tradesPage, perPage: () => tradesPerPage, pagination: () => tradesPagination, onPageChange: handleTradesPageChange },
    { name: 'realms', fetch: (page_num = 0, page_size = 5) => backend.get_realms(page_num, page_size), dataPath: 'RealmsList.realms', paginationPath: 'RealmsList.pagination', page: () => realmsPage, perPage: () => realmsPerPage, pagination: () => realmsPagination, onPageChange: handleRealmsPageChange },
    { name: 'proposals', fetch: (page_num = 0, page_size = 5) => backend.get_proposals(page_num, page_size), dataPath: 'ProposalsList.proposals', paginationPath: 'ProposalsList.pagination', page: () => proposalsPage, perPage: () => proposalsPerPage, pagination: () => proposalsPagination, onPageChange: handleProposalsPageChange },
    { name: 'votes', fetch: (page_num = 0, page_size = 5) => backend.get_votes(page_num, page_size), dataPath: 'VotesList.votes', paginationPath: 'VotesList.pagination', page: () => votesPage, perPage: () => votesPerPage, pagination: () => votesPagination, onPageChange: handleVotesPageChange }
  ];
  
  // Function to fetch data for a specific entity type
  async function fetchEntityData(entityType) {
    console.log('🔧 AdminDashboard: fetchEntityData called for:', entityType);
    
    try {
      loading = true;
      error = null;
      
      const config = entityConfigs.find(c => c.name === entityType);
      console.log('🔧 AdminDashboard: Found config for', entityType, ':', config);
      
      if (!config) {
        console.log('🔧 AdminDashboard: No config found for entityType:', entityType);
        error = `No configuration found for entity type: ${entityType}`;
        loading = false;
        return;
      }
      
      console.log('🔧 AdminDashboard: Calling config.fetch with page:', config.page(), 'perPage:', config.perPage());
      let result = await config.fetch(config.page(), config.perPage());
      console.log('🔧 AdminDashboard: Fetch result:', result);
      console.log('🔧 AdminDashboard: Result type:', typeof result);
      console.log('🔧 AdminDashboard: Result keys:', result ? Object.keys(result) : 'null');
      
      // Handle both success/data format and direct data format
      let actualData = null;
      if (result && result.success && result.data) {
        actualData = result.data;
        console.log('🔧 AdminDashboard: Using result.data format');
      } else if (result && typeof result === 'object') {
        actualData = result;
        console.log('🔧 AdminDashboard: Using direct result format');
      }
      
      if (actualData) {
        const pathParts = config.dataPath.split('.');
        let entityData = actualData;
        
        console.log('🔧 AdminDashboard: Data path:', config.dataPath);
        console.log('🔧 AdminDashboard: Path parts:', pathParts);
        console.log('🔧 AdminDashboard: Starting with actualData:', actualData);
        
        for (const part of pathParts) {
          console.log('🔧 AdminDashboard: Processing path part:', part);
          console.log('🔧 AdminDashboard: Current entityData:', entityData);
          
          if (entityData && entityData[part] !== undefined) {
            entityData = entityData[part];
            console.log('🔧 AdminDashboard: Found part, new entityData:', entityData);
          } else {
            console.log('🔧 AdminDashboard: Part not found, setting to null');
            entityData = null;
            break;
          }
        }
        
        console.log('🔧 AdminDashboard: Final entityData:', entityData);
        
        if (entityData && Array.isArray(entityData) && entityData.length > 0) {
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
          
          console.log('🔧 AdminDashboard: Parsed data for', entityType, ':', parsedData);
          console.log('🔧 AdminDashboard: Sample parsed item:', parsedData[0]);
          
          data = {...data, [entityType]: parsedData};
          
          if (config.paginationPath) {
            const paginationParts = config.paginationPath.split('.');
            let paginationData = actualData;
            
            for (const part of paginationParts) {
              if (paginationData && paginationData[part]) {
                paginationData = paginationData[part];
              } else {
                paginationData = null;
                break;
              }
            }
            
            if (paginationData) {
              if (entityType === 'users') usersPagination = paginationData;
              else if (entityType === 'mandates') mandatesPagination = paginationData;
              else if (entityType === 'tasks') tasksPagination = paginationData;
              else if (entityType === 'transfers') transfersPagination = paginationData;
              else if (entityType === 'instruments') instrumentsPagination = paginationData;
              else if (entityType === 'codexes') codexesPagination = paginationData;
              else if (entityType === 'organizations') organizationsPagination = paginationData;
              else if (entityType === 'disputes') disputesPagination = paginationData;
              else if (entityType === 'licenses') licensesPagination = paginationData;
              else if (entityType === 'trades') tradesPagination = paginationData;
              else if (entityType === 'realms') realmsPagination = paginationData;
              else if (entityType === 'proposals') proposalsPagination = paginationData;
              else if (entityType === 'votes') votesPagination = paginationData;
            }
          }
        } else {
          data = {...data, [entityType]: []};
        }
      } else {
        data = {...data, [entityType]: []};
      }
      
    } catch (err) {
      console.error(`Error fetching ${entityType}:`, err);
      error = `Error fetching ${entityType}: ${err.message}`;
    } finally {
      loading = false;
    }
  }
  
  // Function to handle tab changes
  async function handleTabChange(tabName) {
    activeTab = tabName;
    
    if (tabName === 'overview') {
      loading = true;
      error = null;
      
      const essentialEntities = ['realms', 'mandates', 'instruments', 'transfers'];
      
      try {
        for (const entityType of essentialEntities) {
          await fetchEntityData(entityType);
        }
        
        calculateMetrics();
        
      } catch (err) {
        console.error("Error loading essential data for Overview:", err);
        error = `Error loading Overview data: ${err.message}`;
      } finally {
        loading = false;
      }
    } 
    else if (allEntityTypes.includes(tabName)) {
      await fetchEntityData(tabName);
    }
  }
  
  function calculateMetrics() {
    metrics = {
      totalEntities: Object.values(data).reduce((sum, entities) => sum + (Array.isArray(entities) ? entities.length : 0), 0),
      totalTransfers: data.transfers ? data.transfers.length : 0,
      totalTransferVolume: data.transfers ? data.transfers.reduce((sum, t) => sum + (parseFloat(t.amount) || 0), 0) : 0,
      activeMandates: data.mandates ? data.mandates.filter(m => m.status === 'active').length : 0,
      scheduledTasks: data.tasks ? data.tasks.filter(t => t.status === 'scheduled').length : 0,
      openDisputes: data.disputes ? data.disputes.filter(d => d.status === 'open').length : 0,
      activeProposals: data.proposals ? data.proposals.filter(p => p.status === 'active').length : 0,
      totalVotes: data.votes ? data.votes.length : 0
    };
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
  
  async function importBulkData() {
    if (!importData.trim()) {
      error = 'Please provide data to import';
      return;
    }
    
    importLoading = true;
    importResults = null;
    error = null;
    
    try {
      const result = await backend.extension_sync_call('admin_dashboard', 'import_data', {
        entity_type: selectedEntityType,
        format: selectedFormat,
        data: importData
      });
      
      if (result.success) {
        importResults = result.data;
        // Refresh the relevant entity data if we're on that tab
        if (allEntityTypes.includes(activeTab) && activeTab === selectedEntityType) {
          await fetchEntityData(activeTab);
        }
      } else {
        error = `Import error: ${result.error}`;
      }
    } catch (err) {
      console.error('Error importing data:', err);
      error = `Import error: ${err.message}`;
    } finally {
      importLoading = false;
    }
  }
  
  function clearImportData() {
    importData = '';
    importResults = null;
    error = null;
  }
  
  onMount(() => {
    console.log('🔧 AdminDashboard: Component mounted, activeTab:', activeTab);
    if (activeTab === 'overview') {
      console.log('🔧 AdminDashboard: Calling handleTabChange for overview');
      handleTabChange('overview');
    } else if (allEntityTypes.includes(activeTab)) {
      console.log('🔧 AdminDashboard: Calling fetchEntityData for:', activeTab);
      fetchEntityData(activeTab);
    } else {
      console.log('🔧 AdminDashboard: No initial data fetch needed');
    }
  });
</script>

<div class="w-full px-4 max-w-none">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">{$_('extensions.admin_dashboard.title') || 'Admin Dashboard'}</h1>
      <p class="text-gray-600 mt-1">{$_('extensions.admin_dashboard.subtitle') || 'Generalized Global Governance System'}</p>
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
        placeholder="{$_('extensions.admin_dashboard.search_placeholder') || 'Search across all entities...'}"
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
        📊 {$_('extensions.admin_dashboard.overview') || 'Overview'}
      </button>
      <button 
        class="px-4 py-2 mr-1 {activeTab === 'bulk_import' ? 'border-b-2 border-blue-500 font-medium text-blue-600' : 'text-gray-600 hover:text-gray-900'}"
        on:click={() => handleTabChange('bulk_import')}
      >
        📥 {$_('extensions.admin_dashboard.bulk_import') || 'Bulk Import'}
      </button>
      <button 
        class="px-4 py-2 mr-1 {activeTab === 'registration_urls' ? 'border-b-2 border-blue-500 font-medium text-blue-600' : 'text-gray-600 hover:text-gray-900'}"
        on:click={() => handleTabChange('registration_urls')}
      >
        🔗 {$_('extensions.admin_dashboard.registration_urls') || 'Registration URLs'}
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
      <!-- Overview Dashboard -->
      <div class="p-6">
        {#if data.realms && data.realms.length > 0}
          <div class="mb-8 text-center">
            <h1 class="text-4xl font-bold text-gray-900 mb-2">
              🏛️ {data.realms[0].name || 'Nova Republic'}
            </h1>
            <p class="text-lg text-gray-600 max-w-2xl mx-auto">
              {(() => {
                try {
                  const parsed = JSON.parse(data.realms[0].description || '{}');
                  return parsed.description || data.realms[0].description || 'A progressive digital sovereign realm pioneering governance of digital assets, identity, and social contracts';
                } catch (e) {
                  return data.realms[0].description || 'A progressive digital sovereign realm pioneering governance of digital assets, identity, and social contracts';
                }
              })()}
            </p>
          </div>
        {:else}
          <h2 class="text-2xl font-bold mb-6">{$_('extensions.admin_dashboard.system_overview') || 'System Overview'}</h2>
        {/if}
        
        <!-- Treasury Budget Metrics -->
        <div class="mb-8 bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-200">
          <h3 class="text-xl font-bold text-gray-900 mb-4 flex items-center">
            🏦 <span class="ml-2">{$_('extensions.admin_dashboard.treasury_portfolio') || 'Treasury Portfolio'}</span>
          </h3>
          
          <MetricsComponent />
        </div>
        
        <!-- Metrics Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-8">
          <div class="bg-gradient-to-r from-blue-50 to-blue-100 p-6 rounded-lg border border-blue-200">
            <h3 class="text-lg font-semibold text-blue-800">{$_('extensions.admin_dashboard.total_entities') || 'Total Entities'}</h3>
            <p class="text-3xl font-bold text-blue-600">{metrics.totalEntities || 0}</p>
            <p class="text-sm text-blue-600 mt-1">{$_('extensions.admin_dashboard.across_all_types') || 'Across all types'}</p>
          </div>
          
          <div class="bg-gradient-to-r from-green-50 to-green-100 p-6 rounded-lg border border-green-200">
            <h3 class="text-lg font-semibold text-green-800">{$_('extensions.admin_dashboard.transfer_volume') || 'Transfer Volume'}</h3>
            <p class="text-3xl font-bold text-green-600">{metrics.totalTransferVolume?.toLocaleString() || 0}</p>
            <p class="text-sm text-green-600 mt-1">{metrics.totalTransfers || 0} {$_('extensions.admin_dashboard.transfers') || 'transfers'}</p>
          </div>
          
          <div class="bg-gradient-to-r from-purple-50 to-purple-100 p-6 rounded-lg border border-purple-200">
            <h3 class="text-lg font-semibold text-purple-800">{$_('extensions.admin_dashboard.active_mandates') || 'Active Mandates'}</h3>
            <p class="text-3xl font-bold text-purple-600">{metrics.activeMandates || 0}</p>
            <p class="text-sm text-purple-600 mt-1">{$_('extensions.admin_dashboard.governance_policies') || 'Governance policies'}</p>
          </div>
          
          {#if metrics.scheduledTasks > 0}
            <div class="bg-gradient-to-r from-orange-50 to-orange-100 p-6 rounded-lg border border-orange-200">
              <h3 class="text-lg font-semibold text-orange-800">{$_('extensions.admin_dashboard.scheduled_tasks') || 'Scheduled Tasks'}</h3>
              <p class="text-3xl font-bold text-orange-600">{metrics.scheduledTasks}</p>
              <p class="text-sm text-orange-600 mt-1">{$_('extensions.admin_dashboard.automated_processes') || 'Automated processes'}</p>
            </div>
          {/if}
          
          {#if metrics.openDisputes > 0}
            <div class="bg-gradient-to-r from-red-50 to-red-100 p-6 rounded-lg border border-red-200">
              <h3 class="text-lg font-semibold text-red-800">{$_('extensions.admin_dashboard.open_disputes') || 'Open Disputes'}</h3>
              <p class="text-3xl font-bold text-red-600">{metrics.openDisputes}</p>
              <p class="text-sm text-red-600 mt-1">{$_('extensions.admin_dashboard.requiring_attention') || 'Requiring attention'}</p>
            </div>
          {/if}
          
          {#if metrics.activeProposals > 0}
            <div class="bg-gradient-to-r from-indigo-50 to-indigo-100 p-6 rounded-lg border border-indigo-200">
              <h3 class="text-lg font-semibold text-indigo-800">{$_('extensions.admin_dashboard.active_proposals') || 'Active Proposals'}</h3>
              <p class="text-3xl font-bold text-indigo-600">{metrics.activeProposals}</p>
              <p class="text-sm text-indigo-600 mt-1">{$_('extensions.admin_dashboard.open_for_voting') || 'Open for voting'}</p>
            </div>
          {/if}
          
          {#if metrics.totalVotes > 0}
            <div class="bg-gradient-to-r from-teal-50 to-teal-100 p-6 rounded-lg border border-teal-200">
              <h3 class="text-lg font-semibold text-teal-800">{$_('extensions.admin_dashboard.citizen_votes') || 'Citizen Votes'}</h3>
              <p class="text-3xl font-bold text-teal-600">{metrics.totalVotes}</p>
              <p class="text-sm text-teal-600 mt-1">{$_('extensions.admin_dashboard.democratic_participation') || 'Democratic participation'}</p>
            </div>
          {/if}
        </div>
        
        {#if Object.keys(data).length === 0 && !loading}
          <div class="text-center py-12">
            <span class="text-6xl block mb-4">🏛️</span>
            <h3 class="text-xl font-semibold text-gray-700 mb-2">{$_('extensions.admin_dashboard.no_data_found') || 'No GGG Data Found'}</h3>
            <p class="text-gray-600 mb-4">{$_('extensions.admin_dashboard.load_demo_data') || 'Click "Load Demo Data" to populate the system with sample governance data'}</p>
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
        {:else if activeTab === 'transfers'}
          <GenericEntityTable 
            entityType="transfers"
            items={data.transfers || []}
            loading={loading}
            pagination={transfersPagination}
            onPageChange={handleTransfersPageChange}
          />
        {:else if activeTab === 'users'}
          <GenericEntityTable 
            entityType="users"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={usersPagination}
            onPageChange={handleUsersPageChange}
          />
        {:else if activeTab === 'mandates'}
          <GenericEntityTable 
            entityType="mandates"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={mandatesPagination}
            onPageChange={handleMandatesPageChange}
          />
        {:else if activeTab === 'tasks'}
          <GenericEntityTable 
            entityType="tasks"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={tasksPagination}
            onPageChange={handleTasksPageChange}
          />
        {:else if activeTab === 'instruments'}
          <GenericEntityTable 
            entityType="instruments"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={instrumentsPagination}
            onPageChange={handleInstrumentsPageChange}
          />
        {:else if activeTab === 'organizations'}
          <GenericEntityTable 
            entityType="organizations"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={organizationsPagination}
            onPageChange={handleOrganizationsPageChange}
          />
        {:else if activeTab === 'disputes'}
          <GenericEntityTable 
            entityType="disputes"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={disputesPagination}
            onPageChange={handleDisputesPageChange}
          />
        {:else if activeTab === 'licenses'}
          <GenericEntityTable 
            entityType="licenses"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={licensesPagination}
            onPageChange={handleLicensesPageChange}
          />
        {:else if activeTab === 'trades'}
          <GenericEntityTable 
            entityType="trades"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={tradesPagination}
            onPageChange={handleTradesPageChange}
          />
        {:else if activeTab === 'realms'}
          <GenericEntityTable 
            entityType="realms"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={realmsPagination}
            onPageChange={handleRealmsPageChange}
          />
        {:else if activeTab === 'proposals'}
          <GenericEntityTable 
            entityType="proposals"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={proposalsPagination}
            onPageChange={handleProposalsPageChange}
          />
        {:else if activeTab === 'votes'}
          <GenericEntityTable 
            entityType="votes"
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
            pagination={votesPagination}
            onPageChange={handleVotesPageChange}
          />
        {:else}
          <GenericEntityTable 
            entityType={activeTab}
            items={filteredData[activeTab] || data[activeTab] || []}
            loading={loading}
          />
        {/if}
      </div>
    {:else if activeTab === 'bulk_import'}
      <!-- Bulk Import Section -->
      <div class="p-6">
        <div class="max-w-4xl mx-auto">
          <h2 class="text-2xl font-bold mb-6 flex items-center">
            📥 {$_('extensions.admin_dashboard.bulk_import_title') || 'Bulk Data Import'}
          </h2>
          <p class="text-gray-600 mb-6">
            {$_('extensions.admin_dashboard.bulk_import_description') || 'Import multiple entities at once using CSV or JSON format. Select an entity type, choose your data format, and paste or load template data.'}
          </p>
          
          <!-- Configuration Section -->
          <div class="bg-gray-50 rounded-lg p-6 mb-6">
            <h3 class="text-lg font-semibold mb-4">{$_('extensions.admin_dashboard.import_configuration') || 'Import Configuration'}</h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <!-- Entity Type Selection -->
              <div>
                <label for="entity-type-select" class="block text-sm font-medium text-gray-700 mb-2">
                  {$_('extensions.admin_dashboard.entity_type') || 'Entity Type'}
                </label>
                <select 
                  id="entity-type-select"
                  bind:value={selectedEntityType}
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="users">{$_('extensions.admin_dashboard.users') || 'Users'}</option>
                  <option value="humans">{$_('extensions.admin_dashboard.humans') || 'Humans'}</option>
                  <option value="organizations">{$_('extensions.admin_dashboard.organizations') || 'Organizations'}</option>
                  <option value="mandates">{$_('extensions.admin_dashboard.mandates') || 'Mandates'}</option>
                  <option value="codexes">{$_('extensions.admin_dashboard.codexes') || 'Codexes'}</option>
                  <option value="instruments">{$_('extensions.admin_dashboard.instruments') || 'Instruments'}</option>
                </select>
              </div>
              
              <!-- Data Format Selection -->
              <div>
                <label for="data-format-select" class="block text-sm font-medium text-gray-700 mb-2">
                  {$_('extensions.admin_dashboard.data_format') || 'Data Format'}
                </label>
                <select 
                  id="data-format-select"
                  bind:value={selectedFormat}
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="csv">CSV</option>
                  <option value="json">JSON</option>
                </select>
              </div>
            </div>
            
            <!-- Template Actions -->
            <div class="flex flex-wrap gap-2">
              <button 
                on:click={clearImportData}
                class="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 focus:ring-4 focus:ring-gray-300 transition-colors"
              >
                🗑️ {$_('extensions.admin_dashboard.clear_data') || 'Clear Data'}
              </button>
            </div>
          </div>
          
          <!-- Data Input Section -->
          <div class="mb-6">
            <label for="import-data-textarea" class="block text-sm font-medium text-gray-700 mb-2">
              {$_('extensions.admin_dashboard.import_data_label') || 'Import Data'}
            </label>
            <textarea 
              id="import-data-textarea"
              bind:value={importData}
              placeholder={selectedFormat === 'csv' ? 'Paste CSV data here...' : 'Paste JSON data here...'}
              class="w-full h-64 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
            ></textarea>
          </div>
          
          <!-- Import Action -->
          <div class="mb-6">
            <button 
              on:click={importBulkData}
              disabled={importLoading || !importData.trim()}
              class="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 focus:ring-4 focus:ring-green-300 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center"
            >
              {#if importLoading}
                <span class="animate-spin mr-2">⏳</span>
                {$_('extensions.admin_dashboard.importing') || 'Importing...'}
              {:else}
                🚀 {$_('extensions.admin_dashboard.import_data') || 'Import Data'}
              {/if}
            </button>
          </div>
          
          <!-- Import Results -->
          {#if importResults}
            <div class="bg-green-50 border border-green-200 rounded-lg p-6">
              <h3 class="text-lg font-semibold text-green-800 mb-4 flex items-center">
                ✅ {$_('extensions.admin_dashboard.import_results') || 'Import Results'}
              </h3>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div class="text-center">
                  <div class="text-2xl font-bold text-green-600">{importResults.total_records}</div>
                  <div class="text-sm text-gray-600">{$_('extensions.admin_dashboard.total_records') || 'Total Records'}</div>
                </div>
                <div class="text-center">
                  <div class="text-2xl font-bold text-green-600">{importResults.successful}</div>
                  <div class="text-sm text-gray-600">{$_('extensions.admin_dashboard.successful') || 'Successful'}</div>
                </div>
                <div class="text-center">
                  <div class="text-2xl font-bold text-red-600">{importResults.failed}</div>
                  <div class="text-sm text-gray-600">{$_('extensions.admin_dashboard.failed') || 'Failed'}</div>
                </div>
              </div>
              
              {#if importResults.errors && importResults.errors.length > 0}
                <div class="mt-4">
                  <h4 class="font-semibold text-red-800 mb-2">{$_('extensions.admin_dashboard.errors') || 'Errors'}:</h4>
                  <ul class="list-disc list-inside text-sm text-red-700 space-y-1">
                    {#each importResults.errors as error}
                      <li>{error}</li>
                    {/each}
                  </ul>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    {:else if activeTab === 'registration_urls'}
      <!-- Registration URL Management -->
      <RegistrationUrlManager />
    {/if}
  </div>
</div>
