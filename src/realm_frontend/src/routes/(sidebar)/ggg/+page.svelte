<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  
  import GenericEntityTable from '$lib/components/ggg/GenericEntityTable.svelte';
  
  let loading = true;
  let activeTab = 'overview';
  let error = null;
  let searchTerm = '';
  let data = {};
  let metrics = {};
  let relationships = [];
  let recentActivities = [];
  
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
    'realms'
  ];
  
  // Entity type configurations with their API endpoints
  const entityConfigs = [
    { name: 'users', fetch: () => backend.get_users(), dataPath: 'UsersList.users' },
    { name: 'mandates', fetch: () => backend.get_mandates(), dataPath: 'MandatesList.mandates' },
    { name: 'tasks', fetch: () => backend.get_tasks(), dataPath: 'TasksList.tasks' },
    { name: 'transfers', fetch: () => backend.get_transfers(), dataPath: 'TransfersList.transfers' },
    { name: 'instruments', fetch: () => backend.get_instruments(), dataPath: 'InstrumentsList.instruments' },
    { name: 'codexes', fetch: () => backend.get_codexes(), dataPath: 'CodexesList.codexes' },
    { name: 'organizations', fetch: () => backend.get_organizations(), dataPath: 'OrganizationsList.organizations' },
    { name: 'disputes', fetch: () => backend.get_disputes(), dataPath: 'DisputesList.disputes' },
    { name: 'licenses', fetch: () => backend.get_licenses(), dataPath: 'LicensesList.licenses' },
    { name: 'trades', fetch: () => backend.get_trades(), dataPath: 'TradesList.trades' },
    { name: 'realms', fetch: () => backend.get_realms(), dataPath: 'RealmsList.realms' }
  ];
  
  async function loadDemoData() {
    try {
      loading = true;
      error = null;
      
      console.log("Loading demo data...");
      const result = await backend.extension_sync_call({
        extension_name: "demo_loader",
        function_name: "load",
        args: "load_demo"
      });
      
      console.log("Demo data load result:", result);
      
      if (result.success) {
        console.log("Demo data loaded successfully:", result.response);
        await fetchAllData();
      } else {
        error = `Failed to load demo data: ${result.response || 'Unknown error'}`;
        console.error(error);
      }
    } catch (err) {
      error = `Error loading demo data: ${err.message}`;
      console.error("Demo data load error:", err);
    } finally {
      loading = false;
    }
  }
  
  async function fetchAllData() {
    try {
      loading = true;
      error = null;
      data = {};
      
      console.log("Fetching all GGG data...");
      
      // Try to fetch each entity type
      for (const config of entityConfigs) {
        try {
          const result = await config.fetch();
          
          if (result.success && result.data) {
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
            }
          }
        } catch (err) {
          console.log(`❌ ${config.name}: ${err.message}`);
        }
      }
      
      console.log("Data loaded:", Object.keys(data));
      
      // Calculate metrics and relationships
      calculateMetrics();
      findRelationships();
      getRecentActivity();
      
    } catch (error) {
      console.error("Error fetching data:", error);
      error = `Data fetch error: ${error.message}`;
    } finally {
      loading = false;
    }
  }
  
  function calculateMetrics() {
    const totalEntities = Object.values(data).reduce((sum, arr) => sum + (arr?.length || 0), 0);
    const totalTransfers = data.transfers?.length || 0;
    const totalTransferVolume = data.transfers?.reduce((sum, t) => sum + (parseFloat(t.amount) || 0), 0) || 0;
    const activeMandates = data.mandates?.filter(m => !isExpired(m)).length || 0;
    const scheduledTasks = data.tasks?.filter(t => hasSchedule(t)).length || 0;
    const openDisputes = data.disputes?.filter(d => d.status === 'OPEN' || d.status === 'pending').length || 0;
    
    metrics = {
      totalEntities,
      totalTransfers,
      totalTransferVolume,
      activeMandates,
      scheduledTasks,
      openDisputes
    };
  }
  
  function findRelationships() {
    relationships = [];
    
    // Find mandate-task relationships
    if (data.mandates && data.tasks) {
      data.mandates.forEach(mandate => {
        const relatedTasks = data.tasks.filter(task => 
          isRelated(task, mandate, 'mandate')
        );
        
        if (relatedTasks.length > 0) {
          relationships.push({
            type: 'mandate-tasks',
            source: mandate,
            targets: relatedTasks,
            label: `${mandate.name} → ${relatedTasks.length} tasks`
          });
        }
      });
    }
    
    // Find task-transfer relationships
    if (data.tasks && data.transfers) {
      data.tasks.forEach(task => {
        const relatedTransfers = data.transfers.filter(transfer =>
          isRelated(transfer, task, 'task')
        );
        
        if (relatedTransfers.length > 0) {
          relationships.push({
            type: 'task-transfers',
            source: task,
            targets: relatedTransfers,
            label: `${getTaskName(task)} → ${relatedTransfers.length} transfers`
          });
        }
      });
    }
  }
  
  function getRecentActivity() {
    const activities = [];
    
    // Collect timestamped entities from all types
    Object.entries(data).forEach(([entityType, entities]) => {
      if (Array.isArray(entities)) {
        entities.forEach(entity => {
          const timestamp = entity.timestamp_created || entity.created_at || entity.timestamp;
          if (timestamp) {
            activities.push({
              type: entityType,
              entity: entity,
              timestamp: timestamp,
              description: getActivityDescription(entityType, entity)
            });
          }
        });
      }
    });
    
    recentActivities = activities
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, 10);
  }
  
  function getActivityDescription(type, entity) {
    switch(type) {
      case 'transfers':
        return `Transfer of ${entity.amount || 'N/A'} from ${entity.from_user || 'unknown'} to ${entity.to_user || 'unknown'}`;
      case 'mandates':
        return `New mandate: ${entity.name || entity._id}`;
      case 'tasks':
        return `Task created: ${getTaskName(entity)}`;
      case 'disputes':
        return `Dispute opened: ${entity._id}`;
      case 'licenses':
        return `License issued: ${entity._id}`;
      default:
        return `New ${type.slice(0, -1)}: ${entity.name || entity._id}`;
    }
  }
  
  function isExpired(mandate) {
    // Basic expiration logic - can be enhanced
    return false;
  }
  
  function hasSchedule(task) {
    return task.schedules && task.schedules.length > 0;
  }
  
  function isRelated(entity1, entity2, relationField) {
    // Basic relationship detection - can be enhanced
    return entity1[relationField] === entity2._id;
  }
  
  function getTaskName(task) {
    try {
      const metadata = JSON.parse(task.metadata || '{}');
      return metadata.description || task._id;
    } catch (e) {
      return task._id;
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
      }
    });
    return filtered;
  }
  
  $: filteredData = filterData(data, searchTerm);
  
  onMount(fetchAllData);
