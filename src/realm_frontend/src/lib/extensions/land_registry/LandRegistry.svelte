<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  import LandMap from './LandMap.svelte';
  import GeographicMap from './GeographicMap.svelte';
  import LandTable from './LandTable.svelte';
  import AdminControls from './AdminControls.svelte';
  import { _ } from 'svelte-i18n';
  import SafeText from '$lib/components/SafeText.svelte';
  
  let activeTab = 'map';
  let lands = [];
  let loading = false;
  let error = null;
  
  async function loadLands() {
    console.log('=== loadLands function called ===');
    try {
      loading = true;
      error = null;
      console.log('Setting loading to true, error to null');
      console.log('About to call backend.extension_sync_call with:', {
        extension_name: 'land_registry',
        function_name: 'get_lands',
        args: '{}'
      });
      
      const result = await backend.extension_sync_call({
        extension_name: 'land_registry',
        function_name: 'get_lands',
        args: '{}'
      });
      
      console.log('=== Backend result received ===');
      console.log('Result type:', typeof result);
      console.log('Result keys:', Object.keys(result || {}));
      console.log('Result.success:', result?.success);
      console.log('Result.data type:', typeof result?.data);
      console.log('Result.data value:', result?.data);
      console.log('Result.error:', result?.error);
      console.log('Full result object:', JSON.stringify(result, null, 2));
      
      if (result && result.success && result.data !== undefined) {
        console.log('=== Parsing result.data ===');
        try {
          const response = JSON.parse(result.data);
          console.log('Parsed response type:', typeof response);
          console.log('Parsed response keys:', Object.keys(response || {}));
          console.log('Parsed response.success:', response?.success);
          console.log('Parsed response.data:', response?.data);
          console.log('Parsed response.error:', response?.error);
          
          if (response.success) {
            lands = response.data;
            console.log('=== SUCCESS: Lands loaded ===');
            console.log('Lands array length:', lands?.length);
            console.log('Lands data:', JSON.stringify(lands, null, 2));
            error = null;
          } else {
            console.log('=== ERROR: Response not successful ===');
            error = response.error || 'Backend returned unsuccessful response';
            console.log('Setting error to:', error);
          }
        } catch (parseErr) {
          console.log('=== ERROR: JSON Parse failed ===');
          console.log('Parse error:', parseErr.message);
          console.log('Raw data that failed to parse:', result.data);
          error = `Failed to parse response: ${parseErr.message}`;
        }
      } else {
        console.log('=== ERROR: Invalid result structure ===');
        console.log('Result success check failed');
        error = result?.error || 'Failed to load lands - invalid response structure';
        console.log('Setting error to:', error);
      }
    } catch (err) {
      console.log('=== ERROR: Exception caught ===');
      console.log('Exception type:', err.constructor.name);
      console.log('Exception message:', err.message);
      console.log('Exception stack:', err.stack);
      error = `Exception: ${err.message}`;
    } finally {
      loading = false;
      console.log('=== loadLands completed ===');
      console.log('Final state - loading:', loading);
      console.log('Final state - error:', error);
      console.log('Final state - lands length:', lands?.length);
    }
  }
  
  onMount(() => {
    loadLands();
  });
</script>

<div class="land-registry">
  <div class="header mb-6">
    <h2 class="text-2xl font-bold text-gray-900">
      <SafeText key="extensions.land_registry.title" spinnerSize="sm" />
    </h2>
    <p class="text-gray-600">
      <SafeText key="extensions.land_registry.description" spinnerSize="sm" />
    </p>
  </div>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
      {$_('common.error')}: {error}
    </div>
  {/if}
  
  <div class="border-b border-gray-200 mb-6">
    <nav class="-mb-px flex space-x-8">
      <button 
        class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'map' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab = 'map'}
      >
        <SafeText key="extensions.land_registry.grid_view" spinnerSize="xs" />
      </button>
      <button 
        class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'geographic' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab = 'geographic'}
      >
        <SafeText key="extensions.land_registry.geographic_map" spinnerSize="xs" />
      </button>
      <button 
        class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'table' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab = 'table'}
      >
        <SafeText key="extensions.land_registry.table_view" spinnerSize="xs" />
      </button>
      <button 
        class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'admin' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab = 'admin'}
      >
        <SafeText key="extensions.land_registry.admin_controls" spinnerSize="xs" />
      </button>
    </nav>
  </div>
  
  {#if loading}
    <div class="text-center py-8">{$_('common.loading')}</div>
  {:else if activeTab === 'map'}
    <LandMap {lands} on:refresh={loadLands} />
  {:else if activeTab === 'geographic'}
    <GeographicMap {lands} on:refresh={loadLands} />
  {:else if activeTab === 'table'}
    <LandTable {lands} on:refresh={loadLands} />
  {:else if activeTab === 'admin'}
    <AdminControls on:refresh={loadLands} />
  {/if}
</div>
