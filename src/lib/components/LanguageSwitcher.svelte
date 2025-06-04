<script>
  import { onMount } from 'svelte';
  import { locale, isLoading } from 'svelte-i18n';
  import { supportedLocales, waitLocale } from '$lib/i18n';
  import { browser } from '$app/environment';

  let currentLocale;
  let isReady = false;
  
  // Subscribe to locale changes to update the UI
  locale.subscribe(value => {
    console.log('Locale changed to:', value);
    currentLocale = value;
  });

  onMount(async () => {
    // Wait for i18n to be ready
    if (browser) {
      await waitLocale();
      isReady = true;
      
      // On component mount, check for stored preference
      const storedLocale = localStorage.getItem('preferredLocale');
      if (storedLocale) {
        console.log('Setting locale from localStorage:', storedLocale);
        locale.set(storedLocale);
      }
    }
  });

  function handleLocaleChange(event) {
    const newLocale = event.target.value;
    console.log('Changing locale to:', newLocale);
    locale.set(newLocale);
    
    // Save preference to localStorage
    if (browser) {
      localStorage.setItem('preferredLocale', newLocale);
      console.log('Saved locale preference to localStorage:', newLocale);
      
      // Also set a cookie for server-side rendering
      document.cookie = `locale=${newLocale};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Strict`;
    }
  }
</script>

<div class="language-switcher">
  {#if browser && isReady}
    <select
      value={currentLocale}
      on:change={handleLocaleChange}
      class="bg-transparent border border-gray-300 rounded px-2 py-1 text-sm"
    >
      {#each supportedLocales as loc}
        <option value={loc.id}>{loc.name}</option>
      {/each}
    </select>
  {/if}
</div>

<style>
  .language-switcher {
    display: inline-block;
  }
</style> 