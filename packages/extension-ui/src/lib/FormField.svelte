<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		label: string;
		forId?: string;
		error?: string;
		hint?: string;
		children: Snippet;
	}

	let { label, forId, error, hint, children }: Props = $props();
</script>

<div class="form-field">
	<label
		for={forId}
		class="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300 form-field-label"
	>
		{label}
	</label>
	{@render children()}
	{#if hint && !error}
		<p class="mt-1 text-xs text-gray-500 dark:text-gray-400 form-field-hint">{hint}</p>
	{/if}
	{#if error}
		<p class="mt-1 text-xs text-red-600 dark:text-red-400 form-field-error">{error}</p>
	{/if}
</div>

<style>
	.form-field-label {
		color: var(--color-text-primary, #374151);
	}

	.form-field-hint {
		color: var(--color-text-secondary, #6b7280);
	}

	.form-field-error {
		color: var(--color-error-600, #dc2626);
	}

	:global(.dark) .form-field-label {
		color: var(--color-text-primary, #d1d5db);
	}

	:global(.dark) .form-field-hint {
		color: var(--color-text-secondary, #9ca3af);
	}

	:global(.dark) .form-field-error {
		color: var(--color-error-600, #f87171);
	}
</style>
