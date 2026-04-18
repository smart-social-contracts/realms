<script lang="ts">
  import VerifiedBadge from './VerifiedBadge.svelte';
  import LikeButton from './LikeButton.svelte';
  import RankBadge from './RankBadge.svelte';
  import { categories, formatCount, formatPrice, shortPrincipal } from '$lib/format';

  export let kind: 'ext' | 'codex';
  export let id: string;
  export let name: string;
  export let description: string;
  export let version: string;
  export let developer: string;
  export let icon: string = '';
  export let priceE8s: number = 0;
  export let installs: number = 0;
  export let likes: number = 0;
  export let categoriesStr: string = '';
  export let verificationStatus: string = 'unverified';
  export let liked: boolean = false;
  export let rank: number | null = null;
  export let href: string;
</script>

<a class="card" {href}>
  <div class="row top">
    {#if rank != null}
      <RankBadge {rank} />
    {/if}
    <div class="icon">{icon || (kind === 'codex' ? '📜' : '🧩')}</div>
    <div class="title-block">
      <div class="title-line">
        <h3>{name}</h3>
        <VerifiedBadge status={verificationStatus} />
      </div>
      <p class="meta">v{version} · {shortPrincipal(developer)}</p>
    </div>
    <div class="price-badge" class:free={priceE8s === 0}>{formatPrice(priceE8s)}</div>
  </div>

  <p class="description">{description}</p>

  {#if categoriesStr}
    <div class="categories">
      {#each categories(categoriesStr) as c}
        <span class="cat">{c.replace(/_/g, ' ')}</span>
      {/each}
    </div>
  {/if}

  <div class="row footer">
    <span class="stat" title="Installs">⬇ {formatCount(installs)}</span>
    <LikeButton {kind} itemId={id} {liked} count={likes} />
  </div>
</a>

<style>
  .card {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    text-decoration: none;
    color: inherit;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.85rem;
    padding: 1.1rem 1.2rem;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }
  .card:hover {
    border-color: var(--border-strong);
    transform: translateY(-1px);
    box-shadow: 0 8px 22px -10px rgba(0, 0, 0, 0.18);
  }
  .row { display: flex; align-items: center; gap: 0.75rem; }
  .row.top { align-items: flex-start; }
  .icon {
    width: 44px; height: 44px;
    border-radius: 0.6rem;
    background: var(--surface-2);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; flex-shrink: 0;
  }
  .title-block { flex: 1; min-width: 0; }
  .title-line { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  h3 { margin: 0; font-size: 1rem; font-weight: 600; color: var(--text); }
  .meta { margin: 2px 0 0; font-size: 0.75rem; color: var(--text-faint); font-family: monospace; }
  .price-badge {
    background: var(--surface-2); color: var(--text-muted);
    padding: 0.3rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
    flex-shrink: 0; align-self: center;
  }
  .price-badge.free { background: var(--verified-bg); color: var(--verified); }
  .description {
    margin: 0; font-size: 0.85rem; color: var(--text-muted); line-height: 1.55;
    display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden;
  }
  .categories { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .cat {
    background: var(--surface-2); color: var(--text-muted);
    padding: 0.15rem 0.55rem; border-radius: 0.35rem;
    font-size: 0.7rem; text-transform: capitalize;
  }
  .footer { justify-content: space-between; padding-top: 0.5rem; border-top: 1px solid var(--surface-2); }
  .stat { color: var(--text-faint); font-size: 0.8rem; font-family: monospace; }
</style>
