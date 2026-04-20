<script lang="ts">
  import { onMount } from 'svelte';
  import { registryActor } from '$lib/canisters';
  import { frontendUrl, candidUiUrl, icDashboardUrl, shortId } from '$lib/config';
  import type { RealmRecord } from '$lib/types';

  let loading = true;
  let error = '';
  let allRealms: RealmRecord[] = [];
  let search = '';
  let currentPage = 0;
  const pageSize = 20;
  let expandedId: string | null = null;

  $: filtered = allRealms.filter(r =>
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    r.id.toLowerCase().includes(search.toLowerCase())
  );
  $: totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  $: pageRealms = filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  onMount(async () => {
    try {
      const raw = await registryActor.list_realms();
      const list = raw?.Ok ?? raw;
      allRealms = Array.isArray(list) ? list : [];
    } catch (e: any) {
      error = e.message || 'Failed to load realms';
    } finally {
      loading = false;
    }
  });

  function toggleExpand(id: string) {
    expandedId = expandedId === id ? null : id;
  }
</script>

<h1 class="page-title">Realms</h1>
<p class="page-subtitle">{allRealms.length} realm{allRealms.length !== 1 ? 's' : ''} registered</p>

<div class="toolbar">
  <input type="search" placeholder="Search realms by name or canister ID..." bind:value={search} on:input={() => currentPage = 0} />
</div>

{#if loading}
  <div class="empty-state"><span class="spinner"></span> Loading realms...</div>
{:else if error}
  <div class="card" style="border-color: var(--danger); color: var(--danger);">{error}</div>
{:else if filtered.length === 0}
  <div class="empty-state">No realms found{search ? ' matching "' + search + '"' : ''}.</div>
{:else}
  <div class="realm-list">
    {#each pageRealms as realm (realm.id)}
      <div class="card realm-card">
        <button class="realm-header" on:click={() => toggleExpand(realm.id)}>
          <div class="realm-info">
            {#if realm.logo}
              <img src={realm.logo} alt="" class="realm-logo" />
            {:else}
              <div class="realm-logo placeholder">◎</div>
            {/if}
            <div>
              <div class="realm-name">{realm.name}</div>
              <code class="realm-id">{shortId(realm.id)}</code>
            </div>
          </div>
          <div class="realm-meta">
            <span class="badge badge-neutral">{realm.users_count ?? 0} users</span>
            <span class="expand-icon" class:rotated={expandedId === realm.id}>▸</span>
          </div>
        </button>

        {#if expandedId === realm.id}
          <div class="realm-details">
            <div class="detail-row">
              <span class="detail-label">Backend</span>
              <code>{realm.id}</code>
              <a href={candidUiUrl(realm.id)} target="_blank" rel="noreferrer" class="link-external">Candid</a>
              <a href={icDashboardUrl(realm.id)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
            </div>
            {#if realm.url}
              <div class="detail-row">
                <span class="detail-label">Frontend</span>
                <a href={realm.url} target="_blank" rel="noreferrer" class="link-external">{realm.url}</a>
              </div>
            {/if}
            <div class="detail-actions">
              <a href="/realms/{realm.id}" class="btn btn-sm btn-primary">Full Details</a>
            </div>
          </div>
        {/if}
      </div>
    {/each}
  </div>

  {#if totalPages > 1}
    <div class="pagination">
      <button class="btn btn-sm" disabled={currentPage === 0} on:click={() => currentPage--}>Previous</button>
      <span class="page-info">Page {currentPage + 1} of {totalPages}</span>
      <button class="btn btn-sm" disabled={currentPage >= totalPages - 1} on:click={() => currentPage++}>Next</button>
    </div>
  {/if}
{/if}

<style>
  .toolbar { margin-bottom: 1rem; max-width: 400px; }
  .realm-list { display: flex; flex-direction: column; gap: 0.5rem; }
  .realm-card { padding: 0; overflow: hidden; }
  .realm-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0.85rem 1.25rem;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    color: inherit;
  }
  .realm-header:hover { background: var(--surface-2); }
  .realm-info { display: flex; align-items: center; gap: 0.75rem; }
  .realm-logo {
    width: 36px;
    height: 36px;
    border-radius: 0.5rem;
    object-fit: cover;
  }
  .realm-logo.placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--surface-2);
    color: var(--text-faint);
    font-size: 1.2rem;
  }
  .realm-name { font-weight: 600; font-size: 0.95rem; }
  .realm-id { font-size: 0.75rem; color: var(--text-faint); }
  .realm-meta { display: flex; align-items: center; gap: 0.75rem; }
  .expand-icon { transition: transform 0.15s; color: var(--text-faint); }
  .expand-icon.rotated { transform: rotate(90deg); }

  .realm-details {
    padding: 0.75rem 1.25rem 1rem;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }
  .detail-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.85rem; }
  .detail-label { font-weight: 600; font-size: 0.75rem; text-transform: uppercase; color: var(--text-faint); width: 5rem; }
  .detail-actions { margin-top: 0.5rem; }

  .pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin-top: 1.25rem;
  }
  .page-info { font-size: 0.85rem; color: var(--text-muted); }
</style>
