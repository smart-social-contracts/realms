import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const sidebar = readFileSync(resolve(here, '../../routes/(sidebar)/Sidebar.svelte'), 'utf8');
const layout = readFileSync(resolve(here, '../../routes/(sidebar)/+layout.svelte'), 'utf8');
const navbar = readFileSync(resolve(here, '../../routes/(sidebar)/Navbar.svelte'), 'utf8');

describe('sidebar drawer vs desktop rail', () => {
	it('keeps the mobile drawer and desktop rail on separate flags', () => {
		expect(layout).toContain('<Navbar bind:drawerHidden />');
		expect(layout).toContain('<Sidebar bind:drawerHidden desktopHidden={hideDesktopSidebar} />');
		expect(navbar).toContain('drawerHidden = !drawerHidden');
		expect(sidebar).toContain('export let drawerHidden');
		expect(sidebar).toContain('export let desktopHidden');
	});

	it('shows a scrim + sliding panel only on the mobile drawer', () => {
		expect(sidebar).toContain('lg:hidden');
		expect(sidebar).toContain('drawer-backdrop');
		expect(sidebar).toContain('drawer-panel');
		expect(sidebar).toContain("aria-label=\"Close menu\"");
		expect(sidebar).toMatch(/drawerHidden \? 'pointer-events-none'/);
	});

	it('clips the desktop rail while it collapses so the banner is not covered', () => {
		const desktopAside = sidebar.slice(sidebar.indexOf('<!-- Desktop sidebar'));
		expect(desktopAside).toContain('overflow-hidden');
		expect(desktopAside).toContain('relative isolate');
		expect(desktopAside).toContain('transition-[width]');
		// overflow-hidden must not be gated on desktopHidden — otherwise the
		// w-64 inner column paints over main content (Test Mode banner) mid-toggle.
		const hiddenBranch = desktopAside.match(/desktopHidden \? '([^']+)'/)?.[1] ?? '';
		expect(hiddenBranch).toContain('w-0');
		expect(hiddenBranch).not.toContain('overflow-hidden');
		expect(desktopAside).toMatch(/class="relative isolate[^"]*overflow-hidden/);
	});

	it('does not reopen a user-opened mobile drawer when auth refreshes', () => {
		expect(layout).toContain('Keep a user-opened mobile drawer open across auth/store refreshes');
		expect(layout).toContain('applySidebarVisibility({ forceMobileClosed: !auth })');
	});
});
