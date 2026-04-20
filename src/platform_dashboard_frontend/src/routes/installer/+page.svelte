<script lang="ts">
  import { onMount } from 'svelte';
  import { installerActor } from '$lib/canisters';
  import type { DeployRecord, InstallerInfo } from '$lib/types';

  let loading = true;
  let error = '';
  let healthy = false;
  let info: InstallerInfo | null = null;
  let deploys: DeployRecord[] = [];

  onMount(async () => {
    try {
      const results = await Promise.allSettled([
        installerActor.health(),
        installerActor.info(),
        installerActor.list_deploys(),
      ]);

      if (results[0].status === 'fulfilled') healthy = true;

      if (results[1].status === 'fulfilled') {
        const raw = results[1].value;
        try {
          info = typeof raw === 'string' ? JSON.parse(raw) : (raw?.Ok ? JSON.parse(raw.Ok) : raw);
        } catch { info = null; }
      }

      if (results[2].status === 'fulfilled') {
        const raw = results[2].value;
        try {
          const parsed = typeof raw === 'string' ? JSON.parse(raw) : (raw?.Ok ? JSON.parse(raw.Ok) : raw);
          deploys = Array.isArray(parsed) ? parsed : [];
        } catch { deploys = []; }
      }
    } catch (e: any) {
      error = e.message || 'Failed to load installer data';
    } finally {
      loading = false;
    }
  });

  function statusBadgeClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'completed': case 'success': return 'badge-success';
      case 'in_progress': case 'in-progress': case 'running': return 'badge-warning';
      case 'failed': case 'error': return 'badge-danger';
      case 'pending': case 'queued': return 'badge-info';
      default: return 'badge-neutral';
    }
  }
</script>

<h1 class="page-title">Installer</h1>
<p class="page-subtitle">Realm deployment management and monitoring</p>

{#if loading}
  <div class="empty-state"><span class="spinner"></span> Loading installer data...</div>
{:else if error}
  <div class="card" style="border-color: var(--danger); color: var(--danger);">{error}</div>
{:else}
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-value">
        <span class="badge" class:badge-success={healthy} class:badge-danger={!healthy}>
          {healthy ? 'Healthy' : 'Unreachable'}
        </span>
      </div>
      <div class="stat-label">Health Status</div>
    </div>
    {#if info?.version}
      <div class="stat-card">
        <div class="stat-value" style="font-size:1.1rem">{info.version}</div>
        <div class="stat-label">Version</div>
      </div>
    {/if}
    {#if info?.commit}
      <div class="stat-card">
        <div class="stat-value" style="font-size:1.1rem; font-family:monospace">{info.commit}</div>
        <div class="stat-label">Commit</div>
      </div>
    {/if}
    <div class="stat-card">
      <div class="stat-value">{deploys.length}</div>
      <div class="stat-label">Total Deployments</div>
    </div>
  </div>

  <h2 style="font-size: 1.1rem; margin: 1.5rem 0 0.75rem;">Deployments</h2>

  {#if deploys.length === 0}
    <div class="empty-state">No deployments recorded.</div>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Deploy ID</th>
            <th>Realm</th>
            <th>Status</th>
            <th>Started</th>
            <th>Completed</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each deploys as d}
            <tr>
              <td><code>{d.deploy_id}</code></td>
              <td>{d.realm_name || '—'}</td>
              <td><span class="badge {statusBadgeClass(d.status)}">{d.status}</span></td>
              <td>{d.started_at || '—'}</td>
              <td>{d.completed_at || '—'}</td>
              <td>
                <a href="/installer/{d.deploy_id}" class="btn btn-sm">Details</a>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}

<style>
  .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 0.5rem; }
  .table-wrap table { margin: 0; }
</style>
