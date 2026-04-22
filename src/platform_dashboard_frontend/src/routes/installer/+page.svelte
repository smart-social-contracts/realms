<script lang="ts">
  import { onMount } from 'svelte';
  import { installerActor, registryActor } from '$lib/canisters';
  import { isAuthenticated } from '$lib/auth';
  import type { DeploymentJob, InstallerInfo } from '$lib/types';

  let loading = true;
  let error = '';
  let healthy = false;
  let info: InstallerInfo | null = null;
  let deploymentJobs: DeploymentJob[] = [];
  let legacyDeploys: any[] = [];

  // Deploy form state
  let showDeployForm = false;
  let deployRealmName = '';
  let deployDisplayName = '';
  let deployDescription = '';
  let deployNetwork = 'staging';
  let deploySubmitting = false;
  let deployError = '';
  let deploySuccess = '';

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    loading = true;
    error = '';
    try {
      const results = await Promise.allSettled([
        installerActor.health(),
        installerActor.info(),
        installerActor.list_deployment_jobs(),
        installerActor.list_deploys(),
      ]);

      if (results[0].status === 'fulfilled') healthy = true;

      if (results[1].status === 'fulfilled') {
        const raw = results[1].value;
        try {
          info = typeof raw === 'string' ? JSON.parse(raw) : raw;
        } catch { info = null; }
      }

      if (results[2].status === 'fulfilled') {
        const raw = results[2].value;
        try {
          const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
          deploymentJobs = parsed?.jobs || [];
        } catch { deploymentJobs = []; }
      }

      if (results[3].status === 'fulfilled') {
        const raw = results[3].value;
        try {
          const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
          legacyDeploys = parsed?.tasks || [];
        } catch { legacyDeploys = []; }
      }
    } catch (e: any) {
      error = e.message || 'Failed to load installer data';
    } finally {
      loading = false;
    }
  }

  async function submitDeployment() {
    deploySubmitting = true;
    deployError = '';
    deploySuccess = '';
    try {
      const manifest = JSON.stringify({
        realm: {
          name: deployRealmName,
          display_name: deployDisplayName || deployRealmName,
          description: deployDescription,
          extensions: ['all'],
        },
        network: deployNetwork,
      });

      const raw = await registryActor.request_deployment(manifest);
      const result = typeof raw === 'string' ? JSON.parse(raw) : raw;

      if (result?.success) {
        deploySuccess = `Deployment queued! Job ID: ${result.job_id}`;
        showDeployForm = false;
        await loadData();
      } else {
        deployError = result?.error || 'Deployment request failed';
      }
    } catch (e: any) {
      deployError = e.message || 'Failed to submit deployment';
    } finally {
      deploySubmitting = false;
    }
  }

  function statusBadgeClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'completed': return 'badge-success';
      case 'running': case 'deploying': case 'verifying':
      case 'extensions': case 'registering': return 'badge-warning';
      case 'failed': case 'failed_verification': case 'cancelled': return 'badge-danger';
      case 'pending': case 'queued': case 'waiting': return 'badge-info';
      default: return 'badge-neutral';
    }
  }

  function verifiedBadge(v: number): string {
    if (v === 1) return 'badge-success';
    if (v === -1) return 'badge-danger';
    return 'badge-neutral';
  }

  function verifiedLabel(v: number): string {
    if (v === 1) return 'Verified';
    if (v === -1) return 'Failed';
    return 'Pending';
  }

  function formatTime(ts: number): string {
    if (!ts) return '—';
    return new Date(ts * 1000).toLocaleString();
  }

  function shortId(id: string): string {
    if (!id || id.length <= 20) return id || '—';
    return id.slice(0, 10) + '...';
  }
</script>

