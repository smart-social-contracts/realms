/** Pipeline stages shown to users (order matters). */
export const DEPLOYMENT_PIPELINE = [
  {
    id: 'queue',
    label: 'Queued',
    description: 'Your deployment request is in the queue.',
  },
  {
    id: 'provision',
    label: 'Creating canisters',
    description: 'Provisioning backend and frontend canisters on the Internet Computer.',
  },
  {
    id: 'verify',
    label: 'Verifying software',
    description: 'Checking that installed software matches the authorized release.',
  },
  {
    id: 'extensions',
    label: 'Installing extensions',
    description: 'Deploying codex, extensions, and realm configuration.',
  },
  {
    id: 'register',
    label: 'Registering realm',
    description: 'Recording your realm in the on-chain registry.',
  },
  {
    id: 'complete',
    label: 'Complete',
    description: 'Your realm is live.',
  },
];

const STATUS_STAGE_INDEX = {
  pending: 0,
  provisioning: 1,
  deploying: 1,
  verifying: 2,
  extensions: 3,
  registering: 4,
  completed: 5,
  failed: 5,
  failed_verification: 2,
  cancelled: 0,
};

const TERMINAL_STATUSES = new Set([
  'completed',
  'failed',
  'failed_verification',
  'cancelled',
]);

const FAILED_STATUSES = new Set(['failed', 'failed_verification', 'cancelled']);

/** Relative effort per pipeline stage (queue → register). Used when we lack live observations. */
const STAGE_DURATION_WEIGHTS = [1, 3, 2, 4, 3];

/** Weighted work units for percent calculation (not wall-clock). */
const UNITS = {
  queue: 1,
  provisionBackend: 2,
  provisionFrontend: 2,
  provisionFinalize: 1,
  verify: 1,
  register: 2,
  extensionStep: 1,
};

/**
 * @param {object} job
 * @param {object|null|undefined} deployTask
 * @returns {{ completed: number, total: number, extensionTotal: number, extensionCompleted: number }}
 */
export function computeDeploymentUnits(job, deployTask) {
  const status = (job.status || job.raw_status || '').toLowerCase();
  let completed = 0;
  let total = 0;

  total += UNITS.queue;
  if (status !== 'pending') completed += UNITS.queue;

  total += UNITS.provisionBackend + UNITS.provisionFrontend + UNITS.provisionFinalize;
  if ((job.backend_canister_id || '').trim()) completed += UNITS.provisionBackend;
  if ((job.frontend_canister_id || '').trim()) completed += UNITS.provisionFrontend;
  if (Number(job.assets_verified)) completed += UNITS.provisionFinalize;

  total += UNITS.verify;
  if (Number(job.wasm_verified) && Number(job.assets_verified)) {
    completed += UNITS.verify;
  } else if (['extensions', 'registering', 'completed'].includes(status)) {
    completed += UNITS.verify;
  }

  const extensionTotal = Math.max(
    Number(deployTask?.total_count ?? 0),
    Number(job.expected_step_count ?? 0),
    Array.isArray(deployTask?.steps) ? deployTask.steps.length : 0,
  );
  total += extensionTotal * UNITS.extensionStep;

  let extensionCompleted = Number(deployTask?.completed_count ?? 0);
  if (!deployTask && ['registering', 'completed'].includes(status)) {
    extensionCompleted = extensionTotal;
  }
  extensionCompleted = Math.min(extensionCompleted, extensionTotal);
  completed += extensionCompleted * UNITS.extensionStep;

  total += UNITS.register;
  if (status === 'completed') {
    completed += UNITS.register;
  } else if (status === 'registering') {
    completed += Math.ceil(UNITS.register / 2);
  }

  return { completed, total, extensionTotal, extensionCompleted };
}

/**
 * @param {object} job
 * @param {object|null|undefined} deployTask
 * @returns {number}
 */
export function computeDeploymentPercent(job, deployTask) {
  const status = (job.status || job.raw_status || '').toLowerCase();
  if (status === 'completed') return 100;

  const { completed, total } = computeDeploymentUnits(job, deployTask);
  if (total <= 0) return 0;

  const raw = Math.round((100 * completed) / total);
  if (FAILED_STATUSES.has(status)) {
    return Math.max(0, Math.min(raw, 99));
  }
  return Math.max(0, Math.min(raw, 99));
}

export function toTimestampMs(value) {
  if (value == null || value === '') return null;
  const n = typeof value === 'bigint' ? Number(value) : Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n > 1e12 ? n : n * 1000;
}

