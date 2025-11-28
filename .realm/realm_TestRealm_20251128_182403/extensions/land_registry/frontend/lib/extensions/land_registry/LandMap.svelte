<script>
  import { createEventDispatcher } from 'svelte';
  
  export let lands = [];
  
  const dispatch = createEventDispatcher();
  
  const GRID_SIZE = 20;
  const CELL_SIZE = 30;
  
  const LAND_COLORS = {
    'residential': '#4ade80',
    'agricultural': '#fbbf24',
    'industrial': '#6b7280',
    'commercial': '#3b82f6',
    'unassigned': '#f3f4f6'
  };
  
  $: gridData = createGridData(lands);
  
  function createGridData(lands) {
    const grid = {};
    
    for (let x = 0; x < GRID_SIZE; x++) {
      for (let y = 0; y < GRID_SIZE; y++) {
        grid[`${x},${y}`] = {
          x, y,
          type: 'unassigned',
          owner: null,
          id: null
        };
      }
    }
    
    lands.forEach(land => {
      const key = `${land.x_coordinate},${land.y_coordinate}`;
      if (grid[key]) {
        grid[key] = {
          x: land.x_coordinate,
          y: land.y_coordinate,
          type: land.land_type,
          owner: land.owner_user_id || land.owner_organization_id,
          id: land.id
        };
      }
    });
    
    return grid;
  }
  
  function handleCellClick(cell) {
    console.log('Cell clicked:', cell);
  }
</script>

<div class="land-map">
  <div class="mb-4">
    <h3 class="text-lg font-semibold mb-2">Land Ownership Map</h3>
    <div class="flex flex-wrap gap-4 text-sm">
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 rounded" style="background-color: {LAND_COLORS.residential}"></div>
        <span>Residential</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 rounded" style="background-color: {LAND_COLORS.agricultural}"></div>
        <span>Agricultural</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 rounded" style="background-color: {LAND_COLORS.industrial}"></div>
        <span>Industrial</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 rounded" style="background-color: {LAND_COLORS.commercial}"></div>
        <span>Commercial</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 rounded" style="background-color: {LAND_COLORS.unassigned}"></div>
        <span>Unassigned</span>
      </div>
    </div>
  </div>
  
  <div class="grid-container border border-gray-300 inline-block">
    <div 
      class="grid gap-0" 
      style="grid-template-columns: repeat({GRID_SIZE}, {CELL_SIZE}px); grid-template-rows: repeat({GRID_SIZE}, {CELL_SIZE}px);"
    >
      {#each Object.values(gridData) as cell}
        <div
          class="border border-gray-200 cursor-pointer hover:opacity-80 flex items-center justify-center text-xs"
          style="background-color: {LAND_COLORS[cell.type]}; width: {CELL_SIZE}px; height: {CELL_SIZE}px;"
          on:click={() => handleCellClick(cell)}
          title="({cell.x},{cell.y}) - {cell.type} {cell.owner ? '- Owned' : ''}"
        >
          {#if cell.owner}
            <span class="text-white font-bold">●</span>
          {/if}
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .grid-container {
    overflow: auto;
    max-width: 100%;
  }
</style>
