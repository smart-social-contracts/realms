<script lang="ts">
  import { onMount } from 'svelte';
  import ItemCard from '$lib/components/ItemCard.svelte';
  import Spinner from '$lib/components/Spinner.svelte';
  import { isAuthenticated } from '$lib/auth';
  import { marketplaceClient, type ExtensionListing } from '$lib/marketplace-client';

  let items: ExtensionListing[] = [];
  let total = 0;
  let page = 1;
  let perPage = 24;
  let loading = true;
  let error = '';
  let searchQuery = '';
  let verifiedOnly = false;
  let likedSet = new Set<string>();

  $: void load(page, perPage, verifiedOnly);
  $: void refreshLikes($isAuthenticated);

  async function refreshLikes(_authed: boolean) {
    if (!_authed) {
      likedSet = new Set();
      return;
    }
    try {
      const my = await marketplaceClient.myLikes();
      likedSet = new Set(my.filter((m) => m.item_kind === 'ext').map((m) => `ext|${m.item_id}`));
    } catch {
      likedSet = new Set();
    }
  }

  async function load(p: number, pp: number, v: boolean) {
    loading = true;
    error = '';
    try {
      if (searchQuery.trim()) {
        items = await marketplaceClient.searchExtensions(searchQuery.trim(), v);
        total = items.length;
      } else {
        const r = await marketplaceClient.listExtensions(p, pp, v);
        items = r.listings;
        total = r.total_count;
      }
    } catch (e: any) {
      error = e?.message ?? String(e);
      items = [];
      total = 0;
    } finally {
      loading = false;
    }
  }

  function doSearch() {
    page = 1;
    load(page, perPage, verifiedOnly);
  }
</script>

<header class="head">
  <h1>Extensions</h1>
  <p>Plug-and-play features that any realm can install via the package manager.</p>
</header>

<div class="controls">
  <input
    type="search"
    placeholder="Search extensions…"
    bind:value={searchQuery}
    on:keydown={(e) => e.key === 'Enter' && doSearch()}
  />
  <button class="btn" on:click={doSearch}>Search</button>
  <label class="verified-toggle">
    <input type="checkbox" bind:checked={verifiedOnly} />
    Verified only
  </label>
</div>

{#if loading}
  <div class="state"><Spinner /></div>
{:else if error}
  <div class="state error">⚠️ {error}</div>
{:else if items.length === 0}
  <div class="state empty">
    <p>No extensions found. <a href="/upload">Upload one →</a></p>
  </div>
{:else}
  <div class="grid">
    {#each items as ext}
      <ItemCard
        kind="ext"
        id={ext.extension_id}
        name={ext.name}
        description={ext.description}
        version={ext.version}
        developer={ext.developer}
        icon={ext.icon}
        priceE8s={ext.price_e8s}
        installs={ext.installs}
        likes={ext.likes}
        categoriesStr={ext.categories}
        verificationStatus={ext.verification_status}
        liked={likedSet.has(`ext|${ext.extension_id}`)}
        href={`/extensions/${encodeURIComponent(ext.extension_id)}`}
      />
    {/each}
  </div>

  {#if !searchQuery && total > perPage}
    <div class="pager">
      <button disabled={page <= 1} on:click={() => (page = Math.max(1, page - 1))}>← Prev</button>
      <span>Page {page} of {Math.max(1, Math.ceil(total / perPage))}</span>
      <button
        disabled={page * perPage >= total}
        on:click={() => (page = page + 1)}
      >Next →</button>
    </div>
  {/if}
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); }
  .controls {
    display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin-bottom: 1.25rem;
  }
  input[type='search'] {
    flex: 1; min-width: 240px;
    padding: 0.7rem 0.9rem; border: 1px solid var(--border);
    border-radius: 0.5rem; background: var(--surface); font-size: 0.95rem;
  }
  .verified-toggle { display: inline-flex; align-items: center; gap: 0.35rem; color: var(--text-muted); font-size: 0.85rem; }
  .btn {
    background: var(--primary); color: #fff; border: 1px solid var(--primary);
    padding: 0.7rem 1rem; border-radius: 0.5rem;
  }
  .btn:hover { background: var(--primary-hover); }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
    gap: 1.25rem;
  }
  .state { text-align: center; padding: 3rem; color: var(--text-muted); }
  .state.error { color: var(--danger); }
  .pager {
    display: flex; gap: 1rem; align-items: center; justify-content: center; padding: 2rem 0;
  }
  .pager button {
    background: var(--surface); border: 1px solid var(--border); padding: 0.5rem 1rem; border-radius: 0.4rem;
  }
  .pager button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
