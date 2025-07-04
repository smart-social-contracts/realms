<!-- Minimal layout that bypasses all app dependencies -->
<script>
  // No imports, no dependencies - pure standalone UI development
  console.log('=== STANDALONE DEV LAYOUT LOADED ===');
</script>

<slot />

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
</style>
