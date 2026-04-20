<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { installerActor } from '$lib/canisters';
  import type { DeployStatusRecord, DeployStepRecord } from '$lib/types';

  let loading = true;
  let error = '';
  let deployStatus: DeployStatusRecord | null = null;

  $: deployId = $page.params.deployId;

  onMount(async () => {
    try {
      const raw = await installerActor.get_deploy_status(deployId);
      const parsed = typeof raw === 'string' ? JSON.parse(raw) : (raw?.Ok ? JSON.parse(raw.Ok) : raw);
      deployStatus = parsed;
    } catch (e: any) {
      error = e.message || 'Failed to load deployment status';
    } finally {
      loading = false;
    }
  });

  function statusBadgeClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'completed': case 'success': case 'done': return 'badge-success';
      case 'in_progress': case 'in-progress': case 'running': return 'badge-warning';
      case 'failed': case 'error': return 'badge-danger';
      case 'pending': case 'queued': case 'waiting': return 'badge-info';
      case 'skipped': return 'badge-neutral';
      default: return 'badge-neutral';
    }
  }

  function stepIcon(status: string): string {
    switch (status?.toLowerCase()) {
      case 'completed': case 'success': case 'done': return '✓';
      case 'in_progress': case 'in-progress': case 'running': return '●';
      case 'failed': case 'error': return '✗';
      case 'skipped': return '—';
      default: return '○';
    }
  }
</script>

<div class="breadcrumb">
  <a href="/installer">Installer</a>
  <span class="sep">/</span>
  <span>{deployId}</span>
</div>

<h1 class="page-title">Deployment Details</h1>

{#if loading}
  <div class="empty-state"><span class="spinner"></span> Loading deployment status...</div>
{:else if error}
  <div class="card" style="border-color: var(--danger); color: var(--danger);">{error}</div>
{:else if deployStatus}
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-value" style="font-size:1rem; font-family:monospace">{deployStatus.deploy_id}</div>
      <div class="stat-label">Deploy ID</div>
    </div>
    {#if deployStatus.realm_name}
      <div class="stat-card">
        <div class="stat-value" style="font-size:1.1rem">{deployStatus.realm_name}</div>
        <div class="stat-label">Realm</div>
      </div>
    {/if}
    <div class="stat-card">
      <div class="stat-value">
        <span class="badge {statusBadgeClass(deployStatus.status)}">{deployStatus.status}</span>
      </div>
      <div class="stat-label">Overall Status</div>
    </div>
  </div>

  {#if deployStatus.error}
    <div class="card error-card">
      <strong>Error:</strong> {deployStatus.error}
    </div>
  {/if}

  <h2 style="font-size: 1.1rem; margin: 1.5rem 0 0.75rem;">
    Steps ({deployStatus.steps?.length ?? 0})
  </h2>

  {#if deployStatus.steps && deployStatus.steps.length > 0}
    <div class="steps">
      {#each deployStatus.steps as step, i}
        <div class="step" class:step-active={['in_progress','in-progress','running'].includes(step.status?.toLowerCase())}>
          <div class="step-indicator">
            <span class="step-icon {statusBadgeClass(step.status)}">{stepIcon(step.status)}</span>
            {#if i < deployStatus.steps.length - 1}
              <div class="step-line"></div>
            {/if}
          </div>
          <div class="step-body">
            <div class="step-header">
              <span class="step-name">{step.name}</span>
              <span class="badge {statusBadgeClass(step.status)}">{step.status}</span>
            </div>
            {#if step.started_at || step.completed_at}
              <div class="step-times">
                {#if step.started_at}<span>Started: {step.started_at}</span>{/if}
                {#if step.completed_at}<span>Completed: {step.completed_at}</span>{/if}
              </div>
            {/if}
            {#if step.log}
              <pre class="step-log">{step.log}</pre>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="empty-state">No step information available.</div>
  {/if}
{:else}
  <div class="empty-state">Deployment not found.</div>
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

  .error-card {
    border-color: var(--danger);
    color: var(--danger);
    margin-bottom: 1rem;
  }

  .steps { display: flex; flex-direction: column; }
  .step {
    display: flex;
    gap: 0.85rem;
    min-height: 3rem;
  }
  .step-active { background: var(--surface-2); border-radius: 0.5rem; padding: 0.5rem; margin: -0.5rem; margin-bottom: 0; }

  .step-indicator {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    width: 1.5rem;
  }
  .step-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
  }
  .step-line {
    width: 2px;
    flex: 1;
    background: var(--border);
    margin: 0.25rem 0;
  }

  .step-body {
    flex: 1;
    padding-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .step-header { display: flex; align-items: center; gap: 0.5rem; }
  .step-name { font-weight: 600; font-size: 0.9rem; }
  .step-times { font-size: 0.78rem; color: var(--text-faint); display: flex; gap: 1rem; }
  .step-log {
    margin: 0.35rem 0 0;
    padding: 0.65rem 0.85rem;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 0.375rem;
    font-size: 0.78rem;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
  }
</style>
