<script>
  import { createEventDispatcher } from 'svelte';
  import GenericEntityTable from '$lib/components/ggg/GenericEntityTable.svelte';
  
  export let lands = [];
  
  const dispatch = createEventDispatcher();
  
  $: tableData = lands.map(land => ({
    ID: land.id,
    Coordinates: `(${land.x_coordinate}, ${land.y_coordinate})`,
    Type: land.land_type,
    Owner: land.owner_user_id || land.owner_organization_id || 'Unowned',
    'Owner Type': land.owner_user_id ? 'Citizen' : land.owner_organization_id ? 'Organization' : 'None',
    'Created At': new Date(land.created_at).toLocaleDateString(),
    'Updated At': new Date(land.updated_at).toLocaleDateString()
  }));
  
  const columns = [
    { key: 'ID', label: 'ID' },
    { key: 'Coordinates', label: 'Coordinates' },
    { key: 'Type', label: 'Land Type' },
    { key: 'Owner', label: 'Owner' },
    { key: 'Owner Type', label: 'Owner Type' },
    { key: 'Created At', label: 'Created' },
    { key: 'Updated At', label: 'Updated' }
  ];
</script>

<div class="land-table">
  <div class="mb-4">
    <h3 class="text-lg font-semibold">Land Registry Table</h3>
    <p class="text-gray-600">All registered land parcels</p>
  </div>
  
  {#if tableData.length > 0}
    <GenericEntityTable 
      data={tableData} 
      {columns}
      title="Land Parcels"
    />
  {:else}
    <div class="text-center py-8 text-gray-500">
      No land parcels registered yet.
    </div>
  {/if}
</div>