/** @param {number} ms */
export function formatDuration(ms) {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return '';
  if (ms < 1000) return '<1s';
  const sec = Math.round(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const remSec = sec % 60;
  if (min < 60) return remSec > 0 ? `${min}m ${remSec}s` : `${min}m`;
  const hr = Math.floor(min / 60);
  const remMin = min % 60;
  return remMin > 0 ? `${hr}h ${remMin}m` : `${hr}h`;
}

function stageIndexForJob(job) {
  const status = (job.status || job.raw_status || '').toLowerCase();
  let index = STATUS_STAGE_INDEX[status] ?? 0;

  if (status === 'pending' && (job.backend_canister_id || job.frontend_canister_id)) {
    index = Math.max(index, 1);
  }

  return { status, index };
}

function shortId(id) {
  const s = (id || '').trim();
  return s.length > 8 ? `${s.slice(0, 5)}…` : s;
}

/**
 * @param {object|null|undefined} deployTask
 * @returns {Array<{ label: string, kind: string, status: string, error: string|null, state: string }>}
 */
export function buildExtensionSubSteps(deployTask) {
  const steps = deployTask?.steps;
  if (!Array.isArray(steps) || !steps.length) return [];

  return steps.map((step) => {
    const st = (step.status || '').toLowerCase();
    let state = 'upcoming';
    if (st === 'completed') state = 'done';
    else if (st === 'failed') state = 'failed';
    else if (st === 'running') state = 'active';

    const kind = (step.kind || '').toLowerCase();
    let label = step.label || step.kind || 'step';
    if (kind === 'grant_frontend_access') {
      label = 'Grant frontend access';
    } else if (kind === 'extension') {
      label = `Extension: ${step.label || 'unknown'}`;
    } else if (kind === 'codex') {
      label = `Codex: ${step.label || 'unknown'}`;
    }

    return {
      label,
      kind,
      status: st,
      error: (step.error || '').trim() || null,
      state,
    };
  });
}

function stageDescription(status, job, stage, deployTask) {
  const backend = (job.backend_canister_id || '').trim();
  const frontend = (job.frontend_canister_id || '').trim();
  const { extensionTotal, extensionCompleted } = computeDeploymentUnits(job, deployTask);

  if (status === 'provisioning') {
    const parts = [];
    if (backend) parts.push(`backend ${shortId(backend)} ready`);
    if (frontend) parts.push(`frontend ${shortId(frontend)} ready`);
    if (parts.length) {
      const tail = Number(job.assets_verified)
        ? 'Finalizing stand configuration…'
        : frontend
          ? 'Uploading frontend assets and verifying…'
          : 'Creating frontend canister…';
      return `${parts.join(', ')}. ${tail}`;
    }
    return 'Provisioning canisters via Casals on the Internet Computer.';
  }

  if (status === 'pending' && !backend && !frontend) {
    return stage.description;
  }

  if (status === 'pending' || status === 'deploying') {
    const parts = [];
    if (backend) parts.push(`backend ${shortId(backend)}`);
    if (frontend) parts.push(`frontend ${shortId(frontend)}`);
    if (parts.length) {
      return `${stage.description} (${parts.join(', ')})`;
    }
  }

  if (status === 'extensions') {
    if (extensionTotal > 0) {
      return `Installing extensions and codex (${extensionCompleted}/${extensionTotal} steps complete).`;
    }
    return 'Installing codex, extensions, and realm configuration.';
  }

  if (status === 'registering') {
    return 'Finalizing registration and settling credits.';
  }

  if (status === 'failed_verification') {
    return 'Software verification failed — the installed build did not match the expected release.';
  }

  return stage.description;
}

/**
 * @param {Array<{ id: string, state: string }>} stages
 * @param {number} totalMs
 * @param {number} terminalStageIndex - last stage that ran (inclusive)
 */
function estimateStageDurationsMs(stages, totalMs, terminalStageIndex) {
  const indices = stages
    .map((stage, i) => ({ stage, i }))
    .filter(
      ({ stage, i }) =>
        stage.id !== 'complete' &&
        i <= terminalStageIndex &&
        (stage.state === 'done' || stage.state === 'failed' || stage.state === 'active'),
    );

  if (!indices.length || totalMs <= 0) return {};

  const weights = indices.map(({ i }) => STAGE_DURATION_WEIGHTS[i] ?? 1);
  const weightSum = weights.reduce((a, b) => a + b, 0);
  const out = {};
  indices.forEach(({ i }, idx) => {
    out[i] = Math.max(0, Math.round((totalMs * weights[idx]) / weightSum));
  });
  return out;
}

/**
 * @param {Array<{ id: string, state: string }>} stages
 * @param {number} startMs
 * @param {number} endMs
 * @param {Record<number, number>|null} observedStarts - stage index → timestamp ms
 */
function resolveStageDurationsMs(stages, startMs, endMs, observedStarts) {
  const durations = {};
  const pipelineStages = stages.filter((s) => s.id !== 'complete');

  if (observedStarts && Object.keys(observedStarts).length > 0) {
    const sorted = pipelineStages
      .map((stage, i) => ({ stage, i }))
      .filter(({ stage }) => stage.state !== 'upcoming');

    for (let k = 0; k < sorted.length; k++) {
      const { i, stage } = sorted[k];
      const stageStart = observedStarts[i] ?? (k === 0 ? startMs : observedStarts[sorted[k - 1].i]);
      let stageEnd;
      if (stage.state === 'active') {
        stageEnd = endMs;
      } else {
        const next = sorted[k + 1];
        stageEnd = next ? (observedStarts[next.i] ?? endMs) : endMs;
      }
      if (stageStart && stageEnd && stageEnd >= stageStart) {
        durations[i] = stageEnd - stageStart;
      }
    }
    if (Object.keys(durations).length) return { durations, estimated: false };
  }

  const terminalStageIndex = pipelineStages.reduce(
    (max, stage, i) =>
      stage.state === 'done' || stage.state === 'failed' || stage.state === 'active'
        ? Math.max(max, i)
        : max,
    0,
  );
  return {
    durations: estimateStageDurationsMs(stages, Math.max(0, endMs - startMs), terminalStageIndex),
    estimated: true,
  };
}

/**
 * @param {object} job - installer job view or deployment row
 * @param {{ observedStageStarts?: Record<number, number>|null, deployTask?: object|null }} [options]
 * @returns {object} progress view model for UI
 */
export function getDeploymentProgress(job, options = {}) {
  const deployTask = options.deployTask ?? null;
  const { status, index: stageIndex } = stageIndexForJob(job);
  const isTerminal = TERMINAL_STATUSES.has(status);
  const isFailed = FAILED_STATUSES.has(status);
  const isComplete = status === 'completed';

  const activeIndex = isComplete
    ? DEPLOYMENT_PIPELINE.length - 1
    : isFailed
      ? Math.min(stageIndex, DEPLOYMENT_PIPELINE.length - 2)
      : stageIndex;

  const currentStage = DEPLOYMENT_PIPELINE[activeIndex] || DEPLOYMENT_PIPELINE[0];
  const percent = computeDeploymentPercent(job, deployTask);
  const { extensionTotal, extensionCompleted } = computeDeploymentUnits(job, deployTask);
  const subSteps = buildExtensionSubSteps(deployTask);

  const stages = DEPLOYMENT_PIPELINE.map((stage, i) => {
    let state = 'upcoming';
    if (isComplete) {
      state = 'done';
    } else if (isFailed && i === activeIndex) {
      state = 'failed';
    } else if (i < activeIndex) {
      state = 'done';
    } else if (i === activeIndex) {
      state = isFailed ? 'failed' : 'active';
    }
    return { ...stage, state };
  });

  const startedAtMs = toTimestampMs(job.created_at);
  const finishedAtMs = isTerminal ? toTimestampMs(job.completed_at) ?? Date.now() : null;
  const endMs = finishedAtMs ?? Date.now();
  const totalDurationMs =
    startedAtMs && endMs >= startedAtMs ? endMs - startedAtMs : null;

  const { durations: stageDurationMs, estimated: durationsEstimated } =
    startedAtMs != null
      ? resolveStageDurationsMs(stages, startedAtMs, endMs, options.observedStageStarts ?? null)
      : { durations: {}, estimated: true };

  const stagesWithTiming = stages.map((stage, i) => {
    const durationMs = stageDurationMs[i];
    return {
      ...stage,
      durationMs: durationMs ?? null,
      durationLabel: durationMs != null ? formatDuration(durationMs) : '',
      durationEstimated: durationsEstimated,
    };
  });

  return {
    status,
    stageIndex: activeIndex,
    currentLabel: isComplete ? 'Complete' : isFailed ? 'Failed' : currentStage.label,
    currentDescription: isFailed
      ? job.error || 'Deployment failed.'
      : stageDescription(status, job, currentStage, deployTask),
    percent,
    stages: stagesWithTiming,
    subSteps,
    extensionTotal,
    extensionCompleted,
    isTerminal,
    isFailed,
    isComplete,
    isActive: !isTerminal,
    error: (job.error || '').trim() || null,
    backendCanisterId: (job.backend_canister_id || '').trim() || null,
    frontendCanisterId: (job.frontend_canister_id || '').trim() || null,
    startedAtMs,
    finishedAtMs,
    totalDurationMs,
    totalDurationLabel: totalDurationMs != null ? formatDuration(totalDurationMs) : '',
    durationsEstimated,
  };
}

export function getDeploymentStatusLabel(status) {
  const progress = getDeploymentProgress({ status, raw_status: status });
  if (progress.isComplete) return 'Completed';
  if (progress.isFailed) return 'Failed';
  if (progress.isActive) return progress.currentLabel;
  return status || 'Unknown';
}

export function getDeploymentStatusColor(status) {
  switch ((status || '').toLowerCase()) {
    case 'completed':
      return '#22c55e';
    case 'failed':
    case 'failed_verification':
    case 'cancelled':
      return '#ef4444';
    case 'pending':
      return '#f59e0b';
    default:
      return '#3b82f6';
  }
}
