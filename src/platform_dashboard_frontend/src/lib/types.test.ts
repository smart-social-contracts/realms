import { describe, it, expect } from 'vitest';
import type {
  RealmRecord,
  CanisterInfo,
  QuarterInfoRecord,
  StatusRecord,
  DeployRecord,
  DeployStepRecord,
  DeployStatusRecord,
  FileRegistryStats,
  InstallerInfo,
} from './types';

describe('type contracts', () => {
  it('RealmRecord has the expected shape', () => {
    const record: RealmRecord = {
      id: 'abc-123',
      name: 'Test Realm',
      url: 'https://abc-123.icp0.io',
      backend_url: 'https://abc-123.raw.icp0.io',
      logo: '',
      users_count: 42,
      created_at: '2025-01-01',
    };
    expect(record.id).toBe('abc-123');
    expect(record.users_count).toBe(42);
  });

  it('CanisterInfo has id and type', () => {
    const info: CanisterInfo = { canister_id: 'xyz', canister_type: 'backend' };
    expect(info.canister_type).toBe('backend');
  });

  it('QuarterInfoRecord has population and status', () => {
    const q: QuarterInfoRecord = {
      name: 'Q1',
      canister_id: 'q1-id',
      population: 100,
      status: 'active',
    };
    expect(q.population).toBe(100);
  });

  it('StatusRecord supports optional fields', () => {
    const status: StatusRecord = { version: '1.0.0' };
    expect(status.version).toBe('1.0.0');
    expect(status.quarters).toBeUndefined();
  });

  it('DeployRecord captures deployment metadata', () => {
    const d: DeployRecord = {
      deploy_id: 'd-1',
      realm_name: 'Dominion',
      status: 'completed',
      started_at: '2025-01-01T00:00:00Z',
      completed_at: '2025-01-01T00:05:00Z',
    };
    expect(d.status).toBe('completed');
  });

  it('DeployStatusRecord contains steps', () => {
    const step: DeployStepRecord = {
      step: 1,
      name: 'Upload WASM',
      status: 'done',
    };
    const ds: DeployStatusRecord = {
      deploy_id: 'd-1',
      realm_name: 'Dominion',
      status: 'completed',
      steps: [step],
    };
    expect(ds.steps).toHaveLength(1);
    expect(ds.steps[0].name).toBe('Upload WASM');
  });

  it('FileRegistryStats has numeric fields', () => {
    const stats: FileRegistryStats = {
      total_files: 10,
      total_bytes: 1024,
      total_chunks: 5,
    };
    expect(stats.total_bytes).toBe(1024);
  });

  it('InstallerInfo has version', () => {
    const info: InstallerInfo = { version: '2.0.0', commit: 'abc1234' };
    expect(info.version).toBe('2.0.0');
  });
});
