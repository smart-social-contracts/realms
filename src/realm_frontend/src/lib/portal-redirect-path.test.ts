import { describe, expect, it } from 'vitest';
import {
  normalizePortalRedirectPath,
  resolvePortalNavSyncHref,
} from './portal-redirect-path';

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

describe('resolvePortalNavSyncHref', () => {
  it('does not navigate when the host path matches except iframe-only params', () => {
    expect(resolvePortalNavSyncHref('/join?portal=1&slug=realmtest4', '/join')).toBeNull();
    expect(
      resolvePortalNavSyncHref('/join?portal=1&slug=realmtest4', '/join?portal=1&slug=realmtest4'),
    ).toBeNull();
  });

  it('preserves portal embed params when the host path actually changes', () => {
    expect(resolvePortalNavSyncHref('/join?portal=1&slug=realmtest4', '/extensions/member_dashboard')).toBe(
      '/extensions/member_dashboard?portal=1&slug=realmtest4',
    );
  });

  it('keeps invite query params from the sync path', () => {
    expect(resolvePortalNavSyncHref('/join?portal=1&slug=x', '/join?invite=abc')).toBe(
      '/join?invite=abc&portal=1&slug=x',
    );
  });

  it('does not drop an invite already on the iframe URL when the host syncs pathname only', () => {
    expect(
      resolvePortalNavSyncHref('/join?portal=1&slug=x&invite=abc', '/join'),
    ).toBeNull();
  });

  it('does not drop ?ti= when the host syncs pathname only', () => {
    expect(
      resolvePortalNavSyncHref('/join?portal=1&slug=realmtest6&ti=1', '/join'),
    ).toBeNull();
    expect(
      resolvePortalNavSyncHref('/join?portal=1&slug=realmtest6&ti=0', '/join'),
    ).toBeNull();
  });

  it('copies host ?ti= onto the iframe when the embed src omitted it', () => {
    expect(resolvePortalNavSyncHref('/join?portal=1&slug=realmtest6', '/join?ti=1')).toBe(
      '/join?ti=1&portal=1&slug=realmtest6',
    );
    expect(resolvePortalNavSyncHref('/join?portal=1&slug=realmtest6', '/join?ti=0')).toBe(
      '/join?ti=0&portal=1&slug=realmtest6',
    );
  });

  it('keeps skip_ii and test_mode across a real path change', () => {
    expect(
      resolvePortalNavSyncHref(
        '/join?portal=1&slug=x&ti=1&skip_ii=true&test_mode=true',
        '/extensions/public_dashboard',
      ),
    ).toBe('/extensions/public_dashboard?portal=1&slug=x&ti=1&skip_ii=true&test_mode=true');
  });
});
