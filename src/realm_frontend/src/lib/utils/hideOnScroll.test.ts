import { describe, expect, it } from 'vitest';
import { initialHideOnScrollState, nextHideOnScrollState } from './hideOnScroll';

describe('nextHideOnScrollState', () => {
	it('starts visible at the top', () => {
		expect(initialHideOnScrollState()).toEqual({ hidden: false, lastScrollTop: 0 });
	});

	it('hides after scrolling down past the threshold', () => {
		const next = nextHideOnScrollState({ hidden: false, lastScrollTop: 20 }, 40);
		expect(next).toEqual({ hidden: true, lastScrollTop: 40 });
	});

	it('shows after scrolling up past the threshold', () => {
		const next = nextHideOnScrollState({ hidden: true, lastScrollTop: 80 }, 60);
		expect(next).toEqual({ hidden: false, lastScrollTop: 60 });
	});

	it('ignores jitter below the threshold so the bar does not flicker', () => {
		const current = { hidden: false, lastScrollTop: 40 };
		expect(nextHideOnScrollState(current, 44)).toEqual(current);
		expect(nextHideOnScrollState(current, 36)).toEqual(current);
	});

	it('always shows when the user is back at the top', () => {
		const next = nextHideOnScrollState({ hidden: true, lastScrollTop: 80 }, 0);
		expect(next).toEqual({ hidden: false, lastScrollTop: 0 });
	});

	it('treats rubber-band / negative scrollTop as the top', () => {
		const next = nextHideOnScrollState({ hidden: true, lastScrollTop: 40 }, -12);
		expect(next).toEqual({ hidden: false, lastScrollTop: 0 });
	});

	it('stays visible when forceVisible is set (open mobile drawer)', () => {
		const next = nextHideOnScrollState(
			{ hidden: true, lastScrollTop: 120 },
			200,
			{ forceVisible: true },
		);
		expect(next).toEqual({ hidden: false, lastScrollTop: 200 });
	});

	it('accumulates small downward steps until the threshold is crossed', () => {
		let state = { hidden: false, lastScrollTop: 20 };
		state = nextHideOnScrollState(state, 24);
		expect(state.hidden).toBe(false);
		state = nextHideOnScrollState(state, 29);
		expect(state).toEqual({ hidden: true, lastScrollTop: 29 });
	});
});
