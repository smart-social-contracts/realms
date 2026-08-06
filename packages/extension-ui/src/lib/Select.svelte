<script lang="ts">
	interface Option {
		value: string;
		label: string;
	}

	interface Props {
		value?: string;
		options: Option[];
		disabled?: boolean;
		id?: string;
		name?: string;
	}

	let { value = $bindable(''), options, disabled = false, id, name }: Props = $props();
</script>

<select
	{id}
	{name}
	{disabled}
	bind:value
	class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-gray-100 select"
>
	{#each options as option}
		<option value={option.value}>{option.label}</option>
	{/each}
</select>

<style>
	.select {
		background-color: var(--color-bg-primary, #ffffff);
		border-color: var(--color-border-primary, #d1d5db);
		color: var(--color-text-primary, #111827);
	}

	:global(.dark) .select {
		background-color: var(--color-bg-primary, #1e293b);
		border-color: var(--color-border-primary, #475569);
		color: var(--color-text-primary, #f3f4f6);
	}
</style>
