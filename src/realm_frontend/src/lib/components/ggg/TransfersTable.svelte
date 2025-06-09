<script>
  export let transfers = [];
  export let loading = false;
  export let pagination = null;
  export let onPageChange = (page) => {};
  
  // Parse JSON strings if needed
  $: parsedTransfers = transfers.map(transfer => {
    if (typeof transfer === 'string') {
      try {
        return JSON.parse(transfer);
      } catch (e) {
        console.error('Error parsing transfer JSON:', e);
        return {};
      }
    }
    return transfer;
  });
  
  // Current page defaults to 1 if not provided in pagination
  $: currentPage = pagination?.page || 1;
  $: totalPages = pagination?.total_pages || 1;
  $: hasNextPage = pagination?.has_next || false;
  $: hasPrevPage = pagination?.has_prev || false;
  
  function changePage(newPage) {
    if (newPage >= 1 && newPage <= totalPages) {
      onPageChange(newPage);
    }
  }

  // Helper functions to adapt to the backend data structure
  function getTransferId(transfer) {
    return transfer._id || transfer.id || 'N/A';
  }
  
  function getFromUser(transfer) {
    // Check both formats: relations.from_user[0] (frontend expected) and from_user (backend actual)
    if (transfer.relations?.from_user?.[0]?._id) {
      return transfer.relations.from_user[0]._id;
    } else if (transfer.from_user?.id) {
      return transfer.from_user.id;
    } else if (transfer.from_user) {
      // If from_user is just a string or plain value
      return transfer.from_user;
    }
    return 'N/A';
  }
  
  function getToUser(transfer) {
    // Check both formats: relations.to_user[0] (frontend expected) and to_user (backend actual)
    if (transfer.relations?.to_user?.[0]?._id) {
      return transfer.relations.to_user[0]._id;
    } else if (transfer.to_user?.id) {
      return transfer.to_user.id;
    } else if (transfer.to_user) {
      // If to_user is just a string or plain value
      return transfer.to_user;
    }
    return 'N/A';
  }
  
  function getInstrument(transfer) {
    // Check both formats: relations.instrument[0] (frontend expected) and instrument (backend actual)
    if (transfer.relations?.instrument?.[0]?._id) {
      return transfer.relations.instrument[0]._id;
    } else if (transfer.instrument?.id) {
      return transfer.instrument.id;
    } else if (transfer.instrument) {
      // If instrument is just a string or plain value
      return transfer.instrument;
    }
    return 'N/A';
  }
  
  function getCreatedAt(transfer) {
    // Check various possible timestamp field names
    return transfer.timestamp_created || transfer.created_at || transfer.timestamp || 'N/A';
  }
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
      {:else if parsedTransfers.length === 0}
        <tr>
          <td colspan="7" class="px-6 py-4 text-center">No transfers found</td>
        </tr>
      {:else}
        {#each parsedTransfers as transfer}
          <tr class="border-b hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">{getTransferId(transfer)}</td>
            <td class="px-6 py-4 whitespace-nowrap">{getFromUser(transfer)}</td>
            <td class="px-6 py-4 whitespace-nowrap">{getToUser(transfer)}</td>
            <td class="px-6 py-4 whitespace-nowrap">{getInstrument(transfer)}</td>
            <td class="px-6 py-4 whitespace-nowrap">{transfer.amount || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap">{getCreatedAt(transfer)}</td>
            <td class="px-6 py-4 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-900">View</button>
            </td>
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
  
  {#if pagination && totalPages > 1}
    <div class="flex justify-center items-center mt-4 space-x-2">
      <button 
        class="px-3 py-1 rounded border {hasPrevPage ? 'bg-blue-100 hover:bg-blue-200' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}" 
        disabled={!hasPrevPage}
        on:click={() => changePage(currentPage - 1)}
      >
        Previous
      </button>
      
      <div class="flex space-x-1">
        {#if totalPages <= 7}
          {#each Array(totalPages) as _, i}
            <button 
              class="w-8 h-8 rounded-full {currentPage === i+1 ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}"
              on:click={() => changePage(i+1)}
            >
              {i+1}
            </button>
          {/each}
        {:else}
          <!-- Show first page, current page neighborhood, and last page with ellipsis -->
          <button 
            class="w-8 h-8 rounded-full {currentPage === 1 ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}"
            on:click={() => changePage(1)}
          >
            1
          </button>
          
          {#if currentPage > 3}
            <span class="px-1">...</span>
          {/if}
          
          {#each Array(3).fill(0) as _, i}
            {@const pageNum = Math.max(2, Math.min(currentPage - 1 + i, totalPages - 1))}
            {#if pageNum > 1 && pageNum < totalPages}
              <button 
                class="w-8 h-8 rounded-full {currentPage === pageNum ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}"
                on:click={() => changePage(pageNum)}
              >
                {pageNum}
              </button>
            {/if}
          {/each}
          
          {#if currentPage < totalPages - 2}
            <span class="px-1">...</span>
          {/if}
          
          <button 
            class="w-8 h-8 rounded-full {currentPage === totalPages ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}"
            on:click={() => changePage(totalPages)}
          >
            {totalPages}
          </button>
        {/if}
      </div>
      
      <button 
        class="px-3 py-1 rounded border {hasNextPage ? 'bg-blue-100 hover:bg-blue-200' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}" 
        disabled={!hasNextPage}
        on:click={() => changePage(currentPage + 1)}
      >
        Next
      </button>
    </div>
  {/if}
  
  {#if pagination}
    <div class="text-xs text-gray-500 mt-2 text-center">
      Showing {parsedTransfers.length} of {pagination.total} transfers (Page {currentPage} of {totalPages})
    </div>
  {/if}
</div>
