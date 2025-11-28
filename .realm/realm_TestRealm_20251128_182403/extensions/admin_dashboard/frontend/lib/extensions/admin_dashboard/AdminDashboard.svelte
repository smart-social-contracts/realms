<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  import GenericEntityTable from '$lib/components/ggg/GenericEntityTable.svelte';
  import { ClipboardListOutline } from 'flowbite-svelte-icons';
  
  let selectedType = 'users';
  let items = [];
  let loading = false;
  let expandedItem = null;
  
  // Pagination state
  let currentPage = 0;
  let pageSize = 10;
  let totalItems = 0;
  let totalPages = 0;
  
  // Entity types configuration - all GGG entities
  const entityTypes = [
    // Core Entities
    { value: 'users', label: '👤 Users', className: 'User' },
    { value: 'citizens', label: '🙋 Citizens', className: 'Citizen' },
    { value: 'humans', label: '🧑 Humans', className: 'Human' },
    { value: 'identities', label: '🆔 Identities', className: 'Identity' },
    { value: 'user_profiles', label: '📋 User Profiles', className: 'UserProfile' },
    
    // Organizations & Realms
    { value: 'organizations', label: '🏢 Organizations', className: 'Organization' },
    { value: 'realms', label: '🏛️ Realms', className: 'Realm' },
    
    // Governance
    { value: 'mandates', label: '📜 Mandates', className: 'Mandate' },
    { value: 'proposals', label: '🗳️ Proposals', className: 'Proposal' },
    { value: 'votes', label: '✅ Votes', className: 'Vote' },
    { value: 'codexes', label: '📚 Codexes', className: 'Codex' },
    
    // Financial
    { value: 'instruments', label: '💰 Instruments', className: 'Instrument' },
    { value: 'transfers', label: '🔄 Transfers', className: 'Transfer' },
    { value: 'balances', label: '💵 Balances', className: 'Balance' },
    { value: 'treasuries', label: '🏦 Treasuries', className: 'Treasury' },
    { value: 'tax_records', label: '📊 Tax Records', className: 'TaxRecord' },
    
    // Assets & Resources
    { value: 'lands', label: '🏞️ Lands', className: 'Land' },
    { value: 'licenses', label: '📃 Licenses', className: 'License' },
    
    // Contracts & Agreements
    { value: 'contracts', label: '📝 Contracts', className: 'Contract' },
    { value: 'trades', label: '🤝 Trades', className: 'Trade' },
    { value: 'services', label: '⚙️ Services', className: 'Service' },
    
    // Tasks & Operations
    { value: 'tasks', label: '📋 Tasks', className: 'Task' },
    { value: 'task_schedules', label: '⏰ Task Schedules', className: 'TaskSchedule' },
    { value: 'task_executions', label: '▶️ Task Executions', className: 'TaskExecution' },
    
    // Disputes & Notifications
    { value: 'disputes', label: '⚖️ Disputes', className: 'Dispute' },
    { value: 'notifications', label: '🔔 Notifications', className: 'Notification' },
    
    // Permissions
    { value: 'permissions', label: '🔐 Permissions', className: 'Permission' }
  ];
  
  async function loadData() {
    loading = true;
    expandedItem = null;
    const entityConfig = entityTypes.find(t => t.value === selectedType);
    
    console.log(`📥 Loading ${entityConfig.label} - Page ${currentPage + 1}...`);
    
    try {
      const result = await backend.get_objects_paginated(
        entityConfig.className,
        currentPage,
        pageSize,
        'desc'
      );
      
      if (result.success && result.data) {
        const objects = result.data.objectsListPaginated?.objects || [];
        items = objects.map(obj => {
          try {
            return typeof obj === 'string' ? JSON.parse(obj) : obj;
          } catch (e) {
            return obj;
          }
        });
        
        const pagination = result.data.objectsListPaginated?.pagination;
        if (pagination) {
          // Convert BigInt to Number for JavaScript operations
          totalItems = Number(pagination.total_items || 0);
          totalPages = Number(pagination.total_pages || 0);
        }
        
        console.log(`✅ Loaded ${items.length} items (Page ${currentPage + 1}/${totalPages})`);
      }
    } catch (error) {
      console.error(`❌ Error loading data:`, error);
      items = [];
    } finally {
      loading = false;
    }
  }
  
  function toggleExpand(index) {
    expandedItem = expandedItem === index ? null : index;
  }
  
  function copyJSON(item) {
    const json = JSON.stringify(item, null, 2);
    navigator.clipboard.writeText(json);
    alert('✅ JSON copied to clipboard!');
  }
  
  function goToPage(page) {
    currentPage = page;
    loadData();
  }
  
  function nextPage() {
    if (currentPage < totalPages - 1) goToPage(currentPage + 1);
  }
  
  function prevPage() {
    if (currentPage > 0) goToPage(currentPage - 1);
  }
  
  function firstPage() {
    goToPage(0);
  }
  
  function lastPage() {
    goToPage(totalPages - 1);
  }
  
  onMount(() => {
    console.log('🚀 Simple AdminDashboard mounted');
    // Don't auto-load data - let user explicitly click Load Data button
  });
