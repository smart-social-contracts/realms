<script>
  import { _ } from 'svelte-i18n';
  import { locale } from 'svelte-i18n';
  import { supportedLocales } from '$lib/i18n';
  import T from '$lib/components/T.svelte';
  import { onMount } from 'svelte';
  
  let availableLocales = supportedLocales;
  let currentLocale = '';
  let dictionaries = {};
  
  // Subscribe to locale changes
  locale.subscribe(value => {
    currentLocale = value;
    console.log('Debug page: Current locale is', value);
  });
  
  // Function to manually change locale
  function setLocale(loc) {
    console.log('Debug page: Setting locale to', loc);
    locale.set(loc);
  }
  
  // Function to dump current translations
  function dumpTranslations() {
    try {
      // Access internal state to show in debug view
      const dictionaryValue = $_;
      dictionaries = JSON.stringify(dictionaryValue, null, 2);
      console.log('Dictionaries:', dictionaries);
    } catch (err) {
      console.error('Error dumping translations:', err);
    }
  }
  
  onMount(() => {
    dumpTranslations();
  });
</script>

<svelte:head>
  <title>i18n Debug</title>
</svelte:head>

<div class="container mx-auto p-8">
  <h1 class="text-3xl font-bold mb-6">i18n Debug Page</h1>
  
  <div class="bg-white p-6 rounded-lg shadow-md mb-8">
    <h2 class="text-xl font-semibold mb-4">Current Settings</h2>
    <p><strong>Current Locale:</strong> {currentLocale || 'none'}</p>
    <p><strong>Available Locales:</strong> {availableLocales.map(l => l.id).join(', ')}</p>
    
    <div class="mt-4">
      <h3 class="text-lg font-medium mb-2">Locale Selector</h3>
      <div class="flex space-x-2">
        {#each availableLocales as loc}
          <button 
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            on:click={() => setLocale(loc.id)}
          >
            Switch to {loc.name}
          </button>
        {/each}
      </div>
    </div>
  </div>
  
  <div class="bg-white p-6 rounded-lg shadow-md mb-8">
    <h2 class="text-xl font-semibold mb-4">Translation Examples</h2>
    
    <div class="grid grid-cols-2 gap-4">
      <div class="border p-4 rounded">
        <h3 class="font-medium mb-2">Using T Component</h3>
        <p><T key="common.welcome" /></p>
        <p><T key="common.loading" /></p>
        <p><T key="common.error" /></p>
      </div>
      
      <div class="border p-4 rounded">
        <h3 class="font-medium mb-2">Using $_ Store</h3>
        <p>{$_('common.welcome')}</p>
        <p>{$_('common.loading')}</p>
        <p>{$_('common.error')}</p>
      </div>
    </div>
    
    <button 
      class="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
      on:click={dumpTranslations}
    >
      Refresh Translation Data
    </button>
  </div>
  
  <div class="bg-gray-100 p-6 rounded-lg">
    <h2 class="text-xl font-semibold mb-4">Translation Dictionary</h2>
    <pre class="bg-gray-800 text-gray-100 p-4 rounded overflow-x-auto">{dictionaries}</pre>
  </div>
</div> 