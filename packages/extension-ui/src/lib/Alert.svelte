<script lang="ts">
	import type { Snippet } from 'svelte';

	type Tone = 'info' | 'success' | 'warning' | 'error';

	interface Props {
		tone: Tone;
		title?: string;
		children: Snippet;
	}

	let { tone, title, children }: Props = $props();

	const toneClasses: Record<Tone, string> = {
		info: 'border-blue-500 bg-blue-50 text-blue-800 dark:border-blue-400 dark:bg-blue-900/20 dark:text-blue-300',
		success:
			'border-green-500 bg-green-50 text-green-800 dark:border-green-400 dark:bg-green-900/20 dark:text-green-300',
		warning:
			'border-amber-500 bg-amber-50 text-amber-800 dark:border-amber-400 dark:bg-amber-900/20 dark:text-amber-300',
		error: 'border-red-500 bg-red-50 text-red-800 dark:border-red-400 dark:bg-red-900/20 dark:text-red-300'
	};

	const alertRole = $derived(tone === 'error' || tone === 'warning' ? 'alert' : undefined);
</script>

<div class="rounded-r-md border-l-4 px-4 py-3 alert {toneClasses[tone]}" role={alertRole}>
	{#if title}
		<p class="text-sm font-medium alert-title">{title}</p>
	{/if}
	<div class="text-sm alert-body" class:mt-1={!!title}>
		{@render children()}
	</div>
</div>

<style>
	.alert-title {
		color: inherit;
	}

	.alert-body {
		color: inherit;
	}
</style>
