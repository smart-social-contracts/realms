import { browser } from '$app/environment';
import {
  fetchDeployTaskStatus,
  fetchDeploymentJobStatus,
  installerJobToDeploymentRow,
  isActiveQueueStatus,
} from '$lib/installer-queue.js';
import { recordDeploymentStageObservation } from '$lib/deployment-stage-timing.js';

/** Canonical URL for tracking a single deployment job. */
export function deploymentJobUrl(jobId) {
  const id = (jobId || '').trim();
  if (!id) return '/my-dashboard?tab=realms';
  return `/my-dashboard/deployments?job=${encodeURIComponent(id)}`;
}

function shouldFetchDeployTask(job) {
  if (!job) return false;
  const st = (job.status || '').toLowerCase();
  if (st === 'extensions' || st === 'registering') return true;
  return Boolean((job.ext_deploy_task_id || '').trim());
}

/** @returns {Promise<object|null>} deployment row or null if job missing */
export async function loadDeploymentRow(jobId) {
  if (!browser || !jobId) return null;
  const raw = await fetchDeploymentJobStatus(jobId);
  if (!raw) return null;
  let deployTask = null;
  if (shouldFetchDeployTask(raw)) {
    deployTask = await fetchDeployTaskStatus(jobId);
  }
  return installerJobToDeploymentRow(raw, deployTask);
}

/**
 * Poll a deployment job until terminal. Calls `onUpdate(row)` each tick.
 * @returns {() => void} stop polling
 */
export function startDeploymentJobPolling(jobId, onUpdate, intervalMs = 10000) {
  if (!browser || !jobId) return () => {};

  let stopped = false;

  async function tick() {
    if (stopped) return;
    try {
      const row = await loadDeploymentRow(jobId);
      if (!row) return;
      recordDeploymentStageObservation(jobId, row);
      onUpdate(row);
      if (!isActiveQueueStatus(row.raw_status)) {
        stop();
      }
    } catch (e) {
      console.error('Deployment poll error:', e);
    }
  }

  tick();
  const timer = setInterval(tick, intervalMs);

  function stop() {
    if (stopped) return;
    stopped = true;
    clearInterval(timer);
  }

  return stop;
}
