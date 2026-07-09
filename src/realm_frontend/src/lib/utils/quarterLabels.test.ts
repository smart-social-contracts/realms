import { describe, expect, it } from 'vitest';
import { formatQuarterLabel } from './quarterLabels';

describe('formatQuarterLabel', () => {
	it('labels the capital', () => {
		expect(formatQuarterLabel({ index: 0, is_capital: true })).toBe('Quarter 0 (Capital)');
	});

	it('labels sub-quarters by index', () => {
		expect(formatQuarterLabel({ index: 1, is_capital: false, name: 'agora-quarter-1' })).toBe(
			'Quarter 1'
		);
		expect(formatQuarterLabel({ index: 2, is_capital: false, name: 'agora-quarter-2' })).toBe(
			'Quarter 2'
		);
	});

	it('falls back safely', () => {
		expect(formatQuarterLabel(null)).toBe('Quarter');
		// candid status() drops is_capital — index 0 alone must still read as capital
		expect(formatQuarterLabel({ index: 0 })).toBe('Quarter 0 (Capital)');
	});
});
