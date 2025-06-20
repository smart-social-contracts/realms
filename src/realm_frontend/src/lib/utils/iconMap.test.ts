import { describe, it, expect } from 'vitest';
import { iconMap, getIcon } from './iconMap';
import { LightbulbOutline } from 'flowbite-svelte-icons';

describe('Icon Map Utilities', () => {
  describe('iconMap', () => {
    it('contains expected icon mappings', () => {
      expect(iconMap).toHaveProperty('wallet');
      expect(iconMap).toHaveProperty('cog');
      expect(iconMap).toHaveProperty('chart');
      expect(iconMap).toHaveProperty('lightbulb');
      expect(iconMap).toHaveProperty('dollar');
      expect(iconMap).toHaveProperty('clipboard');
      expect(iconMap).toHaveProperty('layers');
      expect(iconMap).toHaveProperty('lifesaver');
      expect(iconMap).toHaveProperty('lock');
      expect(iconMap).toHaveProperty('wand');
      expect(iconMap).toHaveProperty('analytics');
      expect(iconMap).toHaveProperty('list');
      expect(iconMap).toHaveProperty('table');
      expect(iconMap).toHaveProperty('users');
      expect(iconMap).toHaveProperty('home');
      expect(iconMap).toHaveProperty('file');
    });

    it('maps icon names to components', () => {
      Object.values(iconMap).forEach(iconComponent => {
        expect(iconComponent).toBeDefined();
        expect(typeof iconComponent).toBe('function');
      });
    });
  });

  describe('getIcon', () => {
    it('returns correct icon for valid icon name', () => {
      const walletIcon = getIcon('wallet');
      expect(walletIcon).toBe(iconMap['wallet']);
      
      const cogIcon = getIcon('cog');
      expect(cogIcon).toBe(iconMap['cog']);
    });

    it('returns default icon for invalid icon name', () => {
      const invalidIcon = getIcon('nonexistent');
      expect(invalidIcon).toBe(LightbulbOutline);
    });

    it('returns custom default icon when provided', () => {
      const customDefault = iconMap['wallet'];
      const invalidIcon = getIcon('nonexistent', customDefault);
      expect(invalidIcon).toBe(customDefault);
    });

    it('handles empty string icon name', () => {
      const emptyIcon = getIcon('');
      expect(emptyIcon).toBe(LightbulbOutline);
    });

    it('handles null/undefined icon name', () => {
      const nullIcon = getIcon(null as any);
      expect(nullIcon).toBe(LightbulbOutline);
      
      const undefinedIcon = getIcon(undefined as any);
      expect(undefinedIcon).toBe(LightbulbOutline);
    });

    it('is case sensitive', () => {
      const lowerIcon = getIcon('wallet');
      const upperIcon = getIcon('WALLET');
      
      expect(lowerIcon).toBe(iconMap['wallet']);
      expect(upperIcon).toBe(LightbulbOutline);
    });
  });
});