<h1 class="page-title">Installer</h1>
<p class="page-subtitle">Realm deployment orchestration, queue management, and on-chain verification</p>

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
    <div class="stat-card">
      <div class="stat-value">{deploymentJobs.length}</div>
      <div class="stat-label">Deployment Jobs</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{legacyDeploys.length}</div>
      <div class="stat-label">Legacy Deploys</div>
    </div>
  </div>

  <!-- Deploy New Realm -->
  <div class="section-header">
    <h2>Deploy New Realm</h2>
    {#if $isAuthenticated}
      <button class="btn btn-primary btn-sm" on:click={() => showDeployForm = !showDeployForm}>
        {showDeployForm ? 'Cancel' : '+ New Deployment'}
      </button>
    {/if}
  </div>

  {#if showDeployForm}
    <div class="card deploy-form">
      <div class="form-group">
        <label for="realm-name">Realm Name (identifier)</label>
        <input id="realm-name" type="text" bind:value={deployRealmName} placeholder="e.g. dominion" />
      </div>
      <div class="form-group">
        <label for="display-name">Display Name</label>
        <input id="display-name" type="text" bind:value={deployDisplayName} placeholder="e.g. Dominion" />
      </div>
      <div class="form-group">
        <label for="description">Description</label>
        <textarea id="description" bind:value={deployDescription} rows="2" placeholder="Realm description..."></textarea>
      </div>
      <div class="form-group">
        <label for="network">Network</label>
        <select id="network" bind:value={deployNetwork}>
          <option value="staging">Staging</option>
          <option value="demo">Demo</option>
        </select>
      </div>

      {#if deployError}
        <div class="form-error">{deployError}</div>
      {/if}
      {#if deploySuccess}
        <div class="form-success">{deploySuccess}</div>
      {/if}

      <button
        class="btn btn-primary"
        on:click={submitDeployment}
        disabled={deploySubmitting || !deployRealmName}
      >
        {deploySubmitting ? 'Submitting...' : 'Submit Deployment Request'}
      </button>
    </div>
  {/if}

  <!-- Deployment Jobs (Queue-based) -->
  <h2 style="font-size: 1.1rem; margin: 1.5rem 0 0.75rem;">Deployment Jobs</h2>

  {#if deploymentJobs.length === 0}
    <div class="empty-state">No deployment jobs recorded.</div>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Status</th>
            <th>Network</th>
            <th>Backend</th>
            <th>WASM</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {#each deploymentJobs as job}
            <tr>
              <td><code>{shortId(job.job_id)}</code></td>
              <td><span class="badge {statusBadgeClass(job.status)}">{job.status}</span></td>
              <td>{job.network || '—'}</td>
              <td><code>{shortId(job.backend_canister_id)}</code></td>
              <td>
                <span class="badge {verifiedBadge(job.wasm_verified)}">
                  {verifiedLabel(job.wasm_verified)}
                </span>
              </td>
              <td>{formatTime(job.created_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  <!-- Legacy Deploys -->
  {#if legacyDeploys.length > 0}
    <h2 style="font-size: 1.1rem; margin: 1.5rem 0 0.75rem; opacity: 0.7;">Legacy Deploys</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Task ID</th>
            <th>Target</th>
            <th>Status</th>
            <th>Steps</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          {#each legacyDeploys as d}
            <tr>
              <td><code>{shortId(d.task_id)}</code></td>
              <td><code>{shortId(d.target_canister_id)}</code></td>
              <td><span class="badge {statusBadgeClass(d.status)}">{d.status}</span></td>
              <td>{d.steps_count ?? '—'}</td>
              <td>{formatTime(d.started_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}

<style>
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 1.5rem 0 0.75rem;
  }
  .section-header h2 {
    font-size: 1.1rem;
    margin: 0;
  }
  .deploy-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1.25rem;
    margin-bottom: 1rem;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .form-group label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
  }
  .form-group input, .form-group select, .form-group textarea {
    padding: 0.5rem 0.65rem;
    border: 1px solid var(--border);
    border-radius: 0.4rem;
    background: var(--surface);
    color: var(--text);
    font-size: 0.9rem;
  }
  .form-error {
    padding: 0.5rem 0.75rem;
    background: rgba(var(--danger-rgb, 220,53,69), 0.1);
    color: var(--danger);
    border-radius: 0.4rem;
    font-size: 0.85rem;
  }
  .form-success {
    padding: 0.5rem 0.75rem;
    background: rgba(var(--success-rgb, 40,167,69), 0.1);
    color: var(--success, #28a745);
    border-radius: 0.4rem;
    font-size: 0.85rem;
  }
  .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 0.5rem; }
  .table-wrap table { margin: 0; }
</style>
