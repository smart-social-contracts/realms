import { browser, building } from '$app/environment';
import { CONFIG } from '$lib/config.js';

const buildingOrTesting = building || process.env.NODE_ENV === 'test';

function isLocalDevelopment() {
  if (!browser || typeof window === 'undefined') return false;
  return (
    window.location.hostname.includes('localhost') ||
    window.location.hostname.includes('127.0.0.1')
  );
}

function resultOk(raw) {
  if (raw == null) return null;
  if (typeof raw === 'object' && 'Ok' in raw) return raw.Ok;
  return null;
}

async function createInstallerActor() {
  const { createActor, canisterId } = await import('declarations/realm_installer');
  const { HttpAgent } = await import('@dfinity/agent');
  const agent = new HttpAgent();
  if (isLocalDevelopment()) {
    try {
      await agent.fetchRootKey();
    } catch (_) {
      /* non-fatal */
    }
  }
  const id = CONFIG.realm_installer_canister_id || canisterId;
  if (!id) {
    throw new Error('realm_installer canister id is not configured');
  }
  return createActor(id, { agent });
}

/** @returns {Promise<object[]>} */
export async function fetchDeploymentJobsFromInstaller() {
  if (buildingOrTesting || !browser) return [];
  const actor = await createInstallerActor();
  const raw = await actor.list_deployment_jobs();
  if (raw == null) return [];
  if (typeof raw === 'object' && 'Err' in raw) return [];
  const ok = resultOk(raw);
  return (ok && ok.jobs) || [];
}

/** @returns {Promise<object|null>} */
export async function fetchDeploymentJobStatus(jobId) {
  if (buildingOrTesting || !browser || !jobId) return null;
  const actor = await createInstallerActor();
  const raw = await actor.get_deployment_job_status(jobId);
  if (raw == null) return null;
  if (typeof raw === 'object' && 'Err' in raw) return null;
  return resultOk(raw);
}

/**
 * Map installer job to the shape previously returned by the management HTTP API
 * so dashboard templates stay stable.
 */
export function installerJobToDeploymentRow(job) {
  const st = (job.status || '').toLowerCase();
  let uiStatus = st;
  if (
    st === 'deploying' ||
    st === 'verifying' ||
    st === 'extensions' ||
    st === 'registering'
  ) {
    uiStatus = 'in_progress';
  }
  const frontend = job.frontend_canister_id || '';
  const realmUrl = frontend ? `https://${frontend}.icp0.io` : null;
  return {
    deployment_id: job.job_id,
    realm_name: job.realm_name || job.job_id,
    status: uiStatus,
    raw_status: st,
    created_at: job.created_at || 0,
    completed_at: job.completed_at || null,
    realm_url: realmUrl,
    error: job.error || null,
    credits_charged: 0,
  };
}

export function isActiveQueueStatus(status) {
  const s = (status || '').toLowerCase();
  return (
    s === 'pending' ||
    s === 'deploying' ||
    s === 'verifying' ||
    s === 'extensions' ||
    s === 'registering'
  );
}
