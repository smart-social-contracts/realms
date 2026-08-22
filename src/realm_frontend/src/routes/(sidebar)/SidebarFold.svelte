<script lang="ts">
	/** Collapsible sidebar section body. Height eases via grid-template-rows. */
	export let open = false;
</script>

<div class="fold" class:is-open={open} aria-hidden={!open}>
	<div class="fold-inner" inert={!open ? true : undefined}>
		<slot />
	</div>
</div>

<style>
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
