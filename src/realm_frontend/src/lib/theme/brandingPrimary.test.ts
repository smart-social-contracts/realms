// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import {
	DEFAULT_PRIMARY_COLOR,
	applyBrandingPrimary,
	parsePrimaryColor,
	paletteFromPrimary,
	primaryCssVariables
} from './brandingPrimary';

describe('brandingPrimary', () => {
	it('parses valid hex and rejects invalid values', () => {
		expect(parsePrimaryColor('#3B82F6')).toBe('#3b82f6');
		expect(parsePrimaryColor(' #aabbcc ')).toBe('#aabbcc');
		expect(parsePrimaryColor('#abc')).toBeNull();
		expect(parsePrimaryColor('blue')).toBeNull();
		expect(parsePrimaryColor(null)).toBeNull();
	});

	it('builds a palette where 600 equals the normalized input', () => {
		const palette = paletteFromPrimary('#FF00AA');
		expect(palette[600]).toBe('#ff00aa');
		expect(palette[50]).toMatch(/^#[0-9a-f]{6}$/);
		expect(palette[900]).toMatch(/^#[0-9a-f]{6}$/);
	});

	it('falls back to the default color for invalid input', () => {
		const palette = paletteFromPrimary('not-a-color');
		expect(palette[600]).toBe(DEFAULT_PRIMARY_COLOR);
	});

	it('exports css variables for every primary shade', () => {
		const vars = primaryCssVariables('#2563eb');
		expect(vars['--color-primary-600']).toBe('#2563eb');
		expect(Object.keys(vars)).toHaveLength(10);
	});

	it('applyBrandingPrimary is safe without document', () => {
		const originalDocument = globalThis.document;
		// @ts-expect-error test shim
		delete globalThis.document;
		expect(applyBrandingPrimary('#2563eb')['--color-primary-600']).toBe('#2563eb');
		globalThis.document = originalDocument;
	});

	it('applyBrandingPrimary sets variables on documentElement', () => {
		const vars = applyBrandingPrimary('#dc2626');
		expect(document.documentElement.style.getPropertyValue('--color-primary-600')).toBe('#dc2626');
		expect(vars['--color-primary-700']).toBeTruthy();
	});
});
