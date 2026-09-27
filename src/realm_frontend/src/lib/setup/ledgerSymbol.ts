import { get } from 'svelte/store';
import { Actor, type HttpAgent } from '@dfinity/agent';
import { IDL } from '@dfinity/candid';
import { backendStore } from '$lib/canisters';

const icrc1IdlFactory = ({ IDL }: { IDL: typeof IDL }) =>
	IDL.Service({
		icrc1_symbol: IDL.Func([], [IDL.Text], ['query'])
	});

/** Read `icrc1_symbol` from a ledger the founder typed. */
export async function lookupLedgerSymbol(ledgerId: string): Promise<string> {
	const ledger = ledgerId.trim();
	if (!ledger) throw new Error('Enter a ledger canister id');
	const actor = get(backendStore) as { _agent?: HttpAgent } | null;
	const agent = actor?._agent;
	if (!agent) throw new Error('Sign in before reading the ledger symbol');
	const service = Actor.createActor(icrc1IdlFactory, { agent, canisterId: ledger });
	const symbol = await service.icrc1_symbol();
	const text = String(symbol || '').trim();
	if (!text) throw new Error('The ledger did not return a symbol');
	return text;
}
