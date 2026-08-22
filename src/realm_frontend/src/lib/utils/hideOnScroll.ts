/**
 * Directional hide/show for the mobile top bar.
 *
 * Scroll down past a small threshold → hide. Scroll up → show.
 * Always show near the top so the bar cannot get stuck off-screen.
 */

export type HideOnScrollState = {
	hidden: boolean;
	lastScrollTop: number;
};

export const HIDE_ON_SCROLL_THRESHOLD_PX = 8;
export const HIDE_ON_SCROLL_TOP_REVEAL_PX = 8;

export function initialHideOnScrollState(): HideOnScrollState {
	return { hidden: false, lastScrollTop: 0 };
}

export function nextHideOnScrollState(
	current: HideOnScrollState,
	scrollTop: number,
	options?: { threshold?: number; topReveal?: number; forceVisible?: boolean },
): HideOnScrollState {
	const threshold = options?.threshold ?? HIDE_ON_SCROLL_THRESHOLD_PX;
	const topReveal = options?.topReveal ?? HIDE_ON_SCROLL_TOP_REVEAL_PX;
	const clampedTop = Math.max(0, scrollTop);

	if (options?.forceVisible) {
		return { hidden: false, lastScrollTop: clampedTop };
	}

	if (clampedTop <= topReveal) {
		return { hidden: false, lastScrollTop: clampedTop };
	}

	const delta = clampedTop - current.lastScrollTop;
	if (Math.abs(delta) < threshold) {
		return current;
	}

	return {
		hidden: delta > 0,
		lastScrollTop: clampedTop,
	};
}
