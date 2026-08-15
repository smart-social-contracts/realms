import { describe, expect, it } from 'vitest';
import {
	CUSTOM_TOKEN_ID,
	SHARED_TOKEN_CATALOG,
	matchSharedToken,
	tokenDraftFromChoice
} from './sharedTokens';

describe('sharedTokens', () => {
	it('lists the registry wizard tokens', () => {
		expect(SHARED_TOKEN_CATALOG.map((token) => token.id)).toEqual(['REALMS', 'ckBTC', 'ckUSDC']);
	});

	it('matches a saved symbol or ledger to a catalog token', () => {
		expect(matchSharedToken({ symbol: 'realms' })?.id).toBe('REALMS');
		expect(matchSharedToken({ token_canister_id: 'mxzaz-hqaaa-aaaar-qaada-cai' })?.id).toBe(
			'ckBTC'
		);
		expect(matchSharedToken({ symbol: 'MINE', token_canister_id: 'aaaaa-aa' })).toBeUndefined();
	});

	it('fills ledger and decimals for a catalog choice', () => {
		expect(tokenDraftFromChoice('ckUSDC', { symbol: '', token_canister_id: '' }, 'test')).toEqual({
			symbol: 'ckUSDC',
			token_canister_id: 'xevnm-gaaaa-aaaar-qafnq-cai',
			decimals: 6
		});
	});

	it('requires symbol and canister for a custom token', () => {
		expect(
			tokenDraftFromChoice(CUSTOM_TOKEN_ID, { symbol: 'MINE', token_canister_id: '' }, 'test')
		).toBeNull();
		expect(
			tokenDraftFromChoice(
				CUSTOM_TOKEN_ID,
				{ symbol: 'MINE', token_canister_id: 'aaaaa-aa' },
				'test'
			)
		).toEqual({ symbol: 'MINE', token_canister_id: 'aaaaa-aa' });
	});
});
