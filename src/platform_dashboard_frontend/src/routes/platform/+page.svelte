<script lang="ts">
  import { onMount } from 'svelte';
  import { registryActor, installerActor, marketplaceActor, fileRegistryActor } from '$lib/canisters';
  import { CONFIG, frontendUrl, candidUiUrl, icDashboardUrl, shortId } from '$lib/config';
  import type { StatusRecord, FileRegistryStats, InstallerInfo } from '$lib/types';

  interface SubsystemInfo {
    name: string;
    backendId: string;
    frontendId: string;
    status: StatusRecord | null;
    extra: Record<string, any>;
    loading: boolean;
    error: string;
  }

  let subsystems: SubsystemInfo[] = [
    { name: 'Realm Registry', backendId: CONFIG.realm_registry_backend_id, frontendId: CONFIG.realm_registry_frontend_id, status: null, extra: {}, loading: true, error: '' },
    { name: 'Realm Installer', backendId: CONFIG.realm_installer_id, frontendId: CONFIG.realm_installer_frontend_id, status: null, extra: {}, loading: true, error: '' },
    { name: 'Marketplace', backendId: CONFIG.marketplace_backend_id, frontendId: CONFIG.marketplace_frontend_id, status: null, extra: {}, loading: true, error: '' },
    { name: 'File Registry', backendId: CONFIG.file_registry_id, frontendId: CONFIG.file_registry_frontend_id, status: null, extra: {}, loading: true, error: '' },
  ];

  onMount(async () => {
    const fetchers = [
      async () => {
        try {
          const raw = await registryActor.status();
          subsystems[0].status = raw?.Ok ?? raw;
        } catch (e: any) { subsystems[0].error = e.message; }
        subsystems[0].loading = false;
        subsystems = subsystems;
      },
      async () => {
        try {
          const [health, info] = await Promise.all([
            installerActor.health().catch(() => null),
            installerActor.info().catch(() => null),
          ]);
          subsystems[1].extra = { healthy: !!(health as any)?.ok };
          if (info) {
            subsystems[1].status = info as any;
          }
        } catch (e: any) { subsystems[1].error = e.message; }
        subsystems[1].loading = false;
        subsystems = subsystems;
      },
      async () => {
        try {
          const raw = await marketplaceActor.status();
          subsystems[2].status = raw?.Ok ?? raw;
        } catch (e: any) { subsystems[2].error = e.message; }
        subsystems[2].loading = false;
        subsystems = subsystems;
      },
      async () => {
        try {
          const raw = await fileRegistryActor.get_stats();
          const parsed = typeof raw === 'string' ? JSON.parse(raw) : (raw?.Ok ? JSON.parse(raw.Ok) : raw);
          subsystems[3].extra = { stats: parsed };
        } catch (e: any) { subsystems[3].error = e.message; }
        subsystems[3].loading = false;
        subsystems = subsystems;
      },
    ];
    await Promise.allSettled(fetchers.map(f => f()));
  });
</script>

<h1 class="page-title">Platform Infrastructure</h1>
<p class="page-subtitle">Core canister subsystems powering the platform</p>

<div class="grid">
  {#each subsystems as sub}
    <div class="card subsystem-card">
      <div class="sub-header">
        <h3 class="sub-name">{sub.name}</h3>
        {#if sub.loading}
          <span class="badge badge-neutral"><span class="spinner" style="width:0.8em;height:0.8em;"></span></span>
        {:else if sub.error}
          <span class="badge badge-danger">Error</span>
        {:else}
          <span class="badge badge-success">Online</span>
        {/if}
      </div>

      {#if sub.status?.version}
        <div class="sub-meta">v{sub.status.version}</div>
      {/if}
      {#if sub.status?.commit}
        <div class="sub-meta">Commit: {sub.status.commit}</div>
      {/if}

      {#if sub.name === 'Realm Registry' && sub.status?.realms_count != null}
        <div class="sub-stat">{sub.status.realms_count} realms</div>
      {/if}

      {#if sub.name === 'Marketplace' && sub.status}
        <div class="sub-stat">
          {sub.status.extensions_count ?? 0} extensions,
          {sub.status.codices_count ?? 0} codices,
          {sub.status.assistants_count ?? 0} assistants
        </div>
      {/if}

      {#if sub.name === 'Realm Installer'}
        <div class="sub-stat">
          Health: <span class="badge" class:badge-success={sub.extra.healthy} class:badge-danger={!sub.extra.healthy}>
            {sub.extra.healthy ? 'OK' : 'Down'}
          </span>
        </div>
      {/if}

      {#if sub.name === 'File Registry' && sub.extra.stats}
        <div class="sub-stat">
          {sub.extra.stats.total_files ?? 0} files,
          {sub.extra.stats.total_chunks ?? 0} chunks
        </div>
      {/if}

      {#if sub.error}
        <div class="sub-error">{sub.error}</div>
      {/if}

      <div class="sub-links">
        {#if sub.backendId}
          <div class="canister-row">
            <span class="canister-label">Backend</span>
            <code class="canister-id">{shortId(sub.backendId)}</code>
            <a href={candidUiUrl(sub.backendId)} target="_blank" rel="noreferrer" class="link-external">Candid</a>
            <a href={icDashboardUrl(sub.backendId)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
          </div>
        {/if}
        {#if sub.frontendId}
          <div class="canister-row">
            <span class="canister-label">Frontend</span>
            <code class="canister-id">{shortId(sub.frontendId)}</code>
            <a href={frontendUrl(sub.frontendId)} target="_blank" rel="noreferrer" class="link-external">Open</a>
            <a href={icDashboardUrl(sub.frontendId)} target="_blank" rel="noreferrer" class="link-external">IC Dashboard</a>
          </div>
        {/if}
      </div>
    </div>
  {/each}
</div>

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
  }
  .subsystem-card { display: flex; flex-direction: column; gap: 0.5rem; }
  .sub-header { display: flex; align-items: center; justify-content: space-between; }
  .sub-name { font-size: 1.05rem; margin: 0; font-weight: 600; }
  .sub-meta { font-size: 0.78rem; color: var(--text-faint); font-family: monospace; }
  .sub-stat { font-size: 0.85rem; color: var(--text-muted); }
  .sub-error { font-size: 0.8rem; color: var(--danger); }
  .sub-links {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--border);
  }
  .canister-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .canister-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-faint);
    width: 5rem;
  }
  .canister-id {
    font-size: 0.78rem;
    color: var(--text-muted);
    background: var(--surface-2);
    padding: 0.15em 0.4em;
    border-radius: 0.25rem;
  }
</style>
