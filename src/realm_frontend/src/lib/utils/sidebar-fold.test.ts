import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const foldPath = resolve(here, '../../routes/(sidebar)/SidebarFold.svelte');
const sidebarPath = resolve(here, '../../routes/(sidebar)/Sidebar.svelte');
const fold = readFileSync(foldPath, 'utf8');
const sidebar = readFileSync(sidebarPath, 'utf8');

describe('sidebar fold animation', () => {
	it('does not use a details/summary element (Chrome 131+ ::details-content keeps 1fr at 0px)', () => {
		expect(fold).not.toMatch(/<details[\s>]/);
		expect(fold).not.toMatch(/<summary[\s>]/);
		expect(fold).not.toMatch(/::details-content\s*\{/);
		expect(fold).toContain('Chrome 131+');
	});

	it('keeps is-open in the template so Svelte does not drop the height rule', () => {
		expect(fold).toContain('class:is-open={open}');
		expect(fold).toContain('.sidebar-fold.is-open > .fold');
		expect(fold).toContain('grid-template-rows: 0fr');
		expect(fold).toContain('transition: grid-template-rows 200ms ease-out');
		expect(fold).toContain('grid-template-rows: 1fr');
		expect(fold).not.toMatch(/\.sidebar-details\[open\]\s+\.fold/);
	});

	it('exposes a button whose aria-expanded follows the open prop', () => {
		expect(fold).toContain('type="button"');
		expect(fold).toContain('aria-expanded={open}');
		expect(fold).toContain('onclick={toggle}');
	});

	it('rotates only this fold’s chevron, not nested or sibling rows', () => {
		expect(fold).toContain('transition: transform 200ms ease-out');
		expect(fold).toContain('.sidebar-fold.is-open > .fold-summary :global(.fold-chevron)');
		expect(fold).not.toMatch(/\.sidebar-fold :global\(\.fold-chevron\)/);
		expect(fold).not.toMatch(/\.sidebar-details:not\(\[open\]\)/);
	});
});

describe('sidebar fold wiring', () => {
	it('does not use display:contents on fold headers (breaks summary/button hit-testing)', () => {
		expect(sidebar).not.toMatch(/slot="header"[^>]*class="contents"/);
		expect(sidebar).toContain('slot="header" class="flex w-full min-w-0 items-center justify-between"');
	});

	it('drives every section and category fold from the same open/onToggle contract', () => {
		expect(sidebar.match(/<SidebarFold/g)?.length).toBeGreaterThanOrEqual(8);
		expect(sidebar).toContain("open={sectionOpen('__section_me__')}");
		expect(sidebar).toContain("open={sectionOpen('__section_realm__')}");
		expect(sidebar).toContain("open={sectionOpen('__section_mundus__')}");
		expect(sidebar).toContain('open={sectionOpen(category.id)}');
		expect(sidebar).toContain('onToggle={(nextOpen) => setFoldOpen(');
	});
});
