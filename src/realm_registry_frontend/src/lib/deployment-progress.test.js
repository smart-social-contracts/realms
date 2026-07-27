import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildExtensionInstallGroups,
  buildExtensionSubSteps,
  buildProvisionSubSteps,
  computeDeploymentPercent,
  computeDeploymentUnits,
  getDeploymentProgress,
  withLiveProgressTiming,
} from './deployment-progress.js';

test('completed job is 100%', () => {
  assert.equal(
    computeDeploymentPercent({ status: 'completed', raw_status: 'completed' }, null),
    100,
  );
});

test('provisioning with backend only is well below old fixed 28%', () => {
  const job = {
    status: 'provisioning',
    raw_status: 'provisioning',
    backend_canister_id: 'epc7x-syaaa-aaaac-bfq3q-cai',
    frontend_canister_id: '',
    assets_verified: 0,
    wasm_verified: 1,
    expected_step_count: 33,
  };
  const percent = computeDeploymentPercent(job, null);
  assert.ok(percent < 20, `expected under 20%, got ${percent}%`);
});

test('provisioning with backend and frontend is mid provision range', () => {
  const job = {
    status: 'provisioning',
    raw_status: 'provisioning',
    backend_canister_id: 'abc',
    frontend_canister_id: 'def',
    assets_verified: 0,
    expected_step_count: 10,
  };
  const percent = computeDeploymentPercent(job, null);
  assert.ok(percent >= 20 && percent <= 32, `expected 20-32%, got ${percent}%`);
});

test('provisioning with assets verified scores higher than canisters-only', () => {
  const base = {
    status: 'provisioning',
    raw_status: 'provisioning',
    backend_canister_id: 'abc',
    frontend_canister_id: 'def',
    expected_step_count: 10,
  };
  const withoutAssets = computeDeploymentPercent({ ...base, assets_verified: 0 }, null);
  const withAssets = computeDeploymentPercent(
    { ...base, assets_verified: 1, wasm_verified: 1 },
    null,
  );
  assert.ok(withAssets > withoutAssets);
});

test('extension steps increase percent proportionally', () => {
  const job = {
    status: 'extensions',
    raw_status: 'extensions',
    backend_canister_id: 'abc',
    frontend_canister_id: 'def',
    assets_verified: 1,
    wasm_verified: 1,
    expected_step_count: 10,
  };
  const early = computeDeploymentPercent(job, { total_count: 10, completed_count: 2, steps: [] });
  const later = computeDeploymentPercent(job, { total_count: 10, completed_count: 8, steps: [] });
  assert.ok(later > early);
  assert.ok(early >= 42 && later <= 92);
});

test('withLiveProgressTiming ticks total and active stage duration', () => {
  const now = 1_700_000_000_000;
  const progress = getDeploymentProgress(
    {
      status: 'provisioning',
      raw_status: 'provisioning',
      created_at: (now - 125000) / 1000,
      backend_canister_id: 'abc',
    },
    null,
  );
  const live = withLiveProgressTiming(progress, now, { 1: now - 45000 });
  assert.equal(live.totalDurationLabel, '2m 5s');
  const activeStage = live.stages.find((s) => s.state === 'active');
  assert.equal(activeStage?.durationLabel, '45s');
});

test('getDeploymentProgress exposes provision and extension sub-steps', () => {
  const progress = getDeploymentProgress(
    {
      status: 'provisioning',
      raw_status: 'provisioning',
      backend_canister_id: 'abc',
      frontend_canister_id: '',
      assets_verified: 0,
    },
    null,
  );
  assert.ok(progress.provisionSubSteps.length >= 3);
  assert.equal(progress.provisionSubSteps[0].state, 'done');
  assert.equal(progress.provisionSubSteps[1].state, 'active');

  const extProgress = getDeploymentProgress(
    {
      status: 'extensions',
      raw_status: 'extensions',
      backend_canister_id: 'abc',
      frontend_canister_id: 'def',
      assets_verified: 1,
      wasm_verified: 1,
    },
    {
      deployTask: {
        total_count: 2,
        completed_count: 1,
        steps: [
          { idx: 0, kind: 'grant_frontend_access', label: 'grant_frontend_access', status: 'completed' },
          { idx: 1, kind: 'extension', label: 'public_dashboard', status: 'running' },
        ],
      },
    },
  );
  assert.equal(extProgress.extensionTotal, 2);
  assert.equal(extProgress.extensionCompleted, 1);
  assert.equal(extProgress.subSteps.length, 2);
  assert.match(extProgress.currentDescription, /1\/2/);
});

test('buildExtensionInstallGroups separates setup, extensions, and codex', () => {
  const groups = buildExtensionInstallGroups({
    steps: [
      { kind: 'configure_canister_ids', label: 'configure_canister_ids', status: 'completed' },
      { kind: 'grant_frontend_access', label: 'grant_frontend_access', status: 'completed' },
      { kind: 'extension', label: 'public_dashboard', status: 'completed' },
      { kind: 'extension', label: 'member_dashboard', status: 'running' },
      { kind: 'codex', label: 'syntropia', status: 'pending' },
    ],
  });

  assert.equal(groups.length, 3);
  assert.equal(groups[0].label, 'Setup');
  assert.equal(groups[0].completed, 2);
  assert.equal(groups[1].label, 'Extensions');
  assert.equal(groups[1].completed, 1);
  assert.equal(groups[1].steps[1].label, 'member_dashboard');
  assert.equal(groups[1].steps[1].statusLabel, 'In progress');
  assert.equal(groups[2].label, 'Codex');
  assert.equal(groups[2].steps[0].label, 'syntropia');
});

test('buildExtensionSubSteps expands codex dependencies when no extension steps exist', () => {
  const steps = buildExtensionSubSteps(
    {
      steps: [
        { kind: 'grant_frontend_access', label: 'grant_frontend_access', status: 'completed' },
        { kind: 'codex', label: 'syntropia', status: 'completed' },
      ],
    },
    ['access_manager', 'member_manager', 'zone_selector'],
  );

  const extensions = steps.filter((step) => step.group === 'extension');
  assert.equal(extensions.length, 3);
  assert.equal(extensions[0].label, 'access_manager');
  assert.equal(extensions[0].statusLabel, 'Installed');
  assert.equal(extensions[2].statusLabel, 'Installed');
});
