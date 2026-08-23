<script lang="ts">
	/** Animated <details> fold. Open and close both run the same 200ms height + chevron motion. */
	export let open = false;
	export let summaryClass =
		'flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer';
	export let onToggle: ((nextOpen: boolean) => void) | undefined = undefined;

	const FOLD_MS = 200;

	function detailsRoot(node: HTMLDetailsElement, isOpen: boolean) {
		let current = isOpen;
		let syncing = false;
		let initialized = false;
		let closeTimer: ReturnType<typeof setTimeout> | undefined;
		const summary = node.querySelector(':scope > summary');

		function prefersReducedMotion(): boolean {
			return (
				typeof window !== 'undefined' &&
				window.matchMedia('(prefers-reduced-motion: reduce)').matches
			);
		}

		function clearCloseTimer() {
			if (closeTimer === undefined) return;
			clearTimeout(closeTimer);
			closeTimer = undefined;
		}

		function setOpenAttr(nextOpen: boolean) {
			if (node.open === nextOpen) return;
			syncing = true;
			node.open = nextOpen;
			syncing = false;
		}

		function syncInert(expanded: boolean) {
			const inner = node.querySelector(':scope > .fold > .fold-inner');
			if (!(inner instanceof HTMLElement)) return;
			if (expanded) inner.removeAttribute('inert');
			else inner.setAttribute('inert', '');
		}

		function finishClose() {
			closeTimer = undefined;
			setOpenAttr(false);
		}

		function apply(nextOpen: boolean) {
			current = nextOpen;
			clearCloseTimer();

			if (nextOpen) {
				// Content must stay in the tree for the 0fr → 1fr transition.
				setOpenAttr(true);
				if (!initialized) {
					node.classList.add('is-open');
					syncInert(true);
					initialized = true;
					return;
				}
				node.classList.remove('is-open');
				void node.offsetHeight;
				node.classList.add('is-open');
				syncInert(true);
				return;
			}

			initialized = true;
			node.classList.remove('is-open');
			syncInert(false);
			if (!node.open) return;
			if (prefersReducedMotion()) {
				finishClose();
				return;
			}
			closeTimer = setTimeout(finishClose, FOLD_MS);
		}

		function handleSummaryClick(event: Event) {
			event.preventDefault();
			const nextOpen = !current;
			apply(nextOpen);
			onToggle?.(nextOpen);
		}

		function handleToggle() {
			if (syncing || node.open === current) return;
			const nextOpen = node.open;
			if (!nextOpen) {
				// Native close would hide content immediately — reopen, then animate shut.
				setOpenAttr(true);
				apply(false);
				onToggle?.(false);
				return;
			}
			apply(true);
			onToggle?.(true);
		}

		apply(isOpen);
		initialized = true;
		summary?.addEventListener('click', handleSummaryClick);
		node.addEventListener('toggle', handleToggle);
		return {
			update(nextOpen: boolean) {
				if (nextOpen === current && node.classList.contains('is-open') === nextOpen) return;
				apply(nextOpen);
			},
			destroy() {
				clearCloseTimer();
				summary?.removeEventListener('click', handleSummaryClick);
				node.removeEventListener('toggle', handleToggle);
			}
		};
	}
</script>

<details class="sidebar-details" use:detailsRoot={open}>
	<summary class="fold-summary {summaryClass}">
		<slot name="header" />
	</summary>
	<div class="fold">
		<div class="fold-inner">
			<slot />
		</div>
	</div>
</details>

<style>
	.fold-summary {
		list-style: none;
	}
	.fold-summary::-webkit-details-marker {
		display: none;
	}
	.fold {
		display: grid;
		grid-template-rows: 0fr;
		transition: grid-template-rows 200ms ease-out;
	}
	.sidebar-details.is-open .fold {
		grid-template-rows: 1fr;
	}
	.fold-inner {
		min-height: 0;
		overflow: hidden;
	}
	.sidebar-details :global(.fold-chevron) {
		flex-shrink: 0;
		transform: rotate(-90deg);
		transition: transform 200ms ease-out;
	}
	.sidebar-details.is-open :global(.fold-chevron) {
		transform: rotate(0deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.fold,
		.sidebar-details :global(.fold-chevron) {
			transition: none;
		}
	}
</style>
