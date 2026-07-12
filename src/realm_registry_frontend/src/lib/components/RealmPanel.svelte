<script>
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import RealmCard from './RealmCard.svelte';

  export let open = false;
  export let realms = [];
  export let selectedRealmId = null;
  export let filterStage = '';
  export let sortBy = 'users_desc';
  export let searchQuery = '';

  const dispatch = createEventDispatcher();

  let panelEl;
  let listEl;

  $: if (open && selectedRealmId) {
    scrollToSelected();
  }

  async function scrollToSelected() {
    await tick();
    if (!listEl || !selectedRealmId) return;
    const card = listEl.querySelector(`[data-realm-id="${selectedRealmId}"]`);
    card?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function handleKeydown(e) {
    if (e.key === 'Escape' && open) {
      dispatch('close');
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

{#if open}
  <button class="panel-backdrop" aria-label="Close panel" on:click={() => dispatch('close')}></button>
{/if}

<aside
  class="realm-panel"
  class:open
  bind:this={panelEl}
  aria-hidden={!open}
  role="complementary"
  aria-label={$_('globe.browse_realms')}
>
  <div class="panel-header">
    <h2 class="panel-title">{$_('globe.browse_realms')}</h2>
    <button class="close-btn" on:click={() => dispatch('close')} aria-label="Close">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 6L6 18M6 6l12 12"></path>
      </svg>
    </button>
  </div>

  <div class="panel-filters">
    <select class="filter-select" bind:value={filterStage} on:change={() => dispatch('filter')}>
      <option value="">{$_('globe.filter_all_stages')}</option>
      <option value="alpha">Alpha</option>
      <option value="beta">Beta</option>
      <option value="production">Live</option>
      <option value="deprecation">Winding Down</option>
      <option value="terminated">Archived</option>
    </select>

    <select class="filter-select" bind:value={sortBy} on:change={() => dispatch('filter')}>
      <option value="users_desc">{$_('globe.sort_users_desc')}</option>
      <option value="name">{$_('globe.sort_name')}</option>
      <option value="users_asc">{$_('globe.sort_users_asc')}</option>
      <option value="newest">{$_('globe.sort_newest')}</option>
    </select>
  </div>

  <div class="panel-list" bind:this={listEl}>
    {#if realms.length === 0}
      <div class="empty-panel">
        {#if searchQuery}
          <p>{$_('search.no_results_message', { values: { query: searchQuery } })}</p>
        {:else}
          <p>{$_('empty.message')}</p>
        {/if}
      </div>
    {:else}
      {#each realms as realm (realm.id)}
        <div data-realm-id={realm.id} class="card-wrapper">
          <RealmCard
            {realm}
            selected={selectedRealmId === realm.id}
            on:select={(e) => dispatch('select', e.detail)}
            on:manifesto={(e) => dispatch('manifesto', e.detail)}
          />
        </div>
      {/each}
    {/if}
  </div>
</aside>

<style>
  .panel-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 150;
    background: transparent;
    border: none;
    cursor: default;
  }

  .realm-panel {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--panel-width);
    z-index: 160;
    display: flex;
    flex-direction: column;
    background: var(--surface);
    border-right: 1px solid var(--border);
    box-shadow: 4px 0 16px rgba(0, 0, 0, 0.06);
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    font-family: var(--font-family);
  }

  .realm-panel.open {
    transform: translateX(0);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.875rem 1rem;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .panel-title {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .close-btn:hover {
    background: var(--surface-2);
  }

  .panel-filters {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .filter-select {
    flex: 1;
    height: 32px;
    padding: 0 0.5rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text-secondary);
    font-size: 0.75rem;
    font-family: inherit;
    outline: none;
  }

  .panel-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .card-wrapper {
    flex-shrink: 0;
  }

  .empty-panel {
    padding: 2rem 1rem;
    text-align: center;
    color: var(--text-tertiary);
    font-size: 0.875rem;
  }

  @media (max-width: 767px) {
    .panel-backdrop {
      display: block;
    }

    .realm-panel {
      top: auto;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      max-height: 70vh;
      border-left: none;
      border-top: 1px solid var(--border);
      border-radius: 16px 16px 0 0;
      transform: translateY(100%);
      box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.08);
    }

    .realm-panel.open {
      transform: translateY(0);
    }
  }
</style>
