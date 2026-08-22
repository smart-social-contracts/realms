<script lang="ts">
	/** Native <details> fold. Open/close is the browser's job; Svelte only syncs route auto-expand. */
	export let open = false;
	export let summaryClass =
		'flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer';
	export let onToggle: ((nextOpen: boolean) => void) | undefined = undefined;

	function detailsRoot(node: HTMLDetailsElement, isOpen: boolean) {
		let current = isOpen;
		let syncing = false;

		function syncInert() {
			const inner = node.querySelector('.fold-inner');
			if (!(inner instanceof HTMLElement)) return;
			if (node.open) {
				inner.removeAttribute('inert');
			} else {
				inner.setAttribute('inert', '');
			}
		}

		function apply(nextOpen: boolean) {
			current = nextOpen;
			if (node.open !== nextOpen) {
				syncing = true;
				node.open = nextOpen;
				syncing = false;
			}
			syncInert();
		}

		function handleToggle() {
			syncInert();
			if (syncing || node.open === current) return;
			onToggle?.(node.open);
		}

		apply(isOpen);
		node.addEventListener('toggle', handleToggle);
		return {
			update(nextOpen: boolean) {
				apply(nextOpen);
			},
			destroy() {
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
	.sidebar-details[open] .fold {
		grid-template-rows: 1fr;
	}
	.fold-inner {
		min-height: 0;
		overflow: hidden;
	}
	.sidebar-details :global(.fold-chevron) {
		transform: rotate(0deg);
		transition: transform 200ms ease-out;
	}
	.sidebar-details:not([open]) :global(.fold-chevron) {
		transform: rotate(-90deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.fold,
		.sidebar-details :global(.fold-chevron) {
			transition: none;
		}
	}
</style>
