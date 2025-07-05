<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';
  
  console.log('=== GGG COMPONENT LOADING ===');
  console.log('Backend object:', backend);
  console.log('Backend type:', typeof backend);
  console.log('Backend methods:', Object.keys(backend || {}));
  
  let loading = false;
  let error = null;
  let users = [];
  let organizations = [];
  
  onMount(async () => {
    try {
      loading = true;
      console.log('=== MINIMAL GGG ONMOUNT STARTING ===');
      
      const usersResult = await backend.get_users(0, 5);
      console.log('Users result:', usersResult);
      
      if (usersResult && usersResult.success) {
        users = usersResult.data.UsersList?.users || [];
      }
      
      const orgsResult = await backend.get_organizations(0, 5);
      console.log('Organizations result:', orgsResult);
      
      if (orgsResult && orgsResult.success) {
        organizations = orgsResult.data.OrganizationsList?.organizations || [];
      }
      
      console.log('=== MINIMAL GGG LOADED SUCCESSFULLY ===');
    } catch (e) {
      console.error('Error in minimal GGG:', e);
      error = e.message;
    } finally {
      loading = false;
    }
  });
</script>

<div class="container mx-auto p-4">
  <h1 class="text-3xl font-bold text-gray-900 mb-6">🎯 GGG Admin Dashboard (Minimal)</h1>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
      Error: {error}
    </div>
  {/if}
  
  {#if loading}
    <div class="text-center py-10">
      <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      <p class="mt-2">Loading dummy data...</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="bg-white border rounded-lg p-4 shadow">
        <h2 class="text-xl font-bold mb-4">👤 Users ({users.length})</h2>
        {#if users.length > 0}
          <ul class="space-y-2">
            {#each users as user}
              <li class="p-2 bg-gray-50 rounded">{user._id || 'User'}</li>
            {/each}
          </ul>
        {:else}
          <p class="text-gray-600">No users found (dummy data)</p>
        {/if}
      </div>
      
      <div class="bg-white border rounded-lg p-4 shadow">
        <h2 class="text-xl font-bold mb-4">🏢 Organizations ({organizations.length})</h2>
        {#if organizations.length > 0}
          <ul class="space-y-2">
            {#each organizations as org}
              <li class="p-2 bg-gray-50 rounded">{org._id || 'Organization'}</li>
            {/each}
          </ul>
        {:else}
          <p class="text-gray-600">No organizations found (dummy data)</p>
        {/if}
      </div>
    </div>
    
    <div class="mt-6 p-4 bg-green-100 border border-green-400 rounded">
      <p class="text-green-700">✅ HOT RELOADING CONFIRMED! Text updated at {new Date().toLocaleTimeString()} without page refresh!</p>
    </div>
  {/if}
</div>
