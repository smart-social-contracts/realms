<script>
  import { onDestroy, onMount, tick } from 'svelte';
  import { get } from 'svelte/store';
  import { browser } from '$app/environment';
  import { _ } from 'svelte-i18n';
  import { assistantChrome } from '$lib/assistant-chrome.js';
  import { createRegistryTour, registerTourReplay } from '$lib/registry-tour.js';
  import { isRegistryTourComplete, markRegistryTourComplete } from '$lib/registry-tour-prefs.js';

  export let ready = false;

  /** Bound from parent so the tour can open/close the browse panel. */
  export let panelOpen = false;

  let activeTour = null;
  let autoStarted = false;

  function isMobile() {
    return window.matchMedia('(max-width: 767px)').matches;
  }

  function translate(key) {
    return get(_)(key);
  }

  async function runTour({ markComplete = true } = {}) {
    if (!browser) return;

    activeTour?.destroy();
    activeTour = null;

    panelOpen = false;
    assistantChrome.update((state) => ({ ...state, open: false }));
    await tick();

    const tour = createRegistryTour({
      t: translate,
      isMobile,
      actions: {
        openPanel: async () => {
          panelOpen = true;
          await tick();
        },
        closePanel: async () => {
          panelOpen = false;
          await tick();
        },
        closeAssistant: async () => {
          assistantChrome.update((state) => ({ ...state, open: false }));
          await tick();
        },
      },
      onComplete: () => {
        if (markComplete) markRegistryTourComplete();
        activeTour = null;
      },
    });

    activeTour = tour;
    tour.start();
  }

  onMount(() => {
    registerTourReplay(() => runTour({ markComplete: false }));
  });

  onDestroy(() => {
    activeTour?.destroy();
    registerTourReplay(null);
  });

  $: if (browser && ready && !autoStarted && !isRegistryTourComplete()) {
    autoStarted = true;
    setTimeout(() => runTour({ markComplete: true }), 900);
  }
</script>

<style>
  :global(.registry-tour-popover) {
    font-family: var(--font-family);
    color: var(--text-primary);
  }

  :global(.registry-tour-popover .driver-popover-title) {
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  :global(.registry-tour-popover .driver-popover-description) {
    font-size: 0.8125rem;
    line-height: 1.5;
    color: var(--text-secondary);
  }

  :global(.registry-tour-popover .driver-popover-progress-text) {
    font-size: 0.6875rem;
    color: var(--text-faint);
  }

  :global(.registry-tour-popover button) {
    font-family: var(--font-family);
    font-size: 0.75rem;
    text-shadow: none;
  }

  :global(.driver-active-element) {
    pointer-events: none !important;
  }
</style>
