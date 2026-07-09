import { describe, expect, it } from 'vitest';
import { hasMembership, pickPrimaryHit, type MembershipHit } from './federatedMembership';

function hit(canisterId: string, profiles: string[] = ['member']): MembershipHit {
	return {
		canisterId,
		isCapital: false,
		profiles,
		response: {
			success: true,
			data: { userGet: { profiles } },
		},
	};
}

describe('hasMembership', () => {
	it('requires success + non-empty profiles', () => {
		expect(hasMembership(null)).toBe(false);
		expect(hasMembership({ success: false })).toBe(false);
		expect(hasMembership({ success: true, data: { userGet: { profiles: [] } } })).toBe(false);
		expect(hasMembership({ success: true, data: { userGet: { profiles: ['member'] } } })).toBe(
			true
		);
	});
});

describe('pickPrimaryHit', () => {
	it('returns null for empty hits', () => {
		expect(pickPrimaryHit([])).toBeNull();
	});

	it('prefers a still-valid cache', () => {
		const hits = [hit('q1'), hit('q2'), hit('q3')];
		expect(pickPrimaryHit(hits, 'q2')?.canisterId).toBe('q2');
	});

	it('falls back to the first hit when cache misses', () => {
		const hits = [hit('q1'), hit('q2')];
		expect(pickPrimaryHit(hits, 'missing')?.canisterId).toBe('q1');
		expect(pickPrimaryHit(hits)?.canisterId).toBe('q1');
	});
});
