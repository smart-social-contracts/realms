import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * Mouse-inert primary buttons (Launch/Retry, extension iframe actions).
 *
 * Verified class: Tab+Enter fires the focused control, mouse click does not.
 * That is hit-testing, not “the handler is missing”:
 *   - A leftover layer (splash, mobile drawer stacking layer, closed fold
 *     0fr leak, host chrome over the extension iframe) sits above the
 *     control. `elementFromPoint` is not the button.
 *   - Enter synthesizes `click` on `document.activeElement`, so keyboard
 *     still works.
 *
 * Join “Continue as Identity N” (#366) was a different bug (login waited
 * on portal II). Keep `on:click={continueAsSelectedTestIdentity}`.
 *
 * Repro lock: if a primary action is only a Flowbite `<Button onclick>`
 * and a covering layer can sit above it, mouse-inert returns. Launch/Retry
 * must be native `<button type="button" onclick={handleLaunch}>` like Begin.
 */

const srcDir = join(dirname(fileURLToPath(import.meta.url)));

function readSrc(relative: string): string {
	return readFileSync(join(srcDir, relative), 'utf8');
}

describe('primary action mouse hit-testing', () => {
	it('Launch and Retry are native buttons wired to handleLaunch', () => {
		const setup = readSrc('../routes/(no-sidebar)/setup/+page.svelte');
		expect(setup).toContain('onclick={handleLaunch}');
		expect(setup).toContain('type="button"');
		expect(setup).toContain('setup.wizard.launch_start');
		expect(setup).toContain('setup.wizard.launch_retry');
		const wired = [...setup.matchAll(/<(button|Button)\b(?=[^>]*onclick=\{handleLaunch\})/g)].map(
			(match) => match[1]
		);
		expect(wired).toEqual(['button', 'button']);
	});

	it('does not regress join Continue as Identity N click wiring', () => {
		const join = readSrc('../routes/(no-sidebar)/join/+page.svelte');
		expect(join).toContain('on:click={continueAsSelectedTestIdentity}');
	});

	it('keeps leftover splash from stealing mouse hits', () => {
		const html = readFileSync(join(srcDir, '../app.html'), 'utf8');
		expect(html).toContain('#app-splash');
		expect(html).toMatch(/#app-splash[\s\S]*pointer-events:\s*none/);
		expect(html).toContain('/custom/logo.png');
		expect(html).toContain('has-logo');
		const splash = readSrc('app-splash.ts');
		expect(splash).toContain('dismissAppSplash');
	});

	it('keeps the extension mount and sandbox iframe in the hit stack', () => {
		const host = readSrc('components/ExtensionRuntimeHost.svelte');
		expect(host).toMatch(/\.extension-mount-point[\s\S]*pointer-events:\s*auto/);
		const loader = readSrc('extension-loader.ts');
		expect(loader).toContain("iframe.style.pointerEvents = 'auto'");
	});

	it('dismisses Test Mode Active on a native mouse click, not only Tab+Enter', () => {
		const banner = readSrc('components/DemoBanner.svelte');
		expect(banner).toContain('type="button"');
		expect(banner).toContain('onclick={dismissBanner}');
		expect(banner).toContain('demo_banner.dismiss_label');
		// Click must land on the <button>, not the X <path>. Delegated SVG
		// hits are the Tab+Enter-works / mouse-dead class.
		expect(banner).toMatch(/<svg[^>]*pointer-events-none/);
		expect(banner).toContain('pointer-events-auto');
		// Stay below header z-[70] so the X does not cover menu / avatar.
		expect(banner).toMatch(/\bz-10\b/);
		expect(banner).not.toMatch(/z-\[7/);
		expect(banner).not.toMatch(/z-\[8/);
		expect(banner).not.toMatch(/z-\[9/);
	});

	it('does not let Test Mode banner stacking steal header chrome clicks', () => {
		const layout = readSrc('../routes/(sidebar)/+layout.svelte');
		const navbar = readSrc('../routes/(sidebar)/Navbar.svelte');
		expect(layout.indexOf('<DemoBanner')).toBeLessThan(layout.indexOf('<header'));
		expect(layout).toContain('--realm-banner-h');
		expect(layout).toContain('max-lg:top-[var(--realm-banner-h)]');
		expect(layout).toContain('z-[70]');
		expect(layout).toContain('<Navbar bind:drawerHidden />');
		expect(navbar).toContain('pointer-events: auto');
		expect(navbar).toContain('drawerHidden = !drawerHidden');
		expect(navbar).toContain('AuthButton');
	});
});
