<script>
  export let entities = [];
  export let entityType = '';
  export let loading = false;
  
  // Dynamically determine columns based on entity structure
  $: columns = entities.length > 0 ? 
    Object.keys(entities[0]).filter(key => 
      !key.startsWith('_internal') && 
      !key.startsWith('relations') &&
      key !== 'timestamp_updated'
    ) : [];
  
  function formatValue(value, key) {
    if (value === null || value === undefined) return 'N/A';
    
    if (typeof value === 'object' && value !== null) {
      if (Array.isArray(value)) return `[${value.length} items]`;
      try {
        const parsed = JSON.parse(value);
        if (parsed.description) return parsed.description;
        if (parsed.type) return parsed.type;
        return JSON.stringify(parsed).substring(0, 50) + '...';
      } catch (e) {
        return JSON.stringify(value).substring(0, 50) + '...';
      }
    }
    
    if (key.includes('timestamp') || key.includes('date') || key.includes('created_at')) {
      try {
        return new Date(value).toLocaleDateString();
      } catch (e) {
        return value;
      }
    }
    
    if (key === 'amount' && typeof value === 'number') {
      return value.toLocaleString();
    }
    
    return String(value).length > 50 ? String(value).substring(0, 50) + '...' : value;
  }
  
  function getDisplayName(key) {
    return key.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  }
  
  function getEntityIcon(entityType) {
    const icons = {
      'users': '👤',
      'mandates': '📜',
      'tasks': '📋',
      'transfers': '🔄',
      'organizations': '🏢',
      'disputes': '⚖️',
      'licenses': '📄',
      'instruments': '💰',
      'codexes': '💻',
      'trades': '🤝',
      'realms': '🏛️',
      'treasury': '🏦'
    };
    return icons[entityType] || '📊';
  }
</script>

<div class="w-full overflow-x-auto">
  <h2 class="text-xl font-bold mb-4 flex items-center">
    <span class="mr-2">{getEntityIcon(entityType)}</span>
    {getDisplayName(entityType)} ({entities.length})
  </h2>
  <p class="text-sm text-gray-600 mb-4">
    {#if entityType === 'users'}
      Manage and monitor user accounts
    {:else if entityType === 'mandates'}
      Governance mandates and policies
    {:else if entityType === 'tasks'}
      Automated processes and schedules
    {:else if entityType === 'transfers'}
      Asset transfers between entities
    {:else}
      {getDisplayName(entityType)} in the system
    {/if}
  </p>
  
  {#if entities.length > 0}
    <table class="min-w-full bg-white border border-gray-200 rounded-lg">
      <thead>
        <tr class="bg-gray-100 border-b">
          {#each columns.slice(0, 6) as column}
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {getDisplayName(column)}
            </th>
          {/each}
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Actions
          </th>
        </tr>
      </thead>
      <tbody>
        {#if loading}
          <tr>
            <td colspan="{columns.length + 1}" class="px-6 py-4 text-center">
              <div class="flex items-center justify-center">
                <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                <span class="ml-2">Loading...</span>
              </div>
            </td>
          </tr>
        {:else}
          {#each entities as entity, index}
            <tr class="border-b hover:bg-gray-50 {index % 2 === 0 ? 'bg-white' : 'bg-gray-25'}">
              {#each columns.slice(0, 6) as column}
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  {formatValue(entity[column], column)}
                </td>
              {/each}
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <button class="text-blue-600 hover:text-blue-900 font-medium">View</button>
              </td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  {:else if !loading}
    <div class="text-center py-12 bg-gray-50 rounded-lg">
      <span class="text-4xl mb-4 block">{getEntityIcon(entityType)}</span>
      <h3 class="text-lg font-semibold text-gray-700 mb-2">No {getDisplayName(entityType)} Found</h3>
      {#if entityType === 'users' || entityType === 'mandates' || entityType === 'tasks' || entityType === 'transfers'}
        <p class="text-gray-600 mb-4">This entity type should have data. Try clicking "Load Demo Data" to populate it.</p>
        <div class="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm text-yellow-800 max-w-md mx-auto">
          💡 <strong>Tip:</strong> The {entityType} data might not be loading properly from the backend API.
        </div>
      {:else}
        <p class="text-gray-600 mb-4">No {entityType} have been created yet.</p>
        <p class="text-sm text-gray-500">Data for this entity type will appear here when available</p>
      {/if}
    </div>
  {:else}
    <div class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
      <p class="text-gray-600">Loading {entityType}...</p>
    </div>
  {/if}
</div> 