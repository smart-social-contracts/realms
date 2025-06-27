<script>
  import { createEventDispatcher } from 'svelte';
  import { backend } from '$lib/canisters';
  
  const dispatch = createEventDispatcher();
  
  let loading = false;
  let error = null;
  let success = null;
  
  let newLand = {
    x_coordinate: 0,
    y_coordinate: 0,
    land_type: 'unassigned',
    size_width: 1,
    size_height: 1
  };
  
  let ownership = {
    land_id: '',
    owner_user_id: '',
    owner_organization_id: '',
    owner_type: 'none'
  };
  
  const landTypes = [
    { value: 'unassigned', label: 'Unassigned' },
    { value: 'residential', label: 'Residential' },
    { value: 'agricultural', label: 'Agricultural' },
    { value: 'industrial', label: 'Industrial' },
    { value: 'commercial', label: 'Commercial' }
  ];
  
  async function createLand() {
    try {
      loading = true;
      error = null;
      success = null;
      
      const result = await backend.extension_sync_call({
        extension_name: 'land_registry',
        function_name: 'create_land',
        args: JSON.stringify(newLand)
      });
      
      if (result.success && result.data) {
        const response = JSON.parse(result.data);
        if (response.success) {
          success = 'Land created successfully!';
          newLand = { x_coordinate: 0, y_coordinate: 0, land_type: 'unassigned', size_width: 1, size_height: 1 };
          dispatch('refresh');
        } else {
          error = response.error;
        }
      } else {
        error = result.error || 'Failed to create land';
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }
  
  async function updateOwnership() {
    try {
      loading = true;
      error = null;
      success = null;
      
      const ownershipData = {
        land_id: ownership.land_id,
        owner_user_id: ownership.owner_type === 'user' ? ownership.owner_user_id : null,
        owner_organization_id: ownership.owner_type === 'organization' ? ownership.owner_organization_id : null
      };
      
      const result = await backend.extension_sync_call({
        extension_name: 'land_registry',
        function_name: 'update_land_ownership',
        args: JSON.stringify(ownershipData)
      });
      
      if (result.success && result.data) {
        const response = JSON.parse(result.data);
        if (response.success) {
          success = 'Ownership updated successfully!';
          ownership = { land_id: '', owner_user_id: '', owner_organization_id: '', owner_type: 'none' };
          dispatch('refresh');
        } else {
          error = response.error;
        }
      } else {
        error = result.error || 'Failed to update ownership';
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }
</script>

<div class="admin-controls space-y-8">
  <div>
    <h3 class="text-lg font-semibold mb-4">Admin Controls</h3>
    <p class="text-gray-600 mb-6">Create new land parcels and manage ownership</p>
  </div>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      Error: {error}
    </div>
  {/if}
  
  {#if success}
    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
      {success}
    </div>
  {/if}
  
  <div class="bg-white p-6 border border-gray-200 rounded-lg">
    <h4 class="text-md font-semibold mb-4">Create New Land Parcel</h4>
    <form on:submit|preventDefault={createLand} class="space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">X Coordinate</label>
          <input 
            type="number" 
            bind:value={newLand.x_coordinate}
            min="0"
            max="19"
            class="w-full border border-gray-300 rounded px-3 py-2"
            required
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Y Coordinate</label>
          <input 
            type="number" 
            bind:value={newLand.y_coordinate}
            min="0"
            max="19"
            class="w-full border border-gray-300 rounded px-3 py-2"
            required
          />
        </div>
      </div>
      
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Land Type</label>
        <select bind:value={newLand.land_type} class="w-full border border-gray-300 rounded px-3 py-2">
          {#each landTypes as type}
            <option value={type.value}>{type.label}</option>
          {/each}
        </select>
      </div>
      
      <button 
        type="submit" 
        disabled={loading}
        class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Creating...' : 'Create Land Parcel'}
      </button>
    </form>
  </div>
  
  <div class="bg-white p-6 border border-gray-200 rounded-lg">
    <h4 class="text-md font-semibold mb-4">Update Land Ownership</h4>
    <form on:submit|preventDefault={updateOwnership} class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Land ID</label>
        <input 
          type="text" 
          bind:value={ownership.land_id}
          class="w-full border border-gray-300 rounded px-3 py-2"
          placeholder="Enter land ID"
          required
        />
      </div>
      
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Owner Type</label>
        <select bind:value={ownership.owner_type} class="w-full border border-gray-300 rounded px-3 py-2">
          <option value="none">No Owner</option>
          <option value="user">Citizen</option>
          <option value="organization">Organization</option>
        </select>
      </div>
      
      {#if ownership.owner_type === 'user'}
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">User ID</label>
          <input 
            type="text" 
            bind:value={ownership.owner_user_id}
            class="w-full border border-gray-300 rounded px-3 py-2"
            placeholder="Enter user ID"
            required
          />
        </div>
      {:else if ownership.owner_type === 'organization'}
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Organization ID</label>
          <input 
            type="text" 
            bind:value={ownership.owner_organization_id}
            class="w-full border border-gray-300 rounded px-3 py-2"
            placeholder="Enter organization ID"
            required
          />
        </div>
      {/if}
      
      <button 
        type="submit" 
        disabled={loading}
        class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? 'Updating...' : 'Update Ownership'}
      </button>
    </form>
  </div>
</div>
