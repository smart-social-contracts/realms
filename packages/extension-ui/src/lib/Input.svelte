<script lang="ts">
	interface Props {
		value?: string;
		type?: string;
		placeholder?: string;
		disabled?: boolean;
		error?: boolean;
		id?: string;
		name?: string;
	}

	let {
		value = $bindable(''),
		type = 'text',
		placeholder,
		disabled = false,
		error = false,
		id,
		name
	}: Props = $props();
</script>

<input
	{id}
	{name}
	{type}
	{placeholder}
	{disabled}
	bind:value
	class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 transition-colors placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-gray-100 dark:placeholder:text-gray-500 input"
	class:border-red-500={error}
	class:ring-red-500={error}
	class:focus:border-red-500={error}
	class:focus:ring-red-500={error}
	class:dark:border-red-500={error}
/>

<style>
	.input {
		background-color: var(--color-bg-primary, #ffffff);
		border-color: var(--color-border-primary, #d1d5db);
		color: var(--color-text-primary, #111827);
	}

	:global(.dark) .input {
		background-color: var(--color-bg-primary, #1e293b);
		border-color: var(--color-border-primary, #475569);
		color: var(--color-text-primary, #f3f4f6);
	}
</style>
