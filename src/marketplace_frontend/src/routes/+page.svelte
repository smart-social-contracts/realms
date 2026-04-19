<script lang="ts">
  import { onMount } from 'svelte';
  import ItemCard from '$lib/components/ItemCard.svelte';
  import Spinner from '$lib/components/Spinner.svelte';
  import {
    marketplaceClient,
    type AssistantListing,
    type CodexListing,
    type ExtensionListing,
  } from '$lib/marketplace-client';
  import { isAuthenticated, principalStore } from '$lib/auth';

  type Kind = 'ext' | 'codex' | 'assistant';
  type Metric = 'downloads' | 'likes';

  let kind: Kind = 'ext';
  let metric: Metric = 'downloads';
  let verifiedOnly = false;
  let loading = true;
  let error = '';
  let items: (ExtensionListing | CodexListing | AssistantListing)[] = [];
  let likedSet = new Set<string>();

  $: void load(kind, metric, verifiedOnly);

  // When auth state changes, refresh "my likes" so the heart shows correctly.
  $: void refreshLikes($isAuthenticated, $principalStore?.toText());

  async function refreshLikes(_authed: boolean, _principal: string | undefined) {
    if (!_authed) {
      likedSet = new Set();
      return;
    }
    try {
      const my = await marketplaceClient.myLikes();
      likedSet = new Set(my.map((m) => `${m.item_kind}|${m.item_id}`));
    } catch {
      likedSet = new Set();
    }
  }

  async function load(k: Kind, m: Metric, v: boolean) {
    loading = true;
    error = '';
    try {
      if (k === 'ext') {
        items = m === 'downloads'
          ? await marketplaceClient.topExtensionsByDownloads(20, v)
          : await marketplaceClient.topExtensionsByLikes(20, v);
      } else if (k === 'codex') {
        items = m === 'downloads'
          ? await marketplaceClient.topCodicesByDownloads(20, v)
          : await marketplaceClient.topCodicesByLikes(20, v);
      } else {
        items = m === 'downloads'
          ? await marketplaceClient.topAssistantsByDownloads(20, v)
          : await marketplaceClient.topAssistantsByLikes(20, v);
      }
    } catch (e: any) {
      error = e?.message ?? String(e);
      items = [];
    } finally {
      loading = false;
    }
  }

  function idOf(it: ExtensionListing | CodexListing | AssistantListing): string {
    return (it as any).extension_id ?? (it as any).codex_id ?? (it as any).assistant_id ?? '';
  }

  function hrefOf(k: Kind, it: ExtensionListing | CodexListing | AssistantListing): string {
    if (k === 'ext') return `/extensions/${encodeURIComponent(idOf(it))}`;
    if (k === 'codex') return `/codices/${encodeURIComponent(idOf(it))}`;
    return `/assistants/${encodeURIComponent(idOf(it))}`;
  }

  function defaultIcon(k: Kind): string {
    if (k === 'codex') return '📜';
    if (k === 'assistant') return '🤖';
    return '🧩';
  }

  function categoriesFor(it: ExtensionListing | CodexListing | AssistantListing): string {
    if (it.categories) return it.categories;
    if ((it as AssistantListing).domains) return (it as AssistantListing).domains;
    return '';
  }
</script>

<section class="hero">
  <h1>Top Charts</h1>
  <p>Discover the most popular extensions, codices, and AI assistants powering Realms.</p>
</section>

<div class="controls">
  <div class="toggle">
    <button class:active={kind === 'ext'} on:click={() => (kind = 'ext')}>Extensions</button>
    <button class:active={kind === 'codex'} on:click={() => (kind = 'codex')}>Codices</button>
    <button class:active={kind === 'assistant'} on:click={() => (kind = 'assistant')}>Assistants</button>
  </div>
  <div class="toggle">
    <button class:active={metric === 'downloads'} on:click={() => (metric = 'downloads')}>Most Downloaded</button>
    <button class:active={metric === 'likes'} on:click={() => (metric = 'likes')}>Most Liked</button>
  </div>
  <label class="verified-toggle">
    <input type="checkbox" bind:checked={verifiedOnly} />
    <span>Verified only</span>
  </label>
</div>

{#if loading}
  <div class="state"><Spinner size={32} /><p>Loading…</p></div>
{:else if error}
  <div class="state error"><p>⚠️ {error}</p></div>
{:else if items.length === 0}
  <div class="state empty">
    <h2>Nothing here yet</h2>
    <p>Be the first to <a href="/upload">upload {kind === 'ext' ? 'an extension' : 'a codex'}</a>.</p>
  </div>
{:else}
  <div class="grid">
    {#each items as it, i}
      <ItemCard
        kind={kind}
        id={idOf(it)}
        name={it.name}
        description={it.description}
        version={it.version}
        developer={it.developer}
        icon={it.icon || defaultIcon(kind)}
        priceE8s={it.price_e8s}
        installs={it.installs}
        likes={it.likes}
        categoriesStr={categoriesFor(it)}
        verificationStatus={it.verification_status}
        liked={likedSet.has(`${kind}|${idOf(it)}`)}
        rank={i + 1}
        href={hrefOf(kind, it)}
      />
    {/each}
  </div>
{/if}

<style>
  .hero h1 { font-size: 2rem; margin: 0 0 0.5rem; }
  .hero p { color: var(--text-muted); margin: 0 0 2rem; }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 2rem;
    align-items: center;
  }
  .toggle {
    display: inline-flex;
    background: var(--surface-2);
    border-radius: 0.5rem;
    padding: 0.2rem;
    gap: 0.2rem;
  }
  .toggle button {
    background: transparent;
    border: none;
    padding: 0.5rem 0.95rem;
    border-radius: 0.4rem;
    font-size: 0.85rem;
    color: var(--text-faint);
    transition: all 0.15s ease;
  }
  .toggle button:hover { color: var(--text); }
  .toggle button.active {
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  }
  .verified-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
    gap: 1.25rem;
  }
  .state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
  }
  .state.error { color: var(--danger); }
  .state.empty h2 { margin: 0 0 0.5rem; color: var(--text); }
</style>
