<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import LikeButton from '$lib/components/LikeButton.svelte';
  import Spinner from '$lib/components/Spinner.svelte';
  import VerifiedBadge from '$lib/components/VerifiedBadge.svelte';
  import { isAuthenticated, principalStore } from '$lib/auth';
  import {
    fileRegistryBaseUrl,
    fileUrl,
    listFiles,
    type RegistryFile,
  } from '$lib/file-registry-client';
  import {
    marketplaceClient,
    type ExtensionListing,
  } from '$lib/marketplace-client';
  import { categories, formatCount, formatPrice, formatTimeAgo, shortPrincipal } from '$lib/format';

  let item: ExtensionListing | null = null;
  let loading = true;
  let error = '';
  let files: RegistryFile[] = [];
  let filesError = '';
  let liked = false;
  let purchased = false;
  let busy = false;
  let busyAudit = false;
  let auditMsg = '';

  $: id = decodeURIComponent($page.params.id);
  $: void load(id);
  $: void refreshLikes($isAuthenticated, id);
  $: void refreshPurchased($isAuthenticated, $principalStore?.toText() ?? null, id);

  async function load(extId: string) {
    loading = true;
    error = '';
    try {
      item = await marketplaceClient.getExtensionDetails(extId);
      filesError = '';
      if (item.file_registry_canister_id && item.file_registry_namespace) {
        try {
          files = await listFiles(item.file_registry_canister_id, item.file_registry_namespace);
        } catch (e: any) {
          filesError = e?.message ?? String(e);
        }
      }
    } catch (e: any) {
      error = e?.message ?? String(e);
      item = null;
    } finally {
      loading = false;
    }
  }

  async function refreshLikes(_a: boolean, extId: string) {
    if (!_a) {
      liked = false;
      return;
    }
    try {
      const principal = $principalStore?.toText();
      if (!principal) return;
      liked = await marketplaceClient.hasLiked(principal, 'ext', extId);
    } catch {
      liked = false;
    }
  }

  async function refreshPurchased(_a: boolean, principal: string | null, extId: string) {
    if (!_a || !principal) {
      purchased = false;
      return;
    }
    try {
      purchased = await marketplaceClient.hasPurchasedExtension(principal, extId);
    } catch {
      purchased = false;
    }
  }

  async function doBuy() {
    if (!item || busy) return;
    busy = true;
    try {
      await marketplaceClient.buyExtension(item.extension_id);
      purchased = true;
      // refresh installs counter
      item = await marketplaceClient.getExtensionDetails(item.extension_id);
    } catch (e: any) {
      alert(`Purchase failed: ${e?.message ?? e}`);
    } finally {
      busy = false;
    }
  }

  async function doRequestAudit() {
    if (!item || busyAudit) return;
    busyAudit = true;
    auditMsg = '';
    try {
      await marketplaceClient.requestAudit('ext', item.extension_id);
      auditMsg = '✅ Audit requested. Smart Social Contracts will review.';
      item = await marketplaceClient.getExtensionDetails(item.extension_id);
    } catch (e: any) {
      auditMsg = `⚠️ ${e?.message ?? e}`;
    } finally {
      busyAudit = false;
    }
  }

  function isOwner(): boolean {
    return Boolean(item && $principalStore && $principalStore.toText() === item.developer);
  }
</script>

<a class="back" href="/extensions">← Back to extensions</a>

