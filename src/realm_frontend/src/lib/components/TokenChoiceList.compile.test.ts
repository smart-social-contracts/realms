import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compile } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const tokenChoiceListPath = resolve(here, 'TokenChoiceList.svelte');
const tokenChoiceListSource = readFileSync(tokenChoiceListPath, 'utf8');

function compileSvelte(source: string, filename: string) {
	return compile(source, { generate: 'client', filename });
}

/** Strip only TypeScript surface so svelte/compiler can parse the real file. */
function asSvelteScript(source: string): string {
	return source
		.replace('<script lang="ts">', '<script>')
		.replace(/interface Props[\s\S]*?\n\t}\n\n/, '')
		.replace(': Props', '')
		.replace(/function selectable\(id: string\): boolean/, 'function selectable(id)')
		.replace(/function choose\(id: string\)/, 'function choose(id)');
}

describe('TokenChoiceList Svelte 5 compile', () => {
	it('rejects {@const} as a child of a regular element (c8eae9b install failure)', () => {
		expect(() =>
			compileSvelte(
				`<script>
					let items = ['a'];
				</script>
				<div>
					{#each items as item}
						<span>{item}</span>
					{/each}
					{@const customSelectable = true}
					<label>{customSelectable}</label>
				</div>`,
				'BrokenConst.svelte'
			)
		).toThrow(/\{@const\}/);
	});

	it('does not use {@const} in TokenChoiceList markup', () => {
		expect(tokenChoiceListSource).not.toMatch(/\{@const\b/);
	});

	it('compiles TokenChoiceList under the repo Svelte 5 compiler', () => {
		const result = compileSvelte(
			asSvelteScript(tokenChoiceListSource),
			'TokenChoiceList.svelte'
		);
		expect(result.js.code).toContain('selectable');
		expect(result.js.code).toContain('CUSTOM_TOKEN_ID');
	});
});
