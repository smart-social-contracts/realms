import assert from 'node:assert/strict';
import test from 'node:test';
import {
  computeDeploymentPercent,
  computeDeploymentUnits,
  getDeploymentProgress,
} from './deployment-progress.js';

test('completed job is 100%', () => {
  assert.equal(
    computeDeploymentPercent({ status: 'completed', raw_status: 'completed' }, null),
    100,
  );
});

test('provisioning with backend and frontend advances past flat stage percent', () => {
  const job = {
    status: 'provisioning',
    raw_status: 'provisioning',
    backend_canister_id: 'epc7x-syaaa-aaaac-bfq3q-cai',
    frontend_canister_id: 'fcm3z-5qaaa-aaaac-bfq4a-cai',
    assets_verified: 0,
    wasm_verified: 0,
    expected_step_count: 33,
  };
  const percent = computeDeploymentPercent(job, null);
  assert.ok(percent > 10 && percent < 40, `expected mid-range percent, got ${percent}`);
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
});

test('getDeploymentProgress exposes sub-steps during extensions', () => {
  const progress = getDeploymentProgress(
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
  assert.equal(progress.extensionTotal, 2);
  assert.equal(progress.extensionCompleted, 1);
  assert.equal(progress.subSteps.length, 2);
  assert.match(progress.currentDescription, /1\/2/);
});
