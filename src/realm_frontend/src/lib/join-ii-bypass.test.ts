import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const srcDir = join(dirname(fileURLToPath(import.meta.url)));

function readSrc(relative: string): string {
	return readFileSync(join(srcDir, relative), 'utf8');
}

describe('join II-bypass click + ?ti= wiring', () => {
	it('Continue as Identity N calls bypass login with the selected index', () => {
		const join = readSrc('../routes/(no-sidebar)/join/+page.svelte');
		expect(join).toContain('continueAsSelectedTestIdentity');
		expect(join).toContain('on:click={continueAsSelectedTestIdentity}');
		expect(join).toContain('identityIndex: selectedTestIdentityIndex');
		expect(join).toContain('preferTestMode: true');
		expect(join).toContain('persistSelectedTestIdentity(selectedTestIdentityIndex)');
		expect(join).toMatch(/type="button"/);
	});

	it('reads ?ti= on mount and keeps it on the URL through continue', () => {
		const join = readSrc('../routes/(no-sidebar)/join/+page.svelte');
		expect(join).toContain('parseTestIdentitySearch');
		expect(join).toContain('applyTestIdentitySearch');
		expect(join).toContain('portalNavPush');
	});

	it('login() uses an explicit picker index instead of portal II', () => {
		const auth = readSrc('auth.js');
		expect(auth).toContain('shouldLoginWithTestIdentity');
		expect(auth).toContain('parseTestIdentitySearch');
		expect(auth).toContain('resolvedIndex');
	});

	it('home redirect and portal enter keep ti unless the iframe path drifted from the host', () => {
		const home = readSrc('../routes/(sidebar)/+page.svelte');
		expect(home).toContain('hrefWithPreservedTestIdentityParams');
		const layout = readSrc('../routes/+layout.svelte');
		expect(layout).toContain("navigation.type === 'enter'");
		expect(layout).toContain('shouldPortalEnterPush');
		expect(layout).toContain('syncPortalIfHostStale');
	});
});
