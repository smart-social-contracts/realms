<script lang="ts">
  import { onMount } from 'svelte';
  import { installerActor, registryActor } from '$lib/canisters';
  import { isAuthenticated } from '$lib/auth';
  import { CONFIG } from '$lib/config';
  import type { DeploymentJob, InstallerInfo } from '$lib/types';

  let loading = true;
  let error = '';
  let healthy = false;
  let info: InstallerInfo | null = null;
  let deploymentJobs: DeploymentJob[] = [];

  let showDeployForm = false;
  let deployRealmName = '';
  let deployDisplayName = '';
  let deployDescription = '';
  let deployNetwork = 'staging';
  let deploySubmitting = false;
  let deployError = '';
  let deploySuccess = '';

  let expandedJobId: string | null = null;
  let logsLoading = false;
  let installerLogs: string = '';
  let deployerLogs: string = '';
  let activeLogTab: 'installer' | 'deployer' = 'installer';

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
      ]);

      if (results[0].status === 'fulfilled' && (results[0].value as any)?.ok) {
        healthy = true;
      }

      if (results[1].status === 'fulfilled') {
        const raw = results[1].value as any;
        if (raw && typeof raw === 'object' && 'version' in raw) {
          info = raw as InstallerInfo;
        } else {
          info = null;
        }
      }

      if (results[2].status === 'fulfilled') {
        const raw = results[2].value as any;
        const j =
          raw?.Ok?.jobs ||
          (raw && raw.jobs) ||
          [];
        deploymentJobs = j || [];
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

  async function toggleLogs(jobId: string) {
    if (expandedJobId === jobId) {
      expandedJobId = null;
      return;
    }
    expandedJobId = jobId;
    installerLogs = '';
    deployerLogs = '';
    activeLogTab = 'installer';
    logsLoading = true;

    try {
      const [instResult, deplResult] = await Promise.allSettled([
        fetchInstallerLogs(jobId),
        fetchDeployerLogs(jobId),
      ]);
      if (instResult.status === 'fulfilled') installerLogs = instResult.value;
      else installerLogs = `Error: ${(instResult as any).reason}`;
      if (deplResult.status === 'fulfilled') deployerLogs = deplResult.value;
      else deployerLogs = `Error: ${(deplResult as any).reason}`;
    } finally {
      logsLoading = false;
    }
  }

  async function fetchInstallerLogs(jobId: string): Promise<string> {
    try {
      const entries = await installerActor.get_canister_logs(
        [],       // from_entry
        [],       // max_entries
        [],       // min_level
        [jobId],  // logger_name = job_id
      );
      if (!entries || entries.length === 0) return '(no installer logs for this job)';
      return entries
        .map((e: any) => {
          const ts = new Date(Number(e.timestamp) / 1_000_000).toISOString();
          return `${ts} [${e.level}] ${e.message}`;
        })
        .join('\n');
    } catch (e: any) {
      return `Failed to fetch installer logs: ${e.message || e}`;
    }
  }

  async function fetchDeployerLogs(jobId: string): Promise<string> {
    const base = CONFIG.deploy_service_url;
    if (!base) return '(deploy service URL not configured)';
    try {
      const resp = await fetch(`${base}/api/logs/${encodeURIComponent(jobId)}`);
      if (resp.status === 404) return '(no deployer logs for this job)';
      if (!resp.ok) return `HTTP ${resp.status}: ${await resp.text()}`;
      return await resp.text();
    } catch (e: any) {
      return `Failed to fetch deployer logs: ${e.message || e}`;
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

  function toNum(v: any): number {
    if (typeof v === 'bigint') return Number(v);
    return Number(v) || 0;
  }

  function verifiedBadge(v: any): string {
    const n = toNum(v);
    if (n === 1) return 'badge-success';
    if (n === -1) return 'badge-danger';
    return 'badge-neutral';
  }

  function verifiedLabel(v: any): string {
    const n = toNum(v);
    if (n === 1) return 'Verified';
    if (n === -1) return 'Failed';
    return 'Pending';
  }

  function formatTime(ts: any): string {
    const n = toNum(ts);
    if (!n) return '—';
    return new Date(n * 1000).toLocaleString();
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
          <option value="test">Test</option>
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
            <th>Logs</th>
          </tr>
        </thead>
        <tbody>
          {#each deploymentJobs as job}
            <tr>
              <td><code class="id-cell">{job.job_id || '—'}</code></td>
              <td><span class="badge {statusBadgeClass(job.status)}">{job.status}</span></td>
              <td>{job.network || '—'}</td>
              <td><code class="id-cell">{job.backend_canister_id || '—'}</code></td>
              <td>
                <span class="badge {verifiedBadge(job.wasm_verified)}">
                  {verifiedLabel(job.wasm_verified)}
                </span>
              </td>
              <td>{formatTime(job.created_at)}</td>
              <td>
                <button
                  class="btn btn-sm btn-outline"
                  on:click={() => toggleLogs(job.job_id)}
                >
                  {expandedJobId === job.job_id ? 'Hide' : 'Logs'}
                </button>
              </td>
            </tr>
            {#if expandedJobId === job.job_id}
              <tr class="logs-row">
                <td colspan="7">
                  <div class="logs-panel">
                    <div class="log-tabs">
                      <button
                        class="log-tab"
                        class:active={activeLogTab === 'installer'}
                        on:click={() => activeLogTab = 'installer'}
                      >Installer Canister</button>
                      <button
                        class="log-tab"
                        class:active={activeLogTab === 'deployer'}
                        on:click={() => activeLogTab = 'deployer'}
                      >Deploy Service</button>
                    </div>
                    {#if logsLoading}
                      <div class="log-content"><span class="spinner"></span> Loading logs...</div>
                    {:else}
                      <pre class="log-content">{activeLogTab === 'installer' ? installerLogs : deployerLogs}</pre>
                    {/if}
                  </div>
                </td>
              </tr>
            {/if}
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
  .id-cell {
    font-size: 0.78rem;
    word-break: break-all;
    max-width: 18ch;
    display: inline-block;
  }
  .btn-outline {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
    cursor: pointer;
    padding: 0.2rem 0.5rem;
    border-radius: 0.3rem;
    font-size: 0.78rem;
  }
  .btn-outline:hover {
    background: var(--surface);
  }
  .logs-row td {
    padding: 0 !important;
  }
  .logs-panel {
    border-top: 1px solid var(--border);
    background: var(--surface, #1a1a2e);
  }
  .log-tabs {
    display: flex;
    border-bottom: 1px solid var(--border);
  }
  .log-tab {
    padding: 0.45rem 1rem;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 0.82rem;
    border-bottom: 2px solid transparent;
  }
  .log-tab.active {
    color: var(--text);
    border-bottom-color: var(--primary, #6366f1);
  }
  .log-content {
    padding: 0.75rem 1rem;
    font-size: 0.78rem;
    line-height: 1.5;
    max-height: 20rem;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
    font-family: 'Fira Code', 'JetBrains Mono', monospace;
  }
</style>
