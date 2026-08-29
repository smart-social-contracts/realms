import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * Setup-wizard step rail on a ~390px phone.
 *
 * Recycles the join-page pattern: labels sit under each dot so six steps
 * (Welcome / Codex / Token / Branding / Languages / Launch) fit the card.
 * The previous inline `white-space: nowrap` row clipped "Branding" on
 * test.gos.earth / realmstest10.
 */
const setupPage = readFileSync(
	join(dirname(fileURLToPath(import.meta.url)), '../../routes/(no-sidebar)/setup/+page.svelte'),
	'utf8'
);
const joinPage = readFileSync(
	join(dirname(fileURLToPath(import.meta.url)), '../../routes/(no-sidebar)/join/+page.svelte'),
	'utf8'
);

function cssBlock(className: string): string {
	const match = setupPage.match(new RegExp(`\\.${className}\\s*\\{([^}]+)\\}`));
	expect(match, `missing .${className} rule`).toBeTruthy();
	return match?.[1] ?? '';
}

describe('setup wizard step rail layout', () => {
	it('keeps the join stepper stacked (labels under dots)', () => {
		expect(joinPage).toContain('flex flex-col items-center');
		expect(joinPage).toMatch(/Labels sit under each\s+dot/);
	});

	it('puts each setup step label under the index, not inline', () => {
		expect(setupPage).toContain('class="setup-wizard__step-label"');
		expect(cssBlock('setup-wizard__step')).toMatch(/flex-direction:\s*column/);
		expect(cssBlock('setup-wizard__step')).not.toMatch(/white-space:\s*nowrap/);
		expect(cssBlock('setup-wizard__step')).toMatch(/min-width:\s*0/);
		expect(cssBlock('setup-wizard__step-label')).toMatch(/overflow-wrap:\s*break-word/);
	});

	it('lets the rail shrink instead of overflowing the card', () => {
		expect(cssBlock('setup-wizard__steps')).toMatch(/min-width:\s*0/);
		expect(cssBlock('setup-wizard__steps')).toMatch(/width:\s*100%/);
		expect(cssBlock('setup-wizard__step-rail')).toMatch(/min-width:\s*0\.2rem/);
	});
});
