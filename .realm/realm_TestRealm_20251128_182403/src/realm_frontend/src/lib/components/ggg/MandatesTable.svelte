<script>
  export let mandates = [];
  export let loading = false;
  
  function getDescription(metadata) {
    if (!metadata) return 'N/A';
    try {
      const parsed = JSON.parse(metadata);
      return parsed.description || 'N/A';
    } catch (e) {
      return metadata || 'N/A';
    }
  }
</script>

<div class="w-full overflow-x-auto">
  <h2 class="text-xl font-bold mb-4 flex items-center">
    <span class="mr-2">📜</span>
    Mandates
  </h2>
  <p class="text-sm text-gray-600 mb-4">Manage governance mandates and policies</p>
  
  <div class="flex justify-between items-center mb-4">
    <div class="flex items-center">
      <span class="mr-2">Filter by status</span>
      <select class="border rounded px-2 py-1">
        <option value="all">All</option>
        <option value="active">Active</option>
        <option value="expired">Expired</option>
      </select>
    </div>
    <input type="text" placeholder="Search mandates..." class="border rounded px-3 py-1">
  </div>
  
  <table class="min-w-full bg-white">
    <thead>
      <tr class="bg-gray-100 border-b">
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">NAME</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">DESCRIPTION</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">STATUS</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ACTIONS</th>
      </tr>
    </thead>
    <tbody>
      {#if loading}
        <tr>
          <td colspan="5" class="px-6 py-4 text-center">Loading...</td>
        </tr>
      {:else if mandates.length === 0}
        <tr>
          <td colspan="5" class="px-6 py-4 text-center">No mandates found</td>
        </tr>
      {:else}
        {#each mandates as mandate}
          <tr class="border-b hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">{mandate._id || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{mandate.name || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{getDescription(mandate.metadata)}</td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                Active
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-900 mr-2">View</button>
              <button class="text-gray-600 hover:text-gray-900">Edit</button>
            </td>
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>
