<script>
  import { onDestroy, onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import DeploymentProgress from '$lib/components/DeploymentProgress.svelte';
  import DeploymentManifestPanel from '$lib/components/DeploymentManifestPanel.svelte';
  import { deploymentJobUrl, loadDeploymentRow, startDeploymentJobPolling } from '$lib/deployment-tracker.js';
  import { fetchDeploymentManifest } from '$lib/installer-queue.js';
  import { recordDeploymentStageObservation } from '$lib/deployment-stage-timing.js';
  import {
    findDraftForDeployment,
    draftResumeUrl,
    isFailedDeployment,
    listWizardDrafts,
  } from '$lib/wizard-drafts.js';
  import { deleteDeploymentJob } from '$lib/installer-queue.js';
  import ConfirmModal from '$lib/components/ConfirmModal.svelte';

  let userPrincipal = null;
  let loading = true;
  let loadError = null;
  let deployment = null;
  let wizardDrafts = [];
  let deleting = false;
  let deleteError = null;
  let showDeleteConfirm = false;
  let stopPolling = () => {};
  let manifestRaw = null;
  let manifestLoading = false;
  let manifestError = null;

  async function loadManifest() {
    if (!jobId || !userPrincipal) return;
    manifestLoading = true;
    manifestError = null;
    try {
      manifestRaw = await fetchDeploymentManifest(jobId);
    } catch (err) {
      manifestRaw = null;
      manifestError = err?.message || 'Could not load manifest.';
    } finally {
      manifestLoading = false;
    }
  }

  $: jobId = ($page.url.searchParams.get('job') || '').trim();
  $: linkedDraft = deployment ? findDraftForDeployment(wizardDrafts, deployment) : null;
  $: editDraftHref = linkedDraft
    ? `${draftResumeUrl(linkedDraft, 6)}&edit=1`
    : '/create-realm';
  $: retryDeployHref = linkedDraft ? draftResumeUrl(linkedDraft, 6) : '/create-realm';

  function formatDate(dateValue) {
    const n = Number(dateValue || 0);
    if (!Number.isFinite(n) || n <= 0) return '';
    const ms = n > 1e12 ? n : n * 1000;
    return new Date(ms).toLocaleString();
  }

  async function refresh() {
    if (!jobId) {
      loadError = 'Missing deployment job id.';
      loading = false;
      return;
    }
    try {
      const row = await loadDeploymentRow(jobId);
      if (!row) {
        loadError = 'Deployment not found.';
        deployment = null;
        return;
      }
      if (userPrincipal && row.caller_principal && row.caller_principal !== userPrincipal.toText()) {
        loadError = 'This deployment belongs to another account.';
        deployment = null;
        return;
      }
      loadError = null;
      deployment = row;
      recordDeploymentStageObservation(jobId, row);
    } catch (err) {
      console.error('Failed to load deployment:', err);
      loadError = err?.message || 'Failed to load deployment.';
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    if (!browser) return;

    const { isAuthenticated, getPrincipal, login: authLogin } = await import('$lib/auth.js');
    const { TEST_MODE_II_BYPASS } = await import('$lib/config.js');

    let authenticated = false;
    if (TEST_MODE_II_BYPASS) {
      const result = await authLogin();
      authenticated = !!result.principal;
    } else {
      authenticated = await isAuthenticated();
    }

    if (!authenticated) {
      goto('/');
      return;
    }

    userPrincipal = await getPrincipal();
    try {
      wizardDrafts = await listWizardDrafts();
    } catch (_) {
      wizardDrafts = [];
    }
    await refresh();
    await loadManifest();

    if (jobId && deployment?.progress?.isActive) {
      stopPolling = startDeploymentJobPolling(jobId, async (row) => {
        deployment = row;
        if (!row.progress?.isActive) {
          try {
            wizardDrafts = await listWizardDrafts();
          } catch (_) { /* non-fatal */ }
          if (!manifestRaw && !manifestLoading) {
            await loadManifest();
          }
        }
      });
    }
  });

  onDestroy(() => {
    stopPolling();
  });

  async function removeFailedDeployment() {
    if (!jobId || !deployment || deleting) return;
    showDeleteConfirm = true;
  }

  async function confirmRemoveFailedDeployment() {
    if (!jobId || !deployment || deleting) return;
    deleting = true;
    deleteError = null;
    try {
      await deleteDeploymentJob(jobId);
      showDeleteConfirm = false;
      await goto('/my-dashboard?tab=realms');
    } catch (err) {
      console.error('Failed to delete deployment:', err);
      deleteError = err?.message || 'Failed to delete deployment.';
    } finally {
      deleting = false;
    }
  }
</script>

<svelte:head>
  <title>{deployment?.realm_name ? `${deployment.realm_name} — Deployment` : 'Deployment'} · Realms</title>
</svelte:head>

<div class="page">
  <header class="page-header">
    <a href="/my-dashboard?tab=realms" class="back-link">← My Dashboard</a>
    <h1>Deployment status</h1>
    {#if deployment?.realm_name}
      <p class="subtitle">{deployment.realm_name}</p>
    {/if}
  </header>

  {#if !jobId}
    <div class="card error-card">
      <p>No deployment job specified.</p>
      <a href="/my-dashboard?tab=realms" class="btn btn-outline">Back to My Realms</a>
    </div>
  {:else if loading}
    <div class="card loading-card">
      <div class="spinner"></div>
      <p>Loading deployment…</p>
    </div>
  {:else if loadError}
    <div class="card error-card">
      <p>{loadError}</p>
      <a href="/my-dashboard?tab=realms" class="btn btn-outline">Back to My Realms</a>
    </div>
  {:else if deployment}
    <div class="card">
      <div class="meta-row">
        <span class="meta-label">Job</span>
        <code class="job-id">{deployment.deployment_id}</code>
      </div>
      {#if deployment.created_at}
        <div class="meta-row">
          <span class="meta-label">Started</span>
          <span>{formatDate(deployment.created_at)}</span>
        </div>
      {/if}
      {#if deployment.progress?.finishedAtMs}
        <div class="meta-row">
          <span class="meta-label">Finished</span>
          <span>{formatDate(deployment.progress.finishedAtMs)}</span>
        </div>
      {/if}
      {#if deployment.progress?.totalDurationLabel}
        <div class="meta-row">
          <span class="meta-label">Total duration</span>
          <span>
            {deployment.progress.totalDurationLabel}{#if deployment.progress.durationsEstimated} (estimated){/if}
          </span>
        </div>
      {/if}

      <DeploymentProgress progress={deployment.progress} variant="full" showSteps={true} />

      <DeploymentManifestPanel
        manifestRaw={manifestRaw}
        frontendCanisterId={deployment.frontend_canister_id || ''}
        loading={manifestLoading}
        error={manifestError}
      />

      {#if isFailedDeployment(deployment)}
        <div class="failure-panel">
          <p class="failure-title">Deployment did not complete</p>
          {#if deployment.error}
            <p class="failure-error">{deployment.error}</p>
          {/if}
          <p class="failure-hint">
            Your wizard draft is available again. Edit your configuration or retry with the same settings.
          </p>
        </div>
      {/if}

      <div class="actions">
        {#if deployment.raw_status === 'completed' && deployment.realm_url}
          <a href={deployment.realm_url} target="_blank" rel="noopener noreferrer" class="btn btn-primary">
            Visit Realm →
          </a>
        {/if}
        {#if isFailedDeployment(deployment)}
          <a href={editDraftHref} class="btn btn-primary">Edit configuration</a>
          <a href={retryDeployHref} class="btn btn-outline">Retry deployment</a>
          <button type="button" class="btn btn-danger" disabled={deleting} on:click={removeFailedDeployment}>
            {deleting ? 'Deleting…' : 'Delete'}
          </button>
        {/if}
        {#if deleteError}
          <p class="delete-error">{deleteError}</p>
        {/if}
        <a href="/my-dashboard?tab=realms" class="btn btn-outline">All deployments</a>
      </div>

      {#if deployment.progress?.isActive}
        <p class="refresh-note">This page refreshes automatically every 10 seconds.</p>
      {/if}
    </div>
  {/if}

  <ConfirmModal
    open={showDeleteConfirm}
    title="Remove failed deployment?"
    message={deployment
      ? `Remove "${deployment.realm_name || deployment.deployment_id}" from your dashboard? This cannot be undone.`
      : 'Remove this failed deployment from your dashboard?'}
    confirmLabel="Remove"
    cancelLabel="Cancel"
    variant="danger"
    loading={deleting}
    on:cancel={() => { showDeleteConfirm = false; }}
    on:confirm={confirmRemoveFailedDeployment}
  />
</div>

<style>
  .page {
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }

  .page-header {
    margin-bottom: 1.5rem;
  }

  .back-link {
    display: inline-block;
    margin-bottom: 0.75rem;
    color: #525252;
    text-decoration: none;
    font-size: 0.875rem;
  }

  .back-link:hover {
    color: #171717;
    text-decoration: underline;
  }

  h1 {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 700;
    color: #171717;
  }

  .subtitle {
    margin: 0.25rem 0 0;
    color: #525252;
    font-size: 1rem;
  }

  .card {
    background: #fff;
    border: 1px solid #e5e5e5;
    border-radius: 0.75rem;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .meta-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-size: 0.875rem;
    color: #525252;
  }

  .meta-label {
    font-weight: 600;
    color: #737373;
  }

  .job-id {
    font-size: 0.8125rem;
    word-break: break-all;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.25rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    text-decoration: none;
    border: 1px solid transparent;
  }

  .btn-primary {
    background: #171717;
    color: #fff;
  }

  .btn-outline {
    background: #fff;
    color: #171717;
    border-color: #d4d4d4;
  }

  .btn-danger {
    background: #fff;
    color: #b91c1c;
    border-color: #fecaca;
  }

  .btn-danger:hover:not(:disabled) {
    background: #fef2f2;
  }

  .delete-error {
    margin: 0;
    width: 100%;
    font-size: 0.8125rem;
    color: #b91c1c;
  }

  .refresh-note {
    margin: 0;
    font-size: 0.8125rem;
    color: #737373;
  }

  .failure-panel {
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
  }

  .failure-title {
    margin: 0 0 0.35rem;
    font-weight: 600;
    color: #991b1b;
  }

  .failure-error {
    margin: 0 0 0.35rem;
    font-size: 0.875rem;
    color: #7f1d1d;
    word-break: break-word;
  }

  .failure-hint {
    margin: 0;
    font-size: 0.8125rem;
    color: #7f1d1d;
  }

  .loading-card,
  .error-card {
    align-items: center;
    text-align: center;
  }

  .spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #e5e5e5;
    border-top-color: #525252;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
