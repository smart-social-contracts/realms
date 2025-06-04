<script>
  import { onMount } from 'svelte';
  import { locale } from 'svelte-i18n';
  import { supportedLocales } from '$lib/i18n';

  let currentLocale;
  
  // Subscribe to locale changes to update the UI
  locale.subscribe(value => {
    console.log('Locale changed to:', value);
    currentLocale = value;
  });

  onMount(() => {
    // On component mount, check for stored preference
    if (typeof localStorage !== 'undefined') {
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
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('preferredLocale', newLocale);
      console.log('Saved locale preference to localStorage:', newLocale);
    }
    
    // Also set a cookie for server-side rendering
    document.cookie = `locale=${newLocale};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Strict`;
  }
</script>

<div class="language-switcher">
  <select
    value={currentLocale}
    on:change={handleLocaleChange}
    class="bg-transparent border border-gray-300 rounded px-2 py-1 text-sm"
  >
    {#each supportedLocales as loc}
      <option value={loc.id}>{loc.name}</option>
    {/each}
  </select>
</div>

<style>
  .language-switcher {
    display: inline-block;
  }
</style> 