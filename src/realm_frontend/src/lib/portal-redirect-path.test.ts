import { describe, expect, it } from 'vitest';
import { normalizePortalRedirectPath } from './portal-redirect-path';

describe('normalizePortalRedirectPath', () => {
  it('returns empty string for root', () => {
    expect(normalizePortalRedirectPath('/')).toBe('');
    expect(normalizePortalRedirectPath('')).toBe('');
  });

  it('passes through normal SPA routes unchanged', () => {
    expect(normalizePortalRedirectPath('/admin/manifest')).toBe('/admin/manifest');
    expect(normalizePortalRedirectPath('/extensions/member_dashboard')).toBe(
      '/extensions/member_dashboard',
    );
  });

  it('maps internal extension bundle paths to /extensions/{id}', () => {
    expect(
      normalizePortalRedirectPath('/ext/member_dashboard/1.1.2/frontend/dist/index.html'),
    ).toBe('/extensions/member_dashboard');
    expect(normalizePortalRedirectPath('/ext/voting/0.2.0/frontend/dist/index.js')).toBe(
      '/extensions/voting',
    );
  });
});
