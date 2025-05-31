<script>
  export let users = [];
  export let loading = false;
</script>

<div class="w-full overflow-x-auto">
  <h2 class="text-xl font-bold mb-4 flex items-center">
    <span class="mr-2">👤</span>
    Users
  </h2>
  <p class="text-sm text-gray-600 mb-4">Manage and monitor user accounts</p>
  
  <div class="flex justify-between items-center mb-4">
    <div class="flex items-center">
      <span class="mr-2">Filter by status</span>
      <select class="border rounded px-2 py-1">
        <option value="all">All</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
      </select>
    </div>
    <input type="text" placeholder="Search users..." class="border rounded px-3 py-1">
  </div>
  
  <table class="min-w-full bg-white">
    <thead>
      <tr class="bg-gray-100 border-b">
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">NAME</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TYPE</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CREATION TIME</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ACTIONS</th>
      </tr>
    </thead>
    <tbody>
      {#if loading}
        <tr>
          <td colspan="5" class="px-6 py-4 text-center">Loading...</td>
        </tr>
      {:else if users.length === 0}
        <tr>
          <td colspan="5" class="px-6 py-4 text-center">No users found</td>
        </tr>
      {:else}
        {#each users as user}
          <tr class="border-b hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">{user._id || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{user.name || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{user.type || 'User'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{user.created_at || 'N/A'}</td>
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
