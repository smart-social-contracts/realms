<script lang="ts">import { _ } from "svelte-i18n";
import Spinner from "$lib/components/Spinner.svelte";
import VerifiedBadge from "$lib/components/VerifiedBadge.svelte";
import ItemIcon from "$lib/components/ItemIcon.svelte";
import { isAuthenticated } from "$lib/auth";
import {
  marketplaceClient
} from "$lib/marketplace-client";
import { formatTimeAgo, formatPrice, shortPrincipal } from "$lib/format";
let loading = false;
let error = "";
let rows = [];
$: void load($isAuthenticated);
async function load(_authed) {
  if (!_authed) {
    rows = [];
    return;
  }
  loading = true;
  error = "";
  try {
    const purchases = await marketplaceClient.getMyPurchases();
    const enriched = await Promise.all(
      purchases.map(async (p) => {
        let detail = null;
        try {
          detail = p.item_kind === "codex" ? await marketplaceClient.getCodexDetails(p.item_id) : await marketplaceClient.getExtensionDetails(p.item_id);
        } catch {
          detail = null;
        }
        const dev = detail?.developer ?? p.developer ?? "";
        return {
          ...p,
          name: detail?.name || p.item_id,
          icon: detail?.icon || "",
          version: detail?.version || "",
          verification_status: detail?.verification_status || "unverified",
          developer_short: shortPrincipal(dev),
          detail_load_failed: detail == null
        };
      })
    );
    rows = enriched;
  } catch (e) {
    error = e?.message ?? String(e);
    rows = [];
  } finally {
    loading = false;
  }
}
function hrefFor(p) {
  if (p.item_kind === "codex") return `/codices/${encodeURIComponent(p.item_id)}`;
  return `/extensions/${encodeURIComponent(p.item_id)}`;
}
</script>

<header class="head">
  <h1>{$_('purchases.title')}</h1>
  <p>{$_('purchases.subtitle')}</p>
</header>

{#if !$isAuthenticated}
  <div class="card warn">
    <h2>{$_('purchases.signin')}</h2>
  </div>
{:else if loading}
  <div class="state"><Spinner /></div>
{:else if error}
  <div class="state error">{error}</div>
{:else if rows.length === 0}
  <div class="state empty">
    <p>{$_('purchases.empty_browse')} <a href="/extensions">{$_('purchases.link_extensions')}</a> {$_('purchases.or')} <a href="/codices">{$_('purchases.link_codices')}</a>.</p>
  </div>
{:else}
  <table class="purchases">
    <thead>
      <tr>
        <th></th>
        <th>{$_('purchases.col_item')}</th>
        <th>{$_('purchases.col_kind')}</th>
        <th>{$_('purchases.col_developer')}</th>
        <th>{$_('purchases.col_price')}</th>
        <th>{$_('purchases.col_when')}</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as p}
        <tr>
          <td class="icon"><ItemIcon icon={p.icon} kind={p.item_kind === 'codex' ? 'codex' : p.item_kind === 'assistant' ? 'assistant' : 'ext'} /></td>
          <td>
            <div class="title">
              <a class="link" href={hrefFor(p)}>{p.name}</a>
              {#if p.version}<span class="ver">v{p.version}</span>{/if}
              {#if !p.detail_load_failed}
                <VerifiedBadge status={p.verification_status} />
              {:else}
                <span class="delisted">{$_('purchases.delisted')}</span>
              {/if}
            </div>
            <code class="subtle">{p.item_id}</code>
          </td>
          <td>{p.item_kind === 'codex' ? $_('purchases.kind_codex') : $_('purchases.kind_extension')}</td>
          <td><code>{p.developer_short}</code></td>
          <td>{formatPrice(p.price_paid_e8s)}</td>
          <td>{formatTimeAgo(p.purchased_at)}</td>
          <td><a class="link" href={hrefFor(p)}>{$_('purchases.view')}</a></td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); }
  .card { background: var(--surface); border: 1px solid var(--border); padding: 2rem; border-radius: 0.75rem; text-align: center; }
  .card.warn { border-color: var(--border-strong); background: var(--surface-2); color: var(--text); }
  .state { text-align: center; padding: 3rem; color: var(--text-muted); }
  .state.error { color: var(--danger); }
  .purchases { width: 100%; border-collapse: collapse; background: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; overflow: hidden; }
  .purchases th, .purchases td { text-align: left; padding: 0.75rem 0.95rem; border-bottom: 1px solid var(--surface-2); font-size: 0.9rem; vertical-align: middle; }
  .purchases th { color: var(--text-faint); font-weight: 500; background: var(--surface-2); }
  .purchases code { font-family: monospace; }
  .icon { font-size: 1.4rem; width: 38px; }
  .title { display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
  .title .link { font-weight: 500; }
  .ver { color: var(--text-faint); font-size: 0.75rem; font-family: monospace; }
  .subtle { color: var(--text-faint); font-size: 0.7rem; }
  .delisted {
    background: var(--surface-2); color: var(--text-faint);
    padding: 2px 8px; border-radius: 999px;
    font-size: 0.7rem;
  }
  .link { color: var(--accent); text-decoration: none; }
  .link:hover { text-decoration: underline; }
</style>
