<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		message?: string;
		actions?: Snippet;
	}

	let { title, message, actions }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center px-4 py-12 text-center empty-state">
	<h3 class="text-base font-semibold text-gray-900 dark:text-white empty-title">{title}</h3>
	{#if message}
		<p class="mt-2 max-w-md text-sm text-gray-500 dark:text-gray-400 empty-message">{message}</p>
	{/if}
	{#if actions}
		<div class="mt-4 flex flex-wrap items-center justify-center gap-2">
			{@render actions()}
		</div>
	{/if}
</div>

<style>
	.empty-title {
		color: var(--color-text-primary, #111827);
	}

	.empty-message {
		color: var(--color-text-secondary, #6b7280);
	}

	:global(.dark) .empty-title {
		color: var(--color-text-primary, #f9fafb);
	}

	:global(.dark) .empty-message {
		color: var(--color-text-secondary, #9ca3af);
	}
</style>
