import { describe, it, expect } from 'vitest';
import { formatUSD, formatCompact, formatNumber } from './utils';

describe('Utility Functions', () => {
  describe('formatUSD', () => {
    it('formats positive numbers correctly', () => {
      expect(formatUSD(1234.56)).toBe('$1,234.56');
      expect(formatUSD(0)).toBe('$0.00');
      expect(formatUSD(1)).toBe('$1.00');
      expect(formatUSD(999.99)).toBe('$999.99');
    });

    it('formats negative numbers correctly', () => {
      expect(formatUSD(-1234.56)).toBe('-$1,234.56');
      expect(formatUSD(-0.01)).toBe('-$0.01');
    });

    it('handles large numbers', () => {
      expect(formatUSD(1000000)).toBe('$1,000,000.00');
      expect(formatUSD(1234567.89)).toBe('$1,234,567.89');
    });

    it('handles decimal precision', () => {
      expect(formatUSD(1.1)).toBe('$1.10');
      expect(formatUSD(1.999)).toBe('$2.00');
      expect(formatUSD(1.001)).toBe('$1.00');
    });

    it('handles edge cases', () => {
      expect(formatUSD(0.01)).toBe('$0.01');
      expect(formatUSD(0.001)).toBe('$0.00');
    });
  });

  describe('formatCompact', () => {
    it('formats small numbers without suffix', () => {
      expect(formatCompact(0)).toBe('0');
      expect(formatCompact(1)).toBe('1');
      expect(formatCompact(999)).toBe('999');
    });

    it('formats thousands with K suffix', () => {
      expect(formatCompact(1000)).toBe('1K');
      expect(formatCompact(1500)).toBe('1.5K');
      expect(formatCompact(12345)).toBe('12.3K');
      expect(formatCompact(999999)).toBe('1M');
    });

    it('formats millions with M suffix', () => {
      expect(formatCompact(1000000)).toBe('1M');
      expect(formatCompact(1500000)).toBe('1.5M');
      expect(formatCompact(12345678)).toBe('12.3M');
    });

    it('formats billions with B suffix', () => {
      expect(formatCompact(1000000000)).toBe('1B');
      expect(formatCompact(1500000000)).toBe('1.5B');
    });

    it('formats trillions with T suffix', () => {
      expect(formatCompact(1000000000000)).toBe('1T');
      expect(formatCompact(1500000000000)).toBe('1.5T');
    });

    it('handles negative numbers', () => {
      expect(formatCompact(-1000)).toBe('-1K');
      expect(formatCompact(-1500000)).toBe('-1.5M');
    });
  });

  describe('formatNumber', () => {
    it('formats numbers with default 2 decimal places', () => {
      expect(formatNumber(1234.56)).toBe('1,234.56');
      expect(formatNumber(1234)).toBe('1,234.00');
      expect(formatNumber(0)).toBe('0.00');
    });

    it('formats numbers with custom decimal places', () => {
      expect(formatNumber(1234.56789, 0)).toBe('1,235');
      expect(formatNumber(1234.56789, 1)).toBe('1,234.6');
      expect(formatNumber(1234.56789, 3)).toBe('1,234.568');
      expect(formatNumber(1234.56789, 4)).toBe('1,234.5679');
    });

    it('handles large numbers', () => {
      expect(formatNumber(1000000, 2)).toBe('1,000,000.00');
      expect(formatNumber(1234567.89, 1)).toBe('1,234,567.9');
    });

    it('handles negative numbers', () => {
      expect(formatNumber(-1234.56)).toBe('-1,234.56');
      expect(formatNumber(-1234.56, 1)).toBe('-1,234.6');
    });

    it('handles edge cases', () => {
      expect(formatNumber(0.1, 0)).toBe('0');
      expect(formatNumber(0.9, 0)).toBe('1');
      expect(formatNumber(0.001, 3)).toBe('0.001');
    });
  });
});
