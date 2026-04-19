<script lang="ts">
  import ItemCard from '$lib/components/ItemCard.svelte';
  import Spinner from '$lib/components/Spinner.svelte';
  import { isAuthenticated } from '$lib/auth';
  import { marketplaceClient, type AssistantListing } from '$lib/marketplace-client';
  import { categories } from '$lib/format';

  type SortKey = 'newest' | 'installs' | 'likes';

  let items: AssistantListing[] = [];
  let total = 0;
  let page = 1;
  let perPage = 24;
  let loading = true;
  let error = '';
  let searchQuery = '';
  let verifiedOnly = false;
  let sortBy: SortKey = 'newest';
  let domainFilter = '';
  let likedSet = new Set<string>();

  $: void load(page, perPage, verifiedOnly);
  $: void refreshLikes($isAuthenticated);
  $: filtered = applyDomainFilter(items, domainFilter);
  $: sorted = applySort(filtered, sortBy);
  $: knownDomains = collectDomains(items);

  function collectDomains(list: AssistantListing[]): string[] {
    const set = new Set<string>();
    for (const a of list) {
      for (const d of categories(a.domains)) set.add(d);
    }
    return Array.from(set).sort();
  }

  function applyDomainFilter(list: AssistantListing[], dom: string): AssistantListing[] {
    if (!dom) return list;
    const needle = dom.toLowerCase();
    return list.filter((a) => categories(a.domains).map((d) => d.toLowerCase()).includes(needle));
  }

  function applySort(list: AssistantListing[], key: SortKey): AssistantListing[] {
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
      likedSet = new Set(my.filter((m) => m.item_kind === 'assistant').map((m) => `assistant|${m.item_id}`));
    } catch {
      likedSet = new Set();
    }
  }

  async function load(p: number, pp: number, v: boolean) {
    loading = true;
    error = '';
    try {
      if (searchQuery.trim()) {
        items = await marketplaceClient.searchAssistants(searchQuery.trim(), v);
        total = items.length;
      } else {
        const r = await marketplaceClient.listAssistants(p, pp, v);
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
  <h1>AI Assistants</h1>
  <p>
    Realm-hireable AI agents — governance experts, codex auditors, proposal drafters.
    Realms hire them via a normal governance vote; once approved they run autonomously
    inside the realm with the role and permissions they declare.
  </p>
</header>

<div class="controls">
  <input
    type="search"
    placeholder="Search assistants…"
    bind:value={searchQuery}
    on:keydown={(e) => e.key === 'Enter' && doSearch()}
  />
  <button class="btn" on:click={doSearch}>Search</button>
  <label class="sort">
    Domain
    <select bind:value={domainFilter}>
      <option value="">All</option>
      {#each knownDomains as d}
        <option value={d}>{d.replace(/_/g, ' ')}</option>
      {/each}
    </select>
  </label>
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
    <p>No assistants found. <a href="/upload">Publish one →</a></p>
  </div>
{:else}
  <div class="grid">
    {#each sorted as a}
      <ItemCard
        kind="assistant"
        id={a.assistant_id}
        name={a.name}
        description={a.description}
        version={a.version}
        developer={a.developer}
        icon={a.icon || '🤖'}
        priceE8s={a.price_e8s}
        installs={a.installs}
        likes={a.likes}
        categoriesStr={a.categories || a.domains}
        verificationStatus={a.verification_status}
        liked={likedSet.has(`assistant|${a.assistant_id}`)}
        href={`/assistants/${encodeURIComponent(a.assistant_id)}`}
      />
    {/each}
  </div>
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); max-width: 70ch; }
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
