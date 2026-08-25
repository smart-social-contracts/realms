import { describe, expect, it } from 'vitest';
import {
	buildPromptFromFocus,
	dispatchHostAction,
	hostActionEvents,
	setDocumentFocus,
} from './host-bridge';

describe('host-bridge', () => {
	it('builds a snippet prompt from focus snapshot', () => {
		setDocumentFocus({
			source: 'codex_viewer',
			uri: 'realms://codex_viewer/codex/tax_collection?lines=9-31',
			label: 'tax_collection, lines 9–31',
			snapshot: {
				languageId: 'python',
				range: { startLine: 9, endLine: 31 },
				text: 'def collect():\n    pass',
			},
		});

		const prompt = buildPromptFromFocus({
			source: 'codex_viewer',
			uri: 'realms://codex_viewer/codex/tax_collection?lines=9-31',
			label: 'tax_collection, lines 9–31',
			snapshot: {
				languageId: 'python',
				range: { startLine: 9, endLine: 31 },
				text: 'def collect():\n    pass',
			},
		});

		expect(prompt).toContain('tax_collection, lines 9–31');
		expect(prompt).toContain('```python');
		expect(prompt).toContain('def collect()');
	});

	it('emits navigate.home without a target extension id', () => {
		let seen: { type: string } | null = null;
		const unsub = hostActionEvents.subscribe((event) => {
			if (event?.action.type === 'navigate.home') {
				seen = event.action;
			}
		});
		dispatchHostAction({ type: 'navigate.home' });
		unsub();
		expect(seen).toEqual({ type: 'navigate.home' });
		expect(JSON.stringify(seen)).not.toMatch(/member_dashboard/);
	});
});