{#if loading}
  <div class="state"><Spinner size={32} /></div>
{:else if error || !item}
  <div class="state error">⚠️ {error || 'Not found'}</div>
{:else}
  <article class="detail">
    <header>
      <div class="icon-large">{item.icon || '🧩'}</div>
      <div class="title-block">
        <div class="title-row">
          <h1>{item.name}</h1>
          <VerifiedBadge status={item.verification_status} size="md" />
        </div>
        <p class="meta">
          v{item.version} · by <code>{shortPrincipal(item.developer)}</code> · updated {formatTimeAgo(item.updated_at)}
        </p>
        <div class="badges">
          <span class="badge">⬇ {formatCount(item.installs)} installs</span>
          <span class="badge">💲 {formatPrice(item.price_e8s)}</span>
          {#each categories(item.categories) as c}
            <span class="badge cat">{c.replace(/_/g, ' ')}</span>
          {/each}
        </div>
      </div>
      <div class="cta">
        <button class="btn primary big" disabled={busy || purchased} on:click={doBuy}>
          {purchased ? '✓ Purchased' : busy ? 'Working…' : 'Install / Buy'}
        </button>
        <LikeButton kind="ext" itemId={item.extension_id} liked={liked} count={item.likes} />
      </div>
    </header>

    <section class="block">
      <h2>About</h2>
      <p>{item.description || 'No description provided.'}</p>
    </section>

    <section class="block">
      <h2>Files</h2>
      {#if !item.file_registry_canister_id || !item.file_registry_namespace}
        <p class="muted">No file_registry namespace attached to this listing.</p>
      {:else if filesError}
        <p class="error">⚠️ Could not load files from registry: {filesError}</p>
      {:else if files.length === 0}
        <p class="muted">No files published in <code>{item.file_registry_namespace}</code> yet.</p>
      {:else}
        <table class="files">
          <thead><tr><th>Path</th><th>Size</th><th>Type</th><th></th></tr></thead>
          <tbody>
            {#each files as f}
              <tr>
                <td><code>{f.path}</code></td>
                <td>{formatBytes(f.size)}</td>
                <td><code>{f.content_type}</code></td>
                <td>
                  <a class="link" href={fileUrl(item.file_registry_canister_id, item.file_registry_namespace, f.path)} target="_blank" rel="noreferrer">Open ↗</a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
        <p class="muted small">
          Served from <code>{item.file_registry_canister_id}</code>
          (<a href={fileRegistryBaseUrl(item.file_registry_canister_id)} target="_blank" rel="noreferrer">registry root ↗</a>)
        </p>
      {/if}
    </section>

    {#if isOwner()}
      <section class="block owner">
        <h2>Owner actions</h2>
        <div class="owner-actions">
          <button class="btn" disabled={busyAudit} on:click={doRequestAudit}>
            {busyAudit ? 'Working…' : 'Request audit'}
          </button>
          {#if auditMsg}<span class="audit-msg">{auditMsg}</span>{/if}
        </div>
        {#if item.verification_notes}
          <p class="audit-notes"><strong>Curator notes:</strong> {item.verification_notes}</p>
        {/if}
      </section>
    {/if}
  </article>
{/if}

<script lang="ts" context="module">
  function formatBytes(n: number): string {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  }
</script>

<style>
  .back { display: inline-block; margin-bottom: 1rem; color: var(--text-muted); text-decoration: none; }
  .back:hover { color: var(--text); }
  .state { text-align: center; padding: 4rem; color: var(--text-muted); }
  .state.error { color: var(--danger); }
  .detail { background: var(--surface); border: 1px solid var(--border); border-radius: 0.85rem; padding: 2rem; }
  header {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 1.5rem;
    align-items: flex-start;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
  }
  .icon-large {
    width: 88px; height: 88px; border-radius: 1rem;
    background: var(--surface-2); display: flex; align-items: center; justify-content: center;
    font-size: 2.5rem;
  }
  .title-block { min-width: 0; }
  .title-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
  h1 { margin: 0; font-size: 1.6rem; }
  .meta { margin: 0.4rem 0 0.85rem; color: var(--text-faint); font-size: 0.85rem; }
  .meta code { font-family: monospace; }
  .badges { display: flex; gap: 0.4rem; flex-wrap: wrap; }
  .badge {
    background: var(--surface-2); color: var(--text-muted);
    font-size: 0.75rem; padding: 0.25rem 0.6rem; border-radius: 999px;
  }
  .badge.cat { text-transform: capitalize; }
  .cta { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end; }
  .btn {
    border: 1px solid var(--border); background: var(--surface); color: var(--text-muted);
    padding: 0.5rem 0.95rem; border-radius: 0.5rem; transition: all 0.15s;
  }
  .btn:hover:not(:disabled) { background: var(--surface-2); color: var(--text); }
  .btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
  .btn.primary:hover:not(:disabled) { background: var(--primary-hover); }
  .btn.big { padding: 0.7rem 1.4rem; font-size: 0.95rem; }
  .block { margin-bottom: 2rem; }
  .block h2 { font-size: 1.1rem; margin: 0 0 0.85rem; }
  .block p { color: var(--text-muted); margin: 0; line-height: 1.7; }
  .files {
    width: 100%; border-collapse: collapse;
  }
  .files th, .files td {
    text-align: left; padding: 0.55rem 0.5rem; border-bottom: 1px solid var(--surface-2);
    font-size: 0.85rem;
  }
  .files th { color: var(--text-faint); font-weight: 500; }
  .files td code { font-size: 0.85rem; }
  .link { color: var(--accent); }
  .muted { color: var(--text-faint); }
  .small { font-size: 0.8rem; }
  .error { color: var(--danger); }
  .owner h2 { color: var(--accent); }
  .owner-actions { display: flex; gap: 0.75rem; align-items: center; }
  .audit-msg { color: var(--text-muted); font-size: 0.85rem; }
  .audit-notes { margin-top: 0.85rem; background: var(--surface-2); padding: 0.75rem 1rem; border-radius: 0.5rem; }

  @media (max-width: 760px) {
    header { grid-template-columns: 1fr; }
    .cta { align-items: flex-start; }
  }
</style>
