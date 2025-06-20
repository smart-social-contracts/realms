import { describe, it, expect, beforeEach, vi } from 'vitest';
import { userProfiles, hasProfile, isAdmin, isMember } from './profiles';
import { get } from 'svelte/store';

describe('User Profiles Store and Utilities', () => {
  beforeEach(() => {
    userProfiles.set([]);
  });

  describe('hasProfile', () => {
    it('returns false when user has no profiles', () => {
      userProfiles.set([]);
      expect(hasProfile('admin')).toBe(false);
      expect(hasProfile('member')).toBe(false);
    });

    it('returns true when user has the specified profile', () => {
      userProfiles.set(['admin', 'member']);
      expect(hasProfile('admin')).toBe(true);
      expect(hasProfile('member')).toBe(true);
    });

    it('returns false when user does not have the specified profile', () => {
      userProfiles.set(['member']);
      expect(hasProfile('admin')).toBe(false);
      expect(hasProfile('moderator')).toBe(false);
    });

    it('handles empty string profile', () => {
      userProfiles.set(['admin', '']);
      expect(hasProfile('')).toBe(true);
      expect(hasProfile('admin')).toBe(true);
    });

    it('is case sensitive', () => {
      userProfiles.set(['Admin']);
      expect(hasProfile('admin')).toBe(false);
      expect(hasProfile('Admin')).toBe(true);
    });
  });

  describe('isAdmin', () => {
    it('returns true when user has admin profile', () => {
      userProfiles.set(['admin']);
      expect(isAdmin()).toBe(true);
    });

    it('returns true when user has admin among other profiles', () => {
      userProfiles.set(['member', 'admin', 'moderator']);
      expect(isAdmin()).toBe(true);
    });

    it('returns false when user does not have admin profile', () => {
      userProfiles.set(['member', 'moderator']);
      expect(isAdmin()).toBe(false);
    });

    it('returns false when user has no profiles', () => {
      userProfiles.set([]);
      expect(isAdmin()).toBe(false);
    });
  });

  describe('isMember', () => {
    it('returns true when user has member profile', () => {
      userProfiles.set(['member']);
      expect(isMember()).toBe(true);
    });

    it('returns true when user has member among other profiles', () => {
      userProfiles.set(['admin', 'member', 'moderator']);
      expect(isMember()).toBe(true);
    });

    it('returns false when user does not have member profile', () => {
      userProfiles.set(['admin', 'moderator']);
      expect(isMember()).toBe(false);
    });

    it('returns false when user has no profiles', () => {
      userProfiles.set([]);
      expect(isMember()).toBe(false);
    });
  });

  describe('userProfiles store', () => {
    it('can be updated and read', () => {
      const testProfiles = ['admin', 'member'];
      userProfiles.set(testProfiles);
      expect(get(userProfiles)).toEqual(testProfiles);
    });

    it('starts with empty array', () => {
      expect(get(userProfiles)).toEqual([]);
    });
  });
});
