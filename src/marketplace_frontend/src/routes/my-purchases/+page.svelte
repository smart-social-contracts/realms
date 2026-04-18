<script lang="ts">
  import Spinner from '$lib/components/Spinner.svelte';
  import { isAuthenticated } from '$lib/auth';
  import { marketplaceClient, type PurchaseRecord } from '$lib/marketplace-client';
  import { formatTimeAgo, formatPrice } from '$lib/format';

  let loading = false;
  let error = '';
  let purchases: PurchaseRecord[] = [];

  $: void load($isAuthenticated);

  async function load(_authed: boolean) {
    if (!_authed) {
      purchases = [];
      return;
    }
    loading = true;
    error = '';
    try {
      purchases = await marketplaceClient.getMyPurchases();
    } catch (e: any) {
      error = e?.message ?? String(e);
      purchases = [];
    } finally {
      loading = false;
    }
  }

  function hrefFor(p: PurchaseRecord): string {
    if (p.item_kind === 'codex') return `/codices/${encodeURIComponent(p.item_id)}`;
    return `/extensions/${encodeURIComponent(p.item_id)}`;
  }
</script>

<header class="head">
  <h1>My Purchases</h1>
  <p>Everything you've installed via this marketplace.</p>
</header>

{#if !$isAuthenticated}
  <div class="card warn">
    <h2>Sign in to view your purchases</h2>
  </div>
{:else if loading}
  <div class="state"><Spinner /></div>
{:else if error}
  <div class="state error">⚠️ {error}</div>
{:else if purchases.length === 0}
  <div class="state empty">
    <p>No purchases yet. Browse <a href="/extensions">extensions</a> or <a href="/codices">codices</a>.</p>
  </div>
{:else}
  <table class="purchases">
    <thead><tr><th>Item</th><th>Kind</th><th>Price paid</th><th>When</th><th></th></tr></thead>
    <tbody>
      {#each purchases as p}
        <tr>
          <td><code>{p.item_id}</code></td>
          <td>{p.item_kind === 'codex' ? '📜 codex' : '🧩 extension'}</td>
          <td>{formatPrice(p.price_paid_e8s)}</td>
          <td>{formatTimeAgo(p.purchased_at)}</td>
          <td><a class="link" href={hrefFor(p)}>View →</a></td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); }
  .card { background: var(--surface); border: 1px solid var(--border); padding: 2rem; border-radius: 0.75rem; text-align: center; }
  .card.warn { border-color: var(--warning); background: #FEF3C7; color: #92400E; }
  .state { text-align: center; padding: 3rem; color: var(--text-muted); }
  .state.error { color: var(--danger); }
  .purchases { width: 100%; border-collapse: collapse; background: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; overflow: hidden; }
  .purchases th, .purchases td { text-align: left; padding: 0.75rem 0.95rem; border-bottom: 1px solid var(--surface-2); font-size: 0.9rem; }
  .purchases th { color: var(--text-faint); font-weight: 500; background: var(--surface-2); }
  .purchases code { font-family: monospace; }
  .link { color: var(--accent); }
</style>
