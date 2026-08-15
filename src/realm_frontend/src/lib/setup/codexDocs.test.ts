import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import {
	CODEX_REPO_BASE,
	__resetCodexDocsCache,
	fetchCodexDescription,
	repositoryUrl,
	shortDescriptionUrl,
	stripMarkdownTitle
} from './codexDocs';

describe('codexDocs URLs', () => {
	it('builds the raw SHORT_DESCRIPTION URL', () => {
		expect(shortDescriptionUrl('agora')).toBe(
			'https://raw.githubusercontent.com/smart-social-contracts/realms-codices/main/codices/agora/SHORT_DESCRIPTION.md'
		);
	});

	it('builds the repository URL from the shared base', () => {
		expect(CODEX_REPO_BASE).toBe(
			'https://github.com/smart-social-contracts/realms-codices/tree/main/codices'
		);
		expect(repositoryUrl('syntropia')).toBe(
			'https://github.com/smart-social-contracts/realms-codices/tree/main/codices/syntropia'
		);
	});
});

describe('stripMarkdownTitle', () => {
	it('removes a leading heading and blank line', () => {
		const text = '# Agora\n\nFirst sentence. Second sentence.';
		expect(stripMarkdownTitle(text)).toBe('First sentence. Second sentence.');
	});

	it('collapses remaining lines into one paragraph', () => {
		const text = 'Line one.\n\nLine two.';
		expect(stripMarkdownTitle(text)).toBe('Line one. Line two.');
	});
});

describe('fetchCodexDescription', () => {
	beforeEach(() => {
		__resetCodexDocsCache();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('returns stripped markdown on success', async () => {
		const fetchImpl = vi.fn().mockResolvedValue({
			ok: true,
			text: async () => '# Agora\n\nFetched description.'
		});

		const result = await fetchCodexDescription('agora', 'fallback', { fetchImpl });

		expect(result).toBe('Fetched description.');
		expect(fetchImpl).toHaveBeenCalledWith(
			shortDescriptionUrl('agora'),
			expect.objectContaining({ signal: expect.any(AbortSignal) })
		);
	});

	it('returns fallback on non-OK responses', async () => {
		const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 404 });

		const result = await fetchCodexDescription('agora', 'fallback', { fetchImpl });

		expect(result).toBe('fallback');
	});

	it('returns fallback when fetch rejects', async () => {
		const fetchImpl = vi.fn().mockRejectedValue(new Error('network down'));

		const result = await fetchCodexDescription('agora', 'fallback', { fetchImpl });

		expect(result).toBe('fallback');
	});

	it('returns fallback on timeout', async () => {
		vi.useFakeTimers();
		const fetchImpl = vi.fn(
			(_url: string, init?: { signal?: AbortSignal }) =>
				new Promise((_resolve, reject) => {
					init?.signal?.addEventListener('abort', () => {
						reject(new DOMException('Aborted', 'AbortError'));
					});
				})
		);

		const promise = fetchCodexDescription('agora', 'fallback', {
			fetchImpl,
			timeoutMs: 100
		});
		await vi.advanceTimersByTimeAsync(100);
		const result = await promise;

		expect(result).toBe('fallback');
	});

	it('caches successful fetches', async () => {
		const fetchImpl = vi.fn().mockResolvedValue({
			ok: true,
			text: async () => '# Agora\n\nCached description.'
		});

		const first = await fetchCodexDescription('agora', 'fallback', { fetchImpl });
		const second = await fetchCodexDescription('agora', 'fallback', { fetchImpl });

		expect(first).toBe('Cached description.');
		expect(second).toBe('Cached description.');
		expect(fetchImpl).toHaveBeenCalledTimes(1);
	});
});
