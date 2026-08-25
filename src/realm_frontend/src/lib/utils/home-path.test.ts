import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { resolveHomePath } from './home-path';

describe('resolveHomePath', () => {
	it('uses the sidebar default path the host already resolved', () => {
		expect(resolveHomePath({ defaultPath: '/extensions/welcome' })).toBe('/extensions/welcome');
	});

	it('falls back to realm root when sidebar config is missing', () => {
		expect(resolveHomePath(null)).toBe('/');
		expect(resolveHomePath(undefined)).toBe('/');
		expect(resolveHomePath({ defaultPath: '   ' })).toBe('/');
	});

	it('is what the sidebar layout uses for navigate.home', () => {
		const layout = readFileSync(
			join(dirname(fileURLToPath(import.meta.url)), '../../routes/(sidebar)/+layout.svelte'),
			'utf8',
		);
		expect(layout).toContain('navigate.home');
		expect(layout).toContain('resolveHomePath');
		expect(layout).toContain('sidebarConfig');
	});
});
