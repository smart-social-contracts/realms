<script lang="ts">
  import ItemCard from '$lib/components/ItemCard.svelte';
  import Spinner from '$lib/components/Spinner.svelte';
  import { isAuthenticated } from '$lib/auth';
  import { marketplaceClient, type CodexListing } from '$lib/marketplace-client';

  type SortKey = 'newest' | 'installs' | 'likes';

  let items: CodexListing[] = [];
  let total = 0;
  let page = 1;
  let perPage = 24;
  let loading = true;
  let error = '';
  let searchQuery = '';
  let verifiedOnly = false;
  let sortBy: SortKey = 'newest';
  let likedSet = new Set<string>();

  $: void load(page, perPage, verifiedOnly);
  $: void refreshLikes($isAuthenticated);
  $: sorted = applySort(items, sortBy);

  function applySort(list: CodexListing[], key: SortKey): CodexListing[] {
    const copy = [...list];
    if (key === 'installs') {
      copy.sort((a, b) => b.installs - a.installs || b.likes - a.likes);
    } else if (key === 'likes') {
      copy.sort((a, b) => b.likes - a.likes || b.installs - a.installs);
    } else {
      copy.sort((a, b) => b.updated_at - a.updated_at);
    }
    return copy;
  }

  async function refreshLikes(_authed: boolean) {
    if (!_authed) {
      likedSet = new Set();
      return;
    }
    try {
      const my = await marketplaceClient.myLikes();
      likedSet = new Set(my.filter((m) => m.item_kind === 'codex').map((m) => `codex|${m.item_id}`));
    } catch {
      likedSet = new Set();
    }
  }

  async function load(p: number, pp: number, v: boolean) {
    loading = true;
    error = '';
    try {
      if (searchQuery.trim()) {
        items = await marketplaceClient.searchCodices(searchQuery.trim(), v);
        total = items.length;
      } else {
        const r = await marketplaceClient.listCodices(p, pp, v);
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
  <h1>Codices</h1>
  <p>Governance frameworks and rule packages for realm types — Dominion, Agora, Syntropia and beyond.</p>
</header>

<div class="controls">
  <input
    type="search"
    placeholder="Search codices…"
    bind:value={searchQuery}
    on:keydown={(e) => e.key === 'Enter' && doSearch()}
  />
  <button class="btn" on:click={doSearch}>Search</button>
  <label class="sort">
    Sort
    <select bind:value={sortBy}>
      <option value="newest">Newest</option>
      <option value="installs">Most installs</option>
      <option value="likes">Most likes</option>
    </select>
  </label>
  <label class="verified-toggle">
    <input type="checkbox" bind:checked={verifiedOnly} />
    Verified only
  </label>
</div>

{#if loading}
  <div class="state"><Spinner /></div>
{:else if error}
  <div class="state error">⚠️ {error}</div>
{:else if sorted.length === 0}
  <div class="state empty">
    <p>No codices found. <a href="/upload">Upload one →</a></p>
  </div>
{:else}
  <div class="grid">
    {#each sorted as c}
      <ItemCard
        kind="codex"
        id={c.codex_id}
        name={c.name}
        description={c.description}
        version={c.version}
        developer={c.developer}
        icon={c.icon}
        priceE8s={c.price_e8s}
        installs={c.installs}
        likes={c.likes}
        categoriesStr={c.categories}
        verificationStatus={c.verification_status}
        liked={likedSet.has(`codex|${c.codex_id}`)}
        href={`/codices/${encodeURIComponent(c.codex_id)}`}
      />
    {/each}
  </div>
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); }
  .controls { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin-bottom: 1.25rem; }
  input[type='search'] {
    flex: 1; min-width: 240px;
    padding: 0.7rem 0.9rem; border: 1px solid var(--border);
    border-radius: 0.5rem; background: var(--surface); font-size: 0.95rem;
  }
  .verified-toggle { display: inline-flex; align-items: center; gap: 0.35rem; color: var(--text-muted); font-size: 0.85rem; }
  .sort { display: inline-flex; align-items: center; gap: 0.35rem; color: var(--text-muted); font-size: 0.85rem; }
  .sort select {
    border: 1px solid var(--border); background: var(--surface);
    border-radius: 0.4rem; padding: 0.35rem 0.5rem; font: inherit; color: var(--text);
  }
  .btn { background: var(--primary); color: #fff; border: 1px solid var(--primary); padding: 0.7rem 1rem; border-radius: 0.5rem; }
  .btn:hover { background: var(--primary-hover); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 1.25rem; }
  .state { text-align: center; padding: 3rem; color: var(--text-muted); }
  .state.error { color: var(--danger); }
</style>
