<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  import LandMap from './LandMap.svelte';
  import LandTable from './LandTable.svelte';
  import AdminControls from './AdminControls.svelte';
  
  let activeTab = 'map';
  let lands = [];
  let loading = false;
  let error = null;
  
  async function loadLands() {
    console.log('loadLands function called');
    try {
      loading = true;
      error = null;
      console.log('About to call backend.extension_sync_call');
      
      const result = await backend.extension_sync_call({
        extension_name: 'land_registry',
        function_name: 'get_lands',
        args: '{}'
      });
      
      console.log('Backend result:', result);
      
      if (result.success && result.data !== undefined) {
        const response = JSON.parse(result.data);
        console.log('Parsed response:', response);
        if (response.success) {
          lands = response.data;
          console.log('Lands loaded:', lands);
        } else {
          error = response.error;
        }
      } else {
        error = result.error || 'Failed to load lands';
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }
  
  onMount(() => {
    loadLands();
  });
</script>

<div class="land-registry">
  <div class="header mb-6">
    <h2 class="text-2xl font-bold text-gray-900">Land Registry</h2>
    <p class="text-gray-600">Manage land ownership and visualize parcels</p>
  </div>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
      Error: {error}
    </div>
  {/if}
  
  <div class="border-b border-gray-200 mb-6">
    <nav class="-mb-px flex space-x-8">
      <button 
        class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'map' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab = 'map'}
      >
        Map View
      </button>
      <button 
        class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'table' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab = 'table'}
      >
        Table View
      </button>
      <button 
        class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'admin' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab = 'admin'}
      >
        Admin Controls
      </button>
    </nav>
  </div>
  
  {#if loading}
    <div class="text-center py-8">Loading...</div>
  {:else if activeTab === 'map'}
    <LandMap {lands} on:refresh={loadLands} />
  {:else if activeTab === 'table'}
    <LandTable {lands} on:refresh={loadLands} />
  {:else if activeTab === 'admin'}
    <AdminControls on:refresh={loadLands} />
  {/if}
</div>
