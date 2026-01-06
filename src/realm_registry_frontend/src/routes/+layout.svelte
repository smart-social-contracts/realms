<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { initI18n } from '$lib/i18n';
  import '../index.scss';

  // Flag to track if i18n is ready
  let i18nReady = false;

  onMount(async () => {
    // Initialize i18n and wait for translations to load
    await initI18n();
    i18nReady = true;
  });
</script>

{#if browser && i18nReady}
  <slot />
{:else}
  <div class="loading-screen">
    <div class="spinner"></div>
  </div>
{/if}

<style>
  .loading-screen {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: #FAFAFA;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #F5F5F5;
    border-top: 4px solid #525252;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style>