</script>

<div class="container mx-auto p-4">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">GGG Dashboard</h1>
      <p class="text-gray-600 mt-1">Generalized Global Governance System</p>
    </div>
    <button 
      class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center transition-colors"
      on:click={loadDemoData}
      disabled={loading}
    >
      {#if loading}
        <div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
        Loading...
      {:else}
        <span class="mr-2">🔄</span> Load Demo Data
      {/if}
    </button>
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
        on:click={() => activeTab = 'overview'}
      >
        📊 Overview
      </button>
      {#each allEntityTypes as entityType}
        <button 
          class="px-4 py-2 mr-1 {activeTab === entityType ? 'border-b-2 border-blue-500 font-medium text-blue-600' : 'text-gray-600 hover:text-gray-900'}"
          on:click={() => activeTab = entityType}
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
        <h2 class="text-2xl font-bold mb-6">System Overview</h2>
        
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
          {#if recentActivities.length > 0}
            <div class="bg-gray-50 rounded-lg p-6">
              <h3 class="text-lg font-bold mb-4">Recent Activity</h3>
              <div class="space-y-3">
                {#each recentActivities as activity}
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
        <GenericEntityTable 
          entities={filteredData[activeTab] || data[activeTab] || []} 
          entityType={activeTab} 
          {loading} 
        />
      </div>
    {/if}
  </div>
</div> 