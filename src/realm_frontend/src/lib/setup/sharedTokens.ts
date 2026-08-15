export type SetupTokenNetwork = 'test' | 'staging' | 'demo';

export interface SharedTokenOption {
	id: string;
	name: string;
	symbol: string;
	description: string;
	decimals: number;
	ledgers: Record<SetupTokenNetwork, string>;
	indexers?: Partial<Record<SetupTokenNetwork, string>>;
}

export const SHARED_TOKEN_CATALOG: SharedTokenOption[] = [
	{
		id: 'REALMS',
		name: 'REALMS Token',
		symbol: 'REALMS',
		description: 'The shared mundus-wide token, common to all realms',
		decimals: 8,
		ledgers: {
			staging: '2rqin-xaaaa-aaaah-qunsq-cai',
			demo: 'xbkkh-syaaa-aaaah-qq3ya-cai',
			test: 'nusyl-jiaaa-aaaae-qj6mq-cai'
		}
	},
	{
		id: 'ckBTC',
		name: 'ckBTC',
		symbol: 'ckBTC',
		description: 'Chain-Key Bitcoin — IC-native Bitcoin twin',
		decimals: 8,
		ledgers: {
			staging: 'mxzaz-hqaaa-aaaar-qaada-cai',
			demo: 'mxzaz-hqaaa-aaaar-qaada-cai',
			test: 'mxzaz-hqaaa-aaaar-qaada-cai'
		},
		indexers: {
			staging: 'n5wcd-faaaa-aaaar-qaaea-cai',
			demo: 'n5wcd-faaaa-aaaar-qaaea-cai',
			test: 'n5wcd-faaaa-aaaar-qaaea-cai'
		}
	},
	{
		id: 'ckUSDC',
		name: 'ckUSDC',
		symbol: 'ckUSDC',
		description: 'Chain-Key USDC — IC-native USD stablecoin',
		decimals: 6,
		ledgers: {
			staging: 'xevnm-gaaaa-aaaar-qafnq-cai',
			demo: 'xevnm-gaaaa-aaaar-qafnq-cai',
			test: 'xevnm-gaaaa-aaaar-qafnq-cai'
		}
	}
];

export const CUSTOM_TOKEN_ID = 'custom';

export function setupTokenNetwork(): SetupTokenNetwork {
	const ids = (globalThis as { __CANISTER_IDS?: { portal_url?: string } }).__CANISTER_IDS;
	const portal = ids?.portal_url || '';
	if (portal.includes('staging.')) return 'staging';
	if (portal.includes('demo.')) return 'demo';
	return 'test';
}

export function sharedTokenById(id: string): SharedTokenOption | undefined {
	return SHARED_TOKEN_CATALOG.find((token) => token.id === id);
}

export function matchSharedToken(input: {
	symbol?: string;
	token_canister_id?: string;
}): SharedTokenOption | undefined {
	const canister = (input.token_canister_id || '').trim();
	if (canister) {
		const byLedger = SHARED_TOKEN_CATALOG.find((token) =>
			Object.values(token.ledgers).includes(canister)
		);
		if (byLedger) return byLedger;
	}
	const symbol = (input.symbol || '').trim().toUpperCase();
	if (!symbol) return undefined;
	return SHARED_TOKEN_CATALOG.find(
		(token) => token.id.toUpperCase() === symbol || token.symbol.toUpperCase() === symbol
	);
}

export function tokenDraftFromChoice(
	choiceId: string,
	custom: { symbol: string; token_canister_id: string },
	network: SetupTokenNetwork = setupTokenNetwork()
): Record<string, string | number> | null {
	if (choiceId === CUSTOM_TOKEN_ID) {
		const symbol = custom.symbol.trim();
		const token_canister_id = custom.token_canister_id.trim();
		if (!symbol || !token_canister_id) return null;
		return { symbol, token_canister_id };
	}
	const token = sharedTokenById(choiceId);
	if (!token) return null;
	const draft: Record<string, string | number> = {
		symbol: token.symbol,
		token_canister_id: token.ledgers[network],
		decimals: token.decimals
	};
	const indexer = token.indexers?.[network];
	if (indexer) draft.indexer_canister_id = indexer;
	return draft;
}
