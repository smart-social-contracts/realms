import { describe, expect, it } from 'vitest';
import { buildPromptFromFocus, setDocumentFocus } from './host-bridge';

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
});
