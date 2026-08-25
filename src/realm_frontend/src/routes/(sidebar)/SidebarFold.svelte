<script lang="ts">
	/**
	 * Animated disclosure fold (200ms height + chevron).
	 *
	 * Not a native details widget: Chrome 131+ wraps the body in a
	 * details-content box (height 0, display block), so a 0fr→1fr grid row
	 * resolves to 0px and the panel never opens. A button avoids that UA box,
	 * Svelte rewriting the open attribute, and nested-details hit-testing
	 * (wrong-row chevrons).
	 */
	export let open = false;
	export let summaryClass =
		'flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer';
	export let onToggle: ((nextOpen: boolean) => void) | undefined = undefined;

	function toggle() {
		onToggle?.(!open);
	}
</script>

<div class="sidebar-fold" class:is-open={open}>
	<button type="button" class="fold-summary {summaryClass}" aria-expanded={open} onclick={toggle}>
		<slot name="header" />
	</button>
	<div class="fold">
		<div class="fold-inner" inert={!open ? true : undefined}>
			<slot />
		</div>
	</div>
</div>

<style>
	.fold-summary {
		appearance: none;
		border: 0;
		margin: 0;
		text-align: inherit;
		font: inherit;
		color: inherit;
	}
	.fold {
		display: grid;
		grid-template-rows: 0fr;
		transition: grid-template-rows 200ms ease-out;
	}
	.sidebar-fold.is-open > .fold {
		grid-template-rows: 1fr;
	}
	.fold-inner {
		min-height: 0;
		overflow: hidden;
	}
	.sidebar-fold > .fold-summary :global(.fold-chevron) {
		flex-shrink: 0;
		transform: rotate(-90deg);
		transition: transform 200ms ease-out;
	}
	.sidebar-fold.is-open > .fold-summary :global(.fold-chevron) {
		transform: rotate(0deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.fold,
		.sidebar-fold > .fold-summary :global(.fold-chevron) {
			transition: none;
		}
	}
</style>
