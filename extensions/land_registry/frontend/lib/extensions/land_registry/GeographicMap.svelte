<script>
  import { createEventDispatcher } from 'svelte';
  import Map from '../../../routes/utils/widgets/Map.svelte';
  import { landsToGeoJSON, LAND_COLORS } from './coordinateUtils.js';
  
  export let lands = [];
  
  const dispatch = createEventDispatcher();
  
  $: geoJsonData = landsToGeoJSON(lands);
  
  function handleMapClick(event) {
    console.log('Map clicked:', event);
  }
</script>

<div class="geographic-map">
  <div class="mb-4">
    <h3 class="text-lg font-semibold mb-2">Geographic Land Registry</h3>
    <p class="text-sm text-gray-600 mb-2">
      Land parcels mapped to Central Park NYC area for demonstration
    </p>
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
  
  {#if geoJsonData && geoJsonData.features.length > 0}
    <Map geometry={geoJsonData} />
  {:else}
    <div class="h-[400px] w-full rounded-lg border border-gray-300 flex items-center justify-center text-gray-500">
      No land parcels to display on map
    </div>
  {/if}
</div>
