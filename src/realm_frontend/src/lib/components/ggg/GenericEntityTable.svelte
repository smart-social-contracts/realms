<script>
  export let entityType = '';
  export let items = [];
  export let loading = false;
  export let pagination = null;
  export let onPageChange = (page) => {
    console.log(`Page change requested for ${entityType} to page ${page}`);
  };
  
  console.log('entityType', entityType);
  console.log('items', items);
  console.log('loading', loading);
  console.log('pagination', pagination);
  
  // Alias for backward compatibility
  $: entities = items;
  
  // Dynamically determine columns based on entity structure
  $: columns = entities.length > 0 ? 
    Object.keys(entities[0]).filter(key => 
      !key.startsWith('_internal') && 
      key !== 'timestamp_updated' &&
      key !== 'relations'
    ) : [];
  
  // Import transfer table for specialized display
  import TransfersTable from './TransfersTable.svelte';
  import { Table, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell, Button } from 'flowbite-svelte';
  import { ChevronLeftOutline, ChevronRightOutline } from 'flowbite-svelte-icons';
  
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
        // Handle different date formats
        if (typeof value === 'string') {
          // Try parsing the date string
          const date = new Date(value);
          if (isNaN(date.getTime())) {
            return value; // Return original if not a valid date
          }
          return date.toLocaleDateString();
        }
        return new Date(value).toLocaleDateString();
      } catch (e) {
        return value;
      }
    }
    
    if (key === 'amount' && typeof value === 'number') {
      // Special handling for ckBTC amounts (convert from satoshis)
      // Note: This is a simple heuristic - in a real app you'd want to check the instrument type
      if (value >= 10000000 && value % 10000000 === 0) {
        // Likely ckBTC in satoshis - convert to decimal
        return (value / 100000000).toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 8}) + ' ckBTC';
      }
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
      'treasury': '🏦',
      'proposals': '🗳️',
      'votes': '✅'
    };
    return icons[entityType] || '📊';
  }
  
  // Extract meaningful information from metadata
  function getEntityDescription(entity, entityType) {
    if (entity.metadata) {
      try {
        const metadata = JSON.parse(entity.metadata);
        switch(entityType) {
          case 'proposals':
            return metadata.title || entity._id;
          case 'votes':
            return `${metadata.voter}: ${metadata.vote} on ${metadata.proposal_id}`;
          case 'transfers':
            return metadata.purpose || `Transfer: ${entity.amount}`;
          case 'mandates':
            return metadata.description || entity.name;
          case 'tasks':
            return metadata.description || entity._id;
          case 'licenses':
            return `${metadata.type} for ${metadata.holder}`;
          case 'instruments':
            return `${metadata.symbol}: ${metadata.description}`;
          default:
            return metadata.description || metadata.title || entity.name || entity._id;
        }
      } catch (e) {
        return entity.name || entity._id;
      }
    }
    return entity.name || entity._id;
  }
  
  // Get relationship info
  function getRelationshipInfo(entity) {
    if (entity.relations) {
      const relationCount = Object.values(entity.relations).reduce((sum, rel) => {
        return sum + (Array.isArray(rel) ? rel.length : 0);
      }, 0);
      if (relationCount > 0) {
        return `${relationCount} relations`;
      }
    }
    return '';
  }
  
  // Pagination helpers for users
  $: safePagination = pagination ? {
    page_num: Number(pagination.page_num),
    total_pages: Number(pagination.total_pages),
    total_items_count: Number(pagination.total_items_count),
    page_size: Number(pagination.page_size)
  } : null;
  $: currentPage = (safePagination?.page_num ?? 0) + 1;
  $: totalPages = safePagination?.total_pages ?? 1;
  $: hasNextPage = safePagination ? (safePagination.page_num + 1 < safePagination.total_pages) : false;
  $: hasPrevPage = safePagination ? (safePagination.page_num > 0) : false;
  
  $: if (pagination) console.log('GENERIC TABLE PAGINATION:', entityType, pagination);
</script>

<div class="w-full overflow-x-auto">
  <h2 class="text-xl font-bold mb-4 flex items-center">
    <span class="mr-2">{getEntityIcon(entityType)}</span>
    {getDisplayName(entityType)} ({entities.length})
  </h2>
  <p class="text-sm text-gray-600 mb-4">
    {#if entityType === 'users'}
      Manage and monitor user accounts and citizen profiles
    {:else if entityType === 'mandates'}
      Governance mandates and policies that define system rules
    {:else if entityType === 'tasks'}
      Automated processes and scheduled operations
    {:else if entityType === 'transfers'}
      Asset transfers and financial transactions between entities
    {:else if entityType === 'proposals'}
      Governance proposals for citizen voting and decision making
    {:else if entityType === 'votes'}
      Citizen votes on governance proposals and democratic participation
    {:else if entityType === 'instruments'}
      Financial instruments and digital assets in the treasury
    {:else if entityType === 'licenses'}
      Issued licenses and permits for various activities
    {:else if entityType === 'disputes'}
      Open disputes and conflicts requiring resolution
    {:else}
      {getDisplayName(entityType)} in the system
    {/if}
  </p>
  {#if loading}
    <div class="text-center py-10">
      <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      <p class="mt-2 text-gray-600">Loading {entityType}...</p>
    </div>
  {:else if entities.length === 0}
    <div class="text-center py-10 bg-gray-50 rounded-lg">
      <p class="text-gray-600">No {entityType} found</p>
    </div>
  {:else}
    <Table hoverable={true} striped={true}>
      <TableHead>
        {#each columns as column}
          <TableHeadCell>{getDisplayName(column)}</TableHeadCell>
        {/each}
      </TableHead>
      <TableBody>
        {#each entities as entity}
          <TableBodyRow>
            {#each columns as column}
              <TableBodyCell>
                {formatValue(entity[column], column)}
              </TableBodyCell>
            {/each}
          </TableBodyRow>
        {/each}
        {#if entities.length === 0}
          <TableBodyRow>
            <TableBodyCell colspan={columns.length} class="text-center text-gray-500 dark:text-gray-400">
              No {entityType} found
            </TableBodyCell>
          </TableBodyRow>
        {/if}
      </TableBody>
    </Table>
  {/if}
  {#if pagination}
    <div class="flex justify-center items-center mt-4 space-x-2">
      <Button 
        color="alternative"
        size="sm"
        disabled={!hasPrevPage}
        on:click={() => onPageChange(safePagination.page_num - 1)}
      >
        <ChevronLeftOutline class="w-4 h-4 mr-1" />
        Previous
      </Button>
      
      <span class="text-sm text-gray-700 dark:text-gray-300">
        Page {safePagination.page_num} of {safePagination.total_pages}
        ({safePagination.total_items_count} total items)
      </span>
      
      <Button 
        color="alternative"
        size="sm"
        disabled={!hasNextPage}
        on:click={() => onPageChange(safePagination.page_num + 1)}
      >
        Next
        <ChevronRightOutline class="w-4 h-4 ml-1" />
      </Button>
    </div>
  {/if}
</div> 