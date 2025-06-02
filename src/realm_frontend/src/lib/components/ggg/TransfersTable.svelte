<script>
  export let transfers = [];
  export let loading = false;
</script>

<div class="w-full overflow-x-auto">
  <h2 class="text-xl font-bold mb-4 flex items-center">
    <span class="mr-2">🔄</span>
    Transfers
  </h2>
  <p class="text-sm text-gray-600 mb-4">Track asset transfers between users</p>
  
  <div class="flex justify-between items-center mb-4">
    <div class="flex items-center">
      <span class="mr-2">Filter by type</span>
      <select class="border rounded px-2 py-1">
        <option value="all">All</option>
        <option value="pension">Pension</option>
        <option value="tax">Tax</option>
        <option value="license">License Fee</option>
      </select>
    </div>
    <input type="text" placeholder="Search transfers..." class="border rounded px-3 py-1">
  </div>
  
  <table class="min-w-full bg-white">
    <thead>
      <tr class="bg-gray-100 border-b">
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">FROM</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TO</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">INSTRUMENT</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">AMOUNT</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CREATED AT</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ACTIONS</th>
      </tr>
    </thead>
    <tbody>
      {#if loading}
        <tr>
          <td colspan="7" class="px-6 py-4 text-center">Loading...</td>
        </tr>
      {:else if transfers.length === 0}
        <tr>
          <td colspan="7" class="px-6 py-4 text-center">No transfers found</td>
        </tr>
      {:else}
        {#each transfers as transfer}
          <tr class="border-b hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">{transfer._id || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">
              {transfer.relations?.from_user?.[0]?._id || 'N/A'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              {transfer.relations?.to_user?.[0]?._id || 'N/A'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              {transfer.relations?.instrument?.[0]?._id || 'N/A'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">{transfer.amount || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{transfer.timestamp_created || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-900">View</button>
            </td>
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>
