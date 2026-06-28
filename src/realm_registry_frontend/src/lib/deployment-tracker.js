import { browser } from '$app/environment';
import {
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

/** @returns {Promise<object|null>} deployment row or null if job missing */
export async function loadDeploymentRow(jobId) {
  if (!browser || !jobId) return null;
  const raw = await fetchDeploymentJobStatus(jobId);
  if (!raw) return null;
  return installerJobToDeploymentRow(raw);
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
