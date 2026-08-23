import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const foldPath = resolve(here, '../../routes/(sidebar)/SidebarFold.svelte');
const fold = readFileSync(foldPath, 'utf8');

describe('sidebar fold animation', () => {
	it('animates height from an is-open class, not the native open attribute', () => {
		expect(fold).toContain('grid-template-rows: 0fr');
		expect(fold).toContain('transition: grid-template-rows 200ms ease-out');
		expect(fold).toContain('.sidebar-details.is-open .fold');
		expect(fold).toContain('grid-template-rows: 1fr');
		expect(fold).not.toMatch(/\.sidebar-details\[open\]\s+\.fold/);
	});

	it('rotates the chevron on both open and close', () => {
		expect(fold).toContain('transition: transform 200ms ease-out');
		expect(fold).toContain('.sidebar-details.is-open :global(.fold-chevron)');
		expect(fold).not.toMatch(/\.sidebar-details:not\(\[open\]\)/);
	});

	it('keeps <details> open until the 200ms close animation finishes', () => {
		expect(fold).toContain('const FOLD_MS = 200');
		expect(fold).toContain('setTimeout(finishClose, FOLD_MS)');
		expect(fold).toContain('event.preventDefault()');
	});
});
