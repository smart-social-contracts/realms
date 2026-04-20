<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { createRealmBackendActor, registryActor } from '$lib/canisters';
  import { frontendUrl, candidUiUrl, icDashboardUrl, shortId } from '$lib/config';
  import type { StatusRecord, CanisterInfo, QuarterInfoRecord } from '$lib/types';

  let loading = true;
  let error = '';
  let realmName = '';
  let realmUrl = '';
  let status: StatusRecord | null = null;

  $: realmId = $page.params.realmId;

  onMount(async () => {
    try {
      // Try to get realm info from registry
      try {
        const realms = await registryActor.list_realms();
        const list = realms?.Ok ?? realms;
        if (Array.isArray(list)) {
          const found = list.find((r: any) => r.id === realmId);
          if (found) {
            realmName = found.name;
            realmUrl = found.url;
          }
        }
      } catch { /* registry unavailable */ }

      const actor = await createRealmBackendActor(realmId);
      const raw = await actor.status();
      status = raw?.Ok ?? raw;
    } catch (e: any) {
      error = e.message || 'Failed to load realm details';
    } finally {
      loading = false;
    }
  });

  function canisterTypeLabel(t: string): string {
    const labels: Record<string, string> = {
      'backend': 'Backend',
      'frontend': 'Frontend',
      'quarter': 'Quarter',
      'token': 'Token',
      'nft': 'NFT',
      'file_registry': 'File Registry',
    };
    return labels[t] || t;
  }
</script>

<div class="breadcrumb">
  <a href="/realms">Realms</a>
  <span class="sep">/</span>
  <span>{realmName || shortId(realmId)}</span>
</div>

<h1 class="page-title">{realmName || 'Realm'}</h1>
<p class="page-subtitle">
  Canister ID: <code>{realmId}</code>
  {#if realmUrl}
    &middot; <a href={realmUrl} target="_blank" rel="noreferrer" class="link-external">Open Frontend</a>
  {/if}
</p>

{#if loading}
  <div class="empty-state"><span class="spinner"></span> Loading realm status...</div>
{:else if error}
  <div class="card" style="border-color: var(--danger); color: var(--danger);">{error}</div>
{:else if status}
  <div class="stat-grid">
    {#if status.version}
      <div class="stat-card">
        <div class="stat-value" style="font-size:1.1rem">{status.version}</div>
        <div class="stat-label">Version</div>
      </div>
    {/if}
    {#if status.users_count != null}
      <div class="stat-card">
        <div class="stat-value">{status.users_count}</div>
        <div class="stat-label">Users</div>
      </div>
    {/if}
    {#if status.objects_count != null}
      <div class="stat-card">
        <div class="stat-value">{status.objects_count}</div>
        <div class="stat-label">Objects</div>
      </div>
    {/if}
    {#if status.extensions && status.extensions.length > 0}
      <div class="stat-card">
        <div class="stat-value">{status.extensions.length}</div>
        <div class="stat-label">Extensions</div>
      </div>
    {/if}
  </div>

  <!-- Core Canisters -->
  <section class="section">
    <h2 class="section-title">Canisters</h2>
    <div class="canister-tree">
      <!-- The realm backend itself -->
      <div class="tree-node root">
        <span class="tree-type badge badge-info">Backend</span>
        <code class="tree-id">{realmId}</code>
        <span class="tree-links">
          <a href={candidUiUrl(realmId)} target="_blank" rel="noreferrer" class="link-external">Candid</a>
          <a href={icDashboardUrl(realmId)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
        </span>
      </div>

      {#if realmUrl}
        {@const frontendId = realmUrl.replace('https://', '').replace('.icp0.io', '').replace('.localhost:4943', '')}
        <div class="tree-node">
          <span class="tree-type badge badge-success">Frontend</span>
          <code class="tree-id">{shortId(frontendId)}</code>
          <span class="tree-links">
            <a href={realmUrl} target="_blank" rel="noreferrer" class="link-external">Open</a>
            <a href={icDashboardUrl(frontendId)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
          </span>
        </div>
      {/if}

      {#if status.canisters}
        {#each status.canisters as c}
          <div class="tree-node">
            <span class="tree-type badge badge-neutral">{canisterTypeLabel(c.canister_type)}</span>
            {#if c.name}<span class="tree-name">{c.name}</span>{/if}
            <code class="tree-id">{shortId(c.canister_id)}</code>
            <span class="tree-links">
              <a href={candidUiUrl(c.canister_id)} target="_blank" rel="noreferrer" class="link-external">Candid</a>
              <a href={icDashboardUrl(c.canister_id)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
            </span>
          </div>
        {/each}
      {/if}
    </div>
  </section>

  <!-- Quarters -->
  {#if status.quarters && status.quarters.length > 0}
    <section class="section">
      <h2 class="section-title">Quarters ({status.quarters.length})</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Canister ID</th>
              <th>Population</th>
              <th>Status</th>
              <th>Links</th>
            </tr>
          </thead>
          <tbody>
            {#each status.quarters as q}
              <tr>
                <td>{q.name}</td>
                <td><code>{shortId(q.canister_id)}</code></td>
                <td>{q.population}</td>
                <td>
                  <span class="badge"
                    class:badge-success={q.status === 'active'}
                    class:badge-warning={q.status === 'initializing'}
                    class:badge-danger={q.status === 'error'}
                    class:badge-neutral={!['active','initializing','error'].includes(q.status)}
                  >{q.status}</span>
                </td>
                <td>
                  <a href={candidUiUrl(q.canister_id)} target="_blank" rel="noreferrer" class="link-external">Candid</a>
                  <a href={icDashboardUrl(q.canister_id)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}

  <!-- Registries -->
  {#if status.registries && status.registries.length > 0}
    <section class="section">
      <h2 class="section-title">Linked Registries</h2>
      {#each status.registries as r}
        <div class="tree-node">
          <span class="tree-type badge badge-neutral">{canisterTypeLabel(r.canister_type)}</span>
          {#if r.name}<span class="tree-name">{r.name}</span>{/if}
          <code class="tree-id">{shortId(r.canister_id)}</code>
          <span class="tree-links">
            <a href={candidUiUrl(r.canister_id)} target="_blank" rel="noreferrer" class="link-external">Candid</a>
            <a href={icDashboardUrl(r.canister_id)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
          </span>
        </div>
      {/each}
    </section>
  {/if}
{/if}

<style>
  .breadcrumb {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
  }
  .breadcrumb a { color: var(--primary); text-decoration: none; }
  .breadcrumb a:hover { text-decoration: underline; }
  .sep { margin: 0 0.4rem; color: var(--text-faint); }

  .section { margin-top: 2rem; }
  .section-title { font-size: 1.1rem; margin: 0 0 0.75rem; font-weight: 600; }

  .canister-tree { display: flex; flex-direction: column; gap: 0.4rem; }
  .tree-node {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    padding: 0.5rem 0.75rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
  }
  .tree-node.root { border-color: var(--primary); border-width: 2px; }
  .tree-type { flex-shrink: 0; }
  .tree-name { font-size: 0.85rem; font-weight: 500; }
  .tree-id { font-size: 0.78rem; color: var(--text-muted); }
  .tree-links { display: flex; gap: 0.5rem; margin-left: auto; }

  .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 0.5rem; }
  .table-wrap table { margin: 0; }
</style>
