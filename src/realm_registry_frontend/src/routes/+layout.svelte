<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { initI18n } from '$lib/i18n';
  import RegistryAssistant from '$lib/components/RegistryAssistant.svelte';
  import { assistantChrome } from '$lib/assistant-chrome.js';
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
  <div
    class="app-shell"
    class:assistant-docked={$assistantChrome.open && $assistantChrome.docked}
    class:assistant-resizing={$assistantChrome.resizing}
    style="--assistant-width: {$assistantChrome.width}px"
  >
    <slot />
  </div>
  <!-- Mundus-level AI assistant (float/dock); see issue #233. -->
  <RegistryAssistant />
{:else}
  <div class="loading-screen">
    <div class="spinner"></div>
  </div>
{/if}

<style>
  .app-shell {
    min-height: 100vh;
    transition: padding-right 0.25s ease;
  }
  .app-shell.assistant-docked {
    padding-right: var(--assistant-width);
  }
  .app-shell.assistant-docked.assistant-resizing {
    transition: none;
  }
  /* Narrow: docked panel is a full-width overlay — don't pad the shell. */
  @media (max-width: 767px) {
    .app-shell.assistant-docked {
      padding-right: 0;
    }
  }

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