</script>

<div class="w-full px-4 max-w-none">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
      <p class="text-gray-600 mt-1">Manage realm entities</p>
    </div>
  </div>
  
  <!-- Controls -->
  <div class="mb-6 bg-white shadow-sm rounded-lg p-4">
    <div class="flex items-center gap-4">
      <label for="entity-type-select" class="font-medium text-gray-700">Entity Type:</label>
      <select 
        id="entity-type-select"
        bind:value={selectedType}
        class="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {#each entityTypes as type}
          <option value={type.value}>{type.label}</option>
        {/each}
      </select>
      
      <button 
        on:click={loadData}
        disabled={loading}
        class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
      >
        {loading ? '⏳ Loading...' : '📥 Load Data'}
      </button>
      
      <div class="ml-auto text-gray-600">
        {#if totalItems >= 0}
          Showing {items.length} of {totalItems} items
        {/if}
      </div>
    </div>
  </div>
  
  <!-- Items List -->
  <div class="bg-white shadow-sm rounded-lg">
    {#if loading}
      <div class="text-center py-10 p-6">
        <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        <p class="mt-2 text-gray-600">Loading data...</p>
      </div>
    {:else if items.length === 0}
      <div class="text-center py-10 p-6">
        <span class="text-6xl block mb-4">📭</span>
        <p class="text-gray-600">No items found. Click "Load Data" to fetch entities.</p>
      </div>
    {:else}
      <div class="divide-y divide-gray-200">
        {#each items as item, index}
          <div class="p-4 hover:bg-gray-50 transition">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-3">
                  <button 
                    on:click={() => toggleExpand(index)}
                    class="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    {expandedItem === index ? '▼' : '▶'} 
                    {item._type || 'Entity'} #{item._id || index + 1}
                  </button>
                  {#if item.name}
                    <span class="text-gray-700">- {item.name}</span>
                  {/if}
                  {#if item.id}
                    <span class="text-xs text-gray-500">({item.id})</span>
                  {/if}
                </div>
              </div>
              
              <button 
                on:click={() => copyJSON(item)}
                class="p-1.5 hover:bg-gray-100 text-gray-600 hover:text-gray-900 rounded transition-colors"
                title="Copy JSON"
              >
                <ClipboardListOutline class="w-4 h-4" />
              </button>
            </div>
            
            {#if expandedItem === index}
              <div class="mt-4 bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  {#each Object.entries(item) as [key, value]}
                    <div>
                      <span class="font-semibold text-gray-700">{key}:</span>
                      <span class="text-gray-600 ml-2">
                        {typeof value === 'object' ? JSON.stringify(value) : value}
                      </span>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        {/each}
      </div>
      
      <!-- Pagination Controls -->
      {#if totalPages > 1}
        <div class="border-t border-gray-200 p-4 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <button 
              on:click={firstPage}
              disabled={currentPage === 0}
              class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ⏮ First
            </button>
            <button 
              on:click={prevPage}
              disabled={currentPage === 0}
              class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ◀ Prev
            </button>
          </div>
          
          <div class="flex items-center gap-1">
            {#each Array(Math.min(5, totalPages)) as _, i}
              {#if totalPages <= 5}
                <button 
                  on:click={() => goToPage(i)}
                  class="px-3 py-1 border rounded {currentPage === i ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 hover:bg-gray-50'}"
                >
                  {i + 1}
                </button>
              {:else if i < 2 || i >= totalPages - 2 || Math.abs(currentPage - i) <= 1}
                <button 
                  on:click={() => goToPage(i)}
                  class="px-3 py-1 border rounded {currentPage === i ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 hover:bg-gray-50'}"
                >
                  {i + 1}
                </button>
              {:else if i === 2}
                <span class="px-2">...</span>
              {/if}
            {/each}
          </div>
          
          <div class="flex items-center gap-2">
            <button 
              on:click={nextPage}
              disabled={currentPage >= totalPages - 1}
              class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next ▶
            </button>
            <button 
              on:click={lastPage}
              disabled={currentPage >= totalPages - 1}
              class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Last ⏭
            </button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>
