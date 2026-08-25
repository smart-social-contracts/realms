import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compile } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

const foldSource = readFileSync(
	resolve(dirname(fileURLToPath(import.meta.url)), '../../routes/(sidebar)/SidebarFold.svelte'),
	'utf8',
);

describe('sidebar fold Svelte 5 state tracking', () => {
	it('does not wrap a Set that the template only reads via a helper (live #315)', () => {
		const result = compile(
			`<script>
				let collapsed = new Set(['me']);
				function sectionOpen(id) { return !collapsed.has(id); }
				function setFoldOpen(id, nextOpen) {
					const next = new Set(collapsed);
					if (nextOpen) next.delete(id); else next.add(id);
					collapsed = next;
				}
			</script>
			<button onclick={() => setFoldOpen('me', !sectionOpen('me'))}>{sectionOpen('me')}</button>`,
			{ generate: 'client', filename: 'Live315.svelte' },
		);
		expect(result.js.code).toContain('let collapsed = new Set');
		expect(result.js.code).not.toMatch(/collapsed = \$\.(?:mutable_source|state)\(/);
	});

	it('wraps a template-bound foldOpen record so bind:open invalidates after tap', () => {
		const result = compile(
			`<script>
				let foldOpen = { me: false };
				function setFoldOpen(id, nextOpen) {
					foldOpen[id] = nextOpen;
					foldOpen = foldOpen;
				}
			</script>
			<button onclick={() => setFoldOpen('me', !foldOpen.me)}>{foldOpen.me}</button>`,
			{ generate: 'client', filename: 'BoundFold.svelte' },
		);
		expect(result.js.code).toMatch(/foldOpen = \$\.mutable_source\(/);
	});
});

describe('sidebar fold callback naming', () => {
	it('compiles SidebarFold so toggle assigns open instead of emitting an on* event', () => {
		const result = compile(foldSource, { generate: 'client', filename: 'SidebarFold.svelte' });
		expect(result.js.code).toMatch(/open\s*=\s*!/);
		expect(result.js.code).toMatch(/setOpen/);
		expect(result.js.code).not.toMatch(/\$\.event\([^)]*toggle/i);
	});

	it('does not compile a camelCase on* prop as a parent event listener', () => {
		const withEventish = compile(
			`<script>
				export let onToggle;
			</script>
			<button onclick={() => onToggle?.(true)}>x</button>`,
			{ generate: 'client', filename: 'Eventish.svelte' },
		);
		const withSetOpen = compile(
			`<script>
				export let setOpen;
			</script>
			<button onclick={() => setOpen?.(true)}>x</button>`,
			{ generate: 'client', filename: 'SetOpen.svelte' },
		);

		const parentEventish = compile(
			`<script>
				import Child from './Eventish.svelte';
				function go(v) {}
			</script>
			<Child onToggle={go} />`,
			{ generate: 'client', filename: 'ParentEventish.svelte' },
		);
		const parentSetOpen = compile(
			`<script>
				import Child from './SetOpen.svelte';
				function go(v) {}
			</script>
			<Child setOpen={go} />`,
			{ generate: 'client', filename: 'ParentSetOpen.svelte' },
		);

		// Svelte 5 emits onToggle as an event (`$.event` / props.ontoggle), not
		// a legacy export. setOpen stays a normal prop either way.
		expect(parentSetOpen.js.code).toMatch(/setOpen/);
		expect(withSetOpen.js.code).toMatch(/setOpen/);
		expect(withEventish.js.code + parentEventish.js.code).toMatch(/onToggle|ontoggle|Toggle/);
	});
});
