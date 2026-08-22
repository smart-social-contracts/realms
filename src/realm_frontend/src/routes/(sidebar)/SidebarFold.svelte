<script lang="ts">
	/** Native <details> fold. The browser opens/closes on summary click. */
	export let open = false;
	export let summaryClass =
		'flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer';
	export let onToggle: ((nextOpen: boolean) => void) | undefined = undefined;

	function handleToggle(event: Event) {
		const el = event.currentTarget as HTMLDetailsElement;
		if (el.open === open) return;
		onToggle?.(el.open);
	}
</script>

<details class="sidebar-details" {open} ontoggle={handleToggle}>
	<summary class="fold-summary {summaryClass}">
		<slot name="header" />
	</summary>
	<div class="fold" class:is-open={open} aria-hidden={!open}>
		<div class="fold-inner" inert={!open ? true : undefined}>
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
	.fold.is-open {
		grid-template-rows: 1fr;
	}
	.fold-inner {
		min-height: 0;
		overflow: hidden;
	}
	@media (prefers-reduced-motion: reduce) {
		.fold {
			transition: none;
		}
	}
</style>
