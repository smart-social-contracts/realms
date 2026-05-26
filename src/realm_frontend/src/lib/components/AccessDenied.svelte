<script>
  export let operation = '';
</script>

<div class="flex items-start gap-3 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4 dark:border-gray-700 dark:bg-gray-800/50">
  <svg class="mt-0.5 h-5 w-5 flex-shrink-0 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
  </svg>
  <div>
    <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">Additional permissions needed</h3>
    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">You need additional permissions to view this page.</p>
    {#if operation}
      <p class="mt-2 text-xs text-gray-400 dark:text-gray-500 font-mono">{operation}</p>
    {/if}
  </div>
</div>
