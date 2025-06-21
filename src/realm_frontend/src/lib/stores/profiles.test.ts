import { describe, it, expect, beforeEach, vi } from 'vitest';
import { userProfiles, hasProfile, isAdmin, isMember, resetProfileState, setProfilesForTesting } from './profiles';
import { get } from 'svelte/store';

vi.mock('./auth', () => ({
  isAuthenticated: { subscribe: vi.fn(), set: vi.fn() }
}));

describe('User Profiles Store and Utilities', () => {
  beforeEach(() => {
    resetProfileState();
  });

  describe('hasProfile', () => {
    it('returns false when user has no profiles', () => {
      setProfilesForTesting([]);
      expect(hasProfile('admin')).toBe(false);
      expect(hasProfile('member')).toBe(false);
    });

    it('returns true when user has the specified profile', () => {
      setProfilesForTesting(['admin', 'member']);
      expect(hasProfile('admin')).toBe(true);
      expect(hasProfile('member')).toBe(true);
    });

    it('returns false when user does not have the specified profile', () => {
      setProfilesForTesting(['member']);
      expect(hasProfile('admin')).toBe(false);
      expect(hasProfile('moderator')).toBe(false);
    });

    it('handles empty string profile', () => {
      setProfilesForTesting(['admin', '']);
      expect(hasProfile('')).toBe(true);
      expect(hasProfile('admin')).toBe(true);
    });

    it('is case sensitive', () => {
      setProfilesForTesting(['Admin']);
      expect(hasProfile('admin')).toBe(false);
      expect(hasProfile('Admin')).toBe(true);
    });
  });

  describe('isAdmin', () => {
    it('returns true when user has admin profile', () => {
      setProfilesForTesting(['admin']);
      expect(isAdmin()).toBe(true);
    });

    it('returns true when user has admin among other profiles', () => {
      setProfilesForTesting(['member', 'admin', 'moderator']);
      expect(isAdmin()).toBe(true);
    });

    it('returns false when user does not have admin profile', () => {
      setProfilesForTesting(['member', 'moderator']);
      expect(isAdmin()).toBe(false);
    });

    it('returns false when user has no profiles', () => {
      setProfilesForTesting([]);
      expect(isAdmin()).toBe(false);
    });
  });

  describe('isMember', () => {
    it('returns true when user has member profile', () => {
      setProfilesForTesting(['member']);
      expect(isMember()).toBe(true);
    });

    it('returns true when user has member among other profiles', () => {
      setProfilesForTesting(['admin', 'member', 'moderator']);
      expect(isMember()).toBe(true);
    });

    it('returns false when user does not have member profile', () => {
      setProfilesForTesting(['admin', 'moderator']);
      expect(isMember()).toBe(false);
    });

    it('returns false when user has no profiles', () => {
      setProfilesForTesting([]);
      expect(isMember()).toBe(false);
    });
  });

  describe('userProfiles store', () => {
    it('can be updated and read', () => {
      const testProfiles = ['admin', 'member'];
      setProfilesForTesting(testProfiles);
      expect(get(userProfiles)).toEqual(testProfiles);
    });

    it('starts with empty array', () => {
      resetProfileState();
      expect(get(userProfiles)).toEqual([]);
    });
  });
});
