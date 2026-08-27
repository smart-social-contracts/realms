import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const srcDir = join(dirname(fileURLToPath(import.meta.url)));

function readSrc(relative: string): string {
	return readFileSync(join(srcDir, relative), 'utf8');
}

describe('join_realm departments Candid decode', () => {
	it('generated IDL still requires departments: vec text', () => {
		const didJs = readSrc('../../../declarations/realm_backend/realm_backend.did.js');
		expect(didJs).toContain("'departments' : IDL.Vec(IDL.Text)");
		expect(didJs).toContain('const UserGetRecord = IDL.Record({');
	});

	it('join uses a Reserved departments IDL so missing vec {} cannot fail closed', () => {
		const joinIdl = readSrc('joinIdl.js');
		expect(joinIdl).toContain('departments: I.Reserved');
		expect(joinIdl).toContain('join_realm');
		const joinPage = readSrc('../routes/(no-sidebar)/join/+page.svelte');
		expect(joinPage).toContain('asJoinSafeActor');
		expect(joinPage).toContain('actor.join_realm');
	});

	it('canisters rebuild the join actor with the same identity and canister', () => {
		const canisters = readSrc('canisters.js');
		expect(canisters).toContain('export async function asJoinSafeActor');
		expect(canisters).toContain('joinIdlFactory');
		expect(canisters).toContain('Actor.canisterIdOf');
	});
});
