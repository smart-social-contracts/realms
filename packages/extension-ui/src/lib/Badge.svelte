<script lang="ts">
	import type { Snippet } from 'svelte';

	type Tone = 'gray' | 'green' | 'amber' | 'red' | 'blue';

	interface Props {
		tone?: Tone;
		children: Snippet;
	}

	let { tone = 'gray', children }: Props = $props();

	const toneClasses: Record<Tone, string> = {
		gray: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
		green: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
		amber: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
		red: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
		blue: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
	};
</script>

<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {toneClasses[tone]} badge">
	{@render children()}
</span>

<style>
	.badge {
		background-color: var(--color-bg-secondary, transparent);
		color: var(--color-text-primary, inherit);
	}

	:global(.dark) .badge {
		color: var(--color-text-primary, inherit);
	}
</style>
