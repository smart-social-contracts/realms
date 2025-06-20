import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('$lib/canisters', () => ({}));

vi.mock('./llm_chat/LLMChat.svelte', () => ({
  default: vi.fn(() => ({ $$: {} }))
}));

vi.mock('$lib/utils/iconMap', () => ({
  getIcon: vi.fn((iconName: string) => `MockIcon_${iconName}`)
}));

import { getAllExtensions, getExtension, toggleExtension, getExtensionIcon } from './index';
import type { ExtensionMetadata } from './index';

describe('Extensions System', () => {
  describe('getAllExtensions', () => {
    it('returns an array of extensions', () => {
      const extensions = getAllExtensions();
      expect(Array.isArray(extensions)).toBe(true);
    });

    it('only returns enabled extensions', () => {
      const extensions = getAllExtensions();
      extensions.forEach(ext => {
        expect(ext.enabled).toBe(true);
      });
    });

    it('returns extensions with required metadata fields', () => {
      const extensions = getAllExtensions();
      extensions.forEach(ext => {
        expect(ext).toHaveProperty('id');
        expect(ext).toHaveProperty('name');
        expect(ext).toHaveProperty('description');

        expect(ext).toHaveProperty('icon');
        expect(ext).toHaveProperty('author');
        expect(ext).toHaveProperty('permissions');
        expect(ext).toHaveProperty('component');
        expect(ext).toHaveProperty('enabled');
        
        expect(typeof ext.id).toBe('string');
        expect(typeof ext.name).toBe('string');
        expect(typeof ext.description).toBe('string');

        expect(ext.icon).toBeDefined();
        expect(typeof ext.author).toBe('string');
        expect(Array.isArray(ext.permissions)).toBe(true);
        expect(typeof ext.enabled).toBe('boolean');
      });
    });
  });

  describe('getExtension', () => {
    it('returns extension by valid ID', () => {
      const extensions = getAllExtensions();
      if (extensions.length > 0) {
        const firstExt = extensions[0];
        const retrieved = getExtension(firstExt.id);
        expect(retrieved).toEqual(firstExt);
      }
    });

    it('returns undefined for invalid ID', () => {
      const nonExistent = getExtension('nonexistent_extension_id');
      expect(nonExistent).toBeUndefined();
    });

    it('returns undefined for empty string ID', () => {
      const empty = getExtension('');
      expect(empty).toBeUndefined();
    });

    it('handles null/undefined ID gracefully', () => {
      const nullResult = getExtension(null as any);
      expect(nullResult).toBeUndefined();
      
      const undefinedResult = getExtension(undefined as any);
      expect(undefinedResult).toBeUndefined();
    });
  });

  describe('toggleExtension', () => {
    it('disables an enabled extension', () => {
      const extensions = getAllExtensions();
      if (extensions.length > 0) {
        const firstExt = extensions[0];
        expect(firstExt.enabled).toBe(true);
        
        toggleExtension(firstExt.id, false);
        const updated = getExtension(firstExt.id);
        expect(updated?.enabled).toBe(false);
        
        toggleExtension(firstExt.id, true);
      }
    });

    it('enables a disabled extension', () => {
      const extensions = getAllExtensions();
      if (extensions.length > 0) {
        const firstExt = extensions[0];
        
        toggleExtension(firstExt.id, false);
        let updated = getExtension(firstExt.id);
        expect(updated?.enabled).toBe(false);
        
        toggleExtension(firstExt.id, true);
        updated = getExtension(firstExt.id);
        expect(updated?.enabled).toBe(true);
      }
    });

    it('handles invalid extension ID gracefully', () => {
      expect(() => {
        toggleExtension('nonexistent_id', false);
      }).not.toThrow();
      
      expect(() => {
        toggleExtension('', true);
      }).not.toThrow();
    });

    it('affects getAllExtensions results', () => {
      const initialExtensions = getAllExtensions();
      const initialCount = initialExtensions.length;
      
      if (initialCount > 0) {
        const firstExt = initialExtensions[0];
        
        toggleExtension(firstExt.id, false);
        const afterDisable = getAllExtensions();
        expect(afterDisable.length).toBe(initialCount - 1);
        expect(afterDisable.find(ext => ext.id === firstExt.id)).toBeUndefined();
        
        toggleExtension(firstExt.id, true);
        const afterEnable = getAllExtensions();
        expect(afterEnable.length).toBe(initialCount);
        expect(afterEnable.find(ext => ext.id === firstExt.id)).toBeDefined();
      }
    });
  });

  describe('getExtensionIcon', () => {
    it('returns icon component for extension', () => {
      const extensions = getAllExtensions();
      if (extensions.length > 0) {
        const firstExt = extensions[0];
        const icon = getExtensionIcon(firstExt);
        expect(icon).toBe(`MockIcon_${firstExt.icon}`);
      }
    });

    it('handles extension with different icon names', () => {
      const mockExtension: ExtensionMetadata = {
        id: 'test',
        name: 'Test Extension',
        description: 'Test',
        version: '1.0.0',
        icon: 'custom-icon',
        author: 'Test Author',
        permissions: [],
        enabled: true
      };
      
      const icon = getExtensionIcon(mockExtension);
      expect(icon).toBe('MockIcon_custom-icon');
    });
  });
});
