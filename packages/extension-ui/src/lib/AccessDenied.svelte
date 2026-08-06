<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		operation?: string;
		message?: string;
		children?: Snippet;
	}

	let {
		operation,
		message = "You don't have permission to view this.",
		children
	}: Props = $props();
</script>

<div class="flex flex-col items-center justify-center px-4 py-12 text-center access-denied">
	<svg
		class="mb-4 h-12 w-12 text-gray-400 dark:text-gray-500 access-denied-icon"
		fill="none"
		stroke="currentColor"
		viewBox="0 0 24 24"
		xmlns="http://www.w3.org/2000/svg"
		aria-hidden="true"
	>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			stroke-width="1.5"
			d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
		/>
	</svg>

	<h3 class="text-base font-semibold text-gray-900 dark:text-white access-denied-title">Access denied</h3>

	{#if operation}
		<code
			class="mt-3 inline-block rounded-md bg-gray-100 px-2.5 py-1 font-mono text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400 access-denied-op"
		>
			{operation}
		</code>
	{/if}

	<p class="mt-3 max-w-md text-sm text-gray-500 dark:text-gray-400 access-denied-message">{message}</p>

	{#if children}
		<div class="mt-4">
			{@render children()}
		</div>
	{/if}
</div>

<style>
	.access-denied-title {
		color: var(--color-text-primary, #111827);
	}

	.access-denied-message {
		color: var(--color-text-secondary, #6b7280);
	}

	.access-denied-icon {
		color: var(--color-text-secondary, #9ca3af);
	}

	.access-denied-op {
		background-color: var(--color-bg-secondary, #f3f4f6);
		color: var(--color-text-secondary, #4b5563);
	}

	:global(.dark) .access-denied-title {
		color: var(--color-text-primary, #f9fafb);
	}

	:global(.dark) .access-denied-message {
		color: var(--color-text-secondary, #9ca3af);
	}

	:global(.dark) .access-denied-icon {
		color: var(--color-text-secondary, #6b7280);
	}

	:global(.dark) .access-denied-op {
		background-color: var(--color-bg-secondary, #1f2937);
		color: var(--color-text-secondary, #9ca3af);
	}
</style>
