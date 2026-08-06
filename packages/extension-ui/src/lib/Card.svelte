<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title?: string;
		header?: Snippet;
		children: Snippet;
	}

	let { title, header, children }: Props = $props();
</script>

<section class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 card">
	{#if title || header}
		<div class="border-b border-gray-200 px-4 py-3 dark:border-gray-700 card-header">
			{#if header}
				{@render header()}
			{:else if title}
				<h2 class="text-base font-semibold text-gray-900 dark:text-white card-title">{title}</h2>
			{/if}
		</div>
	{/if}
	<div class="p-4 card-body">
		{@render children()}
	</div>
</section>

<style>
	.card {
		background-color: var(--color-bg-primary, #ffffff);
		border-color: var(--color-border-primary, #e5e7eb);
	}

	.card-header {
		border-color: var(--color-border-primary, #e5e7eb);
	}

	.card-title {
		color: var(--color-text-primary, #111827);
	}

	.card-body {
		color: var(--color-text-primary, #111827);
	}

	:global(.dark) .card {
		background-color: var(--color-bg-primary, #1f2937);
		border-color: var(--color-border-primary, #374151);
	}

	:global(.dark) .card-header {
		border-color: var(--color-border-primary, #374151);
	}

	:global(.dark) .card-title,
	:global(.dark) .card-body {
		color: var(--color-text-primary, #f9fafb);
	}
</style>
