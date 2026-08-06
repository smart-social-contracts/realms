<script lang="ts">
	type Size = 'sm' | 'md' | 'lg';

	interface Props {
		size?: Size;
		label?: string;
	}

	let { size = 'md', label }: Props = $props();

	const sizeClasses: Record<Size, string> = {
		sm: 'h-4 w-4',
		md: 'h-6 w-6',
		lg: 'h-8 w-8'
	};
</script>

<svg
	class="animate-spin text-blue-600 dark:text-blue-400 spinner {sizeClasses[size]}"
	fill="none"
	viewBox="0 0 24 24"
	aria-hidden={label ? undefined : true}
	role={label ? 'status' : undefined}
>
	<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
	<path
		class="opacity-75"
		fill="currentColor"
		d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
	></path>
</svg>
{#if label}
	<span class="sr-only">{label}</span>
{/if}

<style>
	.spinner {
		color: var(--color-primary-600, #2563eb);
	}

	:global(.dark) .spinner {
		color: var(--color-primary-600, #60a5fa);
	}
</style>
