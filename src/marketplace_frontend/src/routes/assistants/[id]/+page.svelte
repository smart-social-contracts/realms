<script lang="ts">
  import { page } from '$app/stores';
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
  import { marketplaceClient, type AssistantListing } from '$lib/marketplace-client';
  import { categories, formatCount, formatPrice, formatTimeAgo, shortPrincipal } from '$lib/format';

  type Tab = 'overview' | 'files';

  let item: AssistantListing | null = null;
  let loading = true;
  let error = '';
  let files: RegistryFile[] = [];
  let filesError = '';
  let liked = false;
  let purchased = false;
  let busy = false;
  let busyAudit = false;
  let auditMsg = '';
  let activeTab: Tab = 'overview';

  $: id = decodeURIComponent($page.params.id);
  $: void load(id);
  $: void refreshLikes($isAuthenticated, id);
  $: void refreshPurchased($isAuthenticated, $principalStore?.toText() ?? null, id);

  async function load(assistantId: string) {
    loading = true;
    error = '';
    try {
      item = await marketplaceClient.getAssistantDetails(assistantId);
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

  async function refreshLikes(_a: boolean, assistantId: string) {
    if (!_a) { liked = false; return; }
    try {
      const principal = $principalStore?.toText();
      if (!principal) return;
      liked = await marketplaceClient.hasLiked(principal, 'assistant', assistantId);
    } catch { liked = false; }
  }

  async function refreshPurchased(_a: boolean, principal: string | null, assistantId: string) {
    if (!_a || !principal) { purchased = false; return; }
    try {
      purchased = await marketplaceClient.hasPurchasedAssistant(principal, assistantId);
    } catch { purchased = false; }
  }

  async function doHire() {
    if (!item || busy) return;
    busy = true;
    try {
      await marketplaceClient.buyAssistant(item.assistant_id);
      purchased = true;
      item = await marketplaceClient.getAssistantDetails(item.assistant_id);
    } catch (e: any) {
      alert(`Hire failed: ${e?.message ?? e}`);
    } finally { busy = false; }
  }

  async function doRequestAudit() {
    if (!item || busyAudit) return;
    busyAudit = true;
    auditMsg = '';
    try {
      await marketplaceClient.requestAudit('assistant', item.assistant_id);
      auditMsg = '✅ Audit requested. Smart Social Contracts will review.';
      item = await marketplaceClient.getAssistantDetails(item.assistant_id);
    } catch (e: any) {
      auditMsg = `⚠️ ${e?.message ?? e}`;
    } finally { busyAudit = false; }
  }

  async function doDelist() {
    if (!item) return;
    if (!confirm(`Delist '${item.assistant_id}'? It will be removed from listings and rankings.`)) return;
    try {
      await marketplaceClient.delistAssistant(item.assistant_id);
      auditMsg = '✅ Delisted.';
      item = null;
      setTimeout(() => { window.location.href = '/assistants'; }, 800);
    } catch (e: any) {
      auditMsg = `⚠️ Could not delist: ${e?.message ?? e}`;
    }
  }

  function isOwner(): boolean {
    return Boolean(item && $principalStore && $principalStore.toText() === item.developer);
  }
</script>

<a class="back" href="/assistants">← Back to assistants</a>

{#if loading}
  <div class="state"><Spinner size={32} /></div>
{:else if error || !item}
  <div class="state error">⚠️ {error || 'Not found'}</div>
{:else}
  <article class="detail">
    <header>
      <div class="icon-large">{item.icon || '🤖'}</div>
      <div class="title-block">
        <div class="title-row">
          <h1>{item.name}</h1>
          <VerifiedBadge status={item.verification_status} size="md" />
        </div>
        <p class="meta">
          v{item.version} · by <code>{shortPrincipal(item.developer)}</code> · updated {formatTimeAgo(item.updated_at)}
          {#if item.runtime} · runtime: <code>{item.runtime}</code>{/if}
        </p>
        <div class="badges">
          <span class="badge">⬇ {formatCount(item.installs)} hires</span>
          <span class="badge">💲 {formatPrice(item.price_e8s)}</span>
          {#if item.pricing_summary}
            <span class="badge muted-badge">{item.pricing_summary}</span>
          {/if}
          {#if item.base_model}
            <span class="badge model">model: {item.base_model}</span>
          {/if}
          {#each categories(item.domains) as d}
            <span class="badge cat">{d.replace(/_/g, ' ')}</span>
          {/each}
          {#each categories(item.languages) as l}
            <span class="badge lang">{l}</span>
          {/each}
        </div>
      </div>
      <div class="cta">
        <button class="btn primary big" disabled={busy || purchased} on:click={doHire}>
          {purchased ? '✓ Hired' : busy ? 'Working…' : 'Hire / Install'}
        </button>
        <LikeButton kind="assistant" itemId={item.assistant_id} liked={liked} count={item.likes} />
      </div>
    </header>

    <div class="tabs" role="tablist">
      <button
        class="tab"
        class:active={activeTab === 'overview'}
        on:click={() => (activeTab = 'overview')}
        role="tab"
        aria-selected={activeTab === 'overview'}
      >Overview</button>
      <button
        class="tab"
        class:active={activeTab === 'files'}
        on:click={() => (activeTab = 'files')}
        role="tab"
        aria-selected={activeTab === 'files'}
      >Files {files.length ? `(${files.length})` : ''}</button>
    </div>

    {#if activeTab === 'overview'}
      <section class="block" role="tabpanel">
        <p class="description">{item.description || 'No description provided.'}</p>

        <h3>Runtime &amp; endpoint</h3>
        <dl class="kv">
          <dt>Runtime</dt><dd><code>{item.runtime || '(unspecified)'}</code></dd>
          <dt>Endpoint</dt>
          <dd>
            {#if item.endpoint_url}
              <code class="break">{item.endpoint_url}</code>
            {:else}
              <span class="muted">(none — listing is metadata-only)</span>
            {/if}
          </dd>
          <dt>Base model</dt><dd><code>{item.base_model || '(unspecified)'}</code></dd>
        </dl>

        <h3>Requested permissions</h3>
        <p class="muted small">
          When a realm hires this assistant, it asks for the following role and operations.
          The realm's hire-vote decides whether to grant them.
        </p>
        <dl class="kv">
          <dt>Role</dt><dd><code>{item.requested_role || '(none)'}</code></dd>
          <dt>Operations</dt>
          <dd>
            {#if item.requested_permissions}
              <ul class="perms">
                {#each categories(item.requested_permissions) as op}
                  <li><code>{op}</code></li>
                {/each}
              </ul>
            {:else}
              <span class="muted">(none declared — read-only assistant)</span>
            {/if}
          </dd>
        </dl>

        {#if item.training_data_summary}
          <h3>Training data summary</h3>
          <p class="prewrap">{item.training_data_summary}</p>
        {/if}

        {#if item.eval_report_url}
          <h3>Audit / evaluation report</h3>
          <p>
            <a class="link" href={item.eval_report_url} target="_blank" rel="noreferrer">Open report ↗</a>
          </p>
        {/if}

        {#if categories(item.categories).length > 0}
          <h3>Categories</h3>
          <div class="badges">
            {#each categories(item.categories) as c}
              <span class="badge cat">{c.replace(/_/g, ' ')}</span>
            {/each}
          </div>
        {/if}
      </section>
    {:else if activeTab === 'files'}
      <section class="block" role="tabpanel">
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
    {/if}

    {#if isOwner()}
      <section class="block owner">
        <h2>Owner actions</h2>
        <div class="owner-actions">
          <button class="btn" disabled={busyAudit} on:click={doRequestAudit}>
            {busyAudit ? 'Working…' : 'Request audit'}
          </button>
          <a class="btn" href={`/upload?prefill=${encodeURIComponent(item.assistant_id)}`}>Edit / new version</a>
          <button class="btn danger" on:click={doDelist}>Delist</button>
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
    display: grid; grid-template-columns: auto 1fr auto; gap: 1.5rem;
    align-items: flex-start; padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border); margin-bottom: 1.5rem;
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
  .badge { background: var(--surface-2); color: var(--text-muted); font-size: 0.75rem; padding: 0.25rem 0.6rem; border-radius: 999px; }
  .badge.cat { text-transform: capitalize; }
  .badge.model { background: #E0E7FF; color: #3730A3; }
  .badge.lang { background: #ECFCCB; color: #3F6212; text-transform: uppercase; font-family: monospace; font-size: 0.7rem; }
  .badge.muted-badge { font-size: 0.7rem; color: var(--text-faint); font-style: italic; }
  .cta { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end; }
  .btn {
    border: 1px solid var(--border); background: var(--surface); color: var(--text-muted);
    padding: 0.5rem 0.95rem; border-radius: 0.5rem;
  }
  .btn:hover:not(:disabled) { background: var(--surface-2); color: var(--text); }
  .btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
  .btn.primary:hover:not(:disabled) { background: var(--primary-hover); }
  .btn.big { padding: 0.7rem 1.4rem; font-size: 0.95rem; }
  .btn.danger { background: var(--danger); border-color: var(--danger); color: #fff; }
  .btn.danger:hover { opacity: 0.92; }
  .tabs {
    display: flex; gap: 0.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
  }
  .tab {
    background: transparent; border: none; padding: 0.7rem 1rem;
    color: var(--text-muted); border-bottom: 2px solid transparent;
    font-size: 0.9rem; cursor: pointer; transition: color 0.15s;
  }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--text); border-bottom-color: var(--primary); font-weight: 500; }
  .block { margin-bottom: 2rem; }
  .block h2 { font-size: 1.1rem; margin: 0 0 0.85rem; }
  .block h3 { font-size: 0.85rem; margin: 1.5rem 0 0.5rem; color: var(--text-faint); font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; }
  .block p { color: var(--text-muted); margin: 0; line-height: 1.7; }
  .block .description { color: var(--text); }
  .prewrap { white-space: pre-wrap; }
  .kv {
    display: grid; grid-template-columns: 140px 1fr; gap: 0.4rem 1rem;
    margin: 0.5rem 0;
  }
  .kv dt { color: var(--text-faint); font-size: 0.85rem; }
  .kv dd { margin: 0; color: var(--text); font-size: 0.9rem; }
  .kv .break { word-break: break-all; }
  .perms { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 0.2rem; }
  .perms li { background: var(--surface-2); padding: 0.25rem 0.55rem; border-radius: 0.3rem; font-size: 0.8rem; }
  .files { width: 100%; border-collapse: collapse; }
  .files th, .files td { text-align: left; padding: 0.55rem 0.5rem; border-bottom: 1px solid var(--surface-2); font-size: 0.85rem; }
  .files th { color: var(--text-faint); font-weight: 500; }
  .link { color: var(--accent); }
  .muted { color: var(--text-faint); }
  .small { font-size: 0.8rem; }
  .error { color: var(--danger); }
  .owner h2 { color: var(--accent); }
  .owner-actions { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
  .owner-actions a.btn { text-decoration: none; }
  .audit-msg { color: var(--text-muted); font-size: 0.85rem; }
  .audit-notes { margin-top: 0.85rem; background: var(--surface-2); padding: 0.75rem 1rem; border-radius: 0.5rem; }
  @media (max-width: 760px) { header { grid-template-columns: 1fr; } .cta { align-items: flex-start; } .kv { grid-template-columns: 1fr; } }
</style>
