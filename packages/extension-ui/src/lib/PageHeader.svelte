<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		subtitle?: string;
		actions?: Snippet;
	}

	let { title, subtitle, actions }: Props = $props();
</script>

<header class="pt-4">
	<div class="flex items-start justify-between gap-4">
		<div class="min-w-0">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white page-title">{title}</h1>
			{#if subtitle}
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400 page-subtitle">{subtitle}</p>
			{/if}
		</div>
		{#if actions}
			<div class="flex shrink-0 items-center gap-2">
				{@render actions()}
			</div>
		{/if}
	</div>
</header>

<style>
	.page-title {
		color: var(--color-text-primary, #111827);
	}

	.page-subtitle {
		color: var(--color-text-secondary, #6b7280);
	}

	:global(.dark) .page-title {
		color: var(--color-text-primary, #f9fafb);
	}

	:global(.dark) .page-subtitle {
		color: var(--color-text-secondary, #9ca3af);
	}
</style>
