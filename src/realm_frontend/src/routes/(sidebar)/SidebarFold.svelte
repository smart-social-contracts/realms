<script lang="ts">
	/**
	 * Animated disclosure fold (200ms height + chevron).
	 *
	 * Not a native details widget: Chrome 131+ wraps the body in a
	 * details-content box (height 0, display block), so a 0fr→1fr grid row
	 * resolves to 0px and the panel never opens. A button avoids that UA box
	 * and nested-details hit-testing (wrong-row chevrons).
	 *
	 * Visual open state is assigned here (`open = !open`) and bound to a
	 * parent record. Live #315 (7734920) did call the parent callback; the
	 * parent stored open ids in a Set that the template never read, so
	 * Svelte 5 compiled `open={sectionOpen(id)}` as a derived over a plain
	 * `let` and never invalidated `is-open` / aria-expanded after a tap.
	 */
	export let open = false;
	export let summaryClass =
		'flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer';
	/** Parent bookkeeping (userHasToggledFolds). Name must not start with `on`. */
	export let setOpen: ((nextOpen: boolean) => void) | undefined = undefined;

	function toggle() {
		open = !open;
		setOpen?.(open);
	}
</script>

<div class="sidebar-fold" class:is-open={open}>
	<button type="button" class="fold-summary {summaryClass}" aria-expanded={open} onclick={toggle}>
		<slot name="header" />
	</button>
	<div
		class="fold"
		style:display="grid"
		style:overflow="hidden"
		style:grid-template-rows={open ? '1fr' : '0fr'}
	>
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
		overflow: hidden;
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
