import { describe, it, expect } from 'vitest';
import { frontendUrl, candidUiUrl, icDashboardUrl, shortId } from './config';

describe('frontendUrl', () => {
  it('returns icp0.io URL for a canister ID', () => {
    expect(frontendUrl('abc-def')).toBe('https://abc-def.icp0.io');
  });
});

describe('candidUiUrl', () => {
  it('returns Candid UI URL with the canister ID as query param', () => {
    const url = candidUiUrl('xyz-123');
    expect(url).toContain('a4gq6-oaaaa-aaaab-qaa4q-cai.raw.icp0.io');
    expect(url).toContain('id=xyz-123');
  });
});

describe('icDashboardUrl', () => {
  it('returns IC Dashboard URL with the canister ID in the path', () => {
    expect(icDashboardUrl('abc-def')).toBe(
      'https://dashboard.internetcomputer.org/canister/abc-def',
    );
  });
});

describe('shortId', () => {
  it('returns short IDs unchanged', () => {
    expect(shortId('abc-def')).toBe('abc-def');
  });

  it('truncates long canister IDs with ellipsis', () => {
    const long = 'rhw4p-gqaaa-aaaac-qbw7q-cai';
    const short = shortId(long);
    expect(short.length).toBeLessThan(long.length);
    expect(short).toContain('...');
    expect(short.startsWith(long.slice(0, 7))).toBe(true);
    expect(short.endsWith(long.slice(-5))).toBe(true);
  });

  it('returns strings at the boundary length unchanged', () => {
    const exactly15 = '123456789012345';
    expect(shortId(exactly15)).toBe(exactly15);
  });
});
