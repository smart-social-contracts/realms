<script lang="ts">
	import type { Snippet } from 'svelte';

	type Tone = 'primary' | 'secondary' | 'danger';
	type Size = 'sm' | 'md';

	interface Props {
		tone?: Tone;
		size?: Size;
		disabled?: boolean;
		type?: 'button' | 'submit' | 'reset';
		onclick?: (event: MouseEvent) => void;
		children: Snippet;
	}

	let {
		tone = 'primary',
		size = 'md',
		disabled = false,
		type = 'button',
		onclick,
		children
	}: Props = $props();

	const toneClasses: Record<Tone, string> = {
		primary:
			'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-300 dark:bg-blue-600 dark:hover:bg-blue-700',
		secondary:
			'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus-visible:ring-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700',
		danger:
			'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-300 dark:bg-red-600 dark:hover:bg-red-700'
	};

	const sizeClasses: Record<Size, string> = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-5 py-2.5 text-sm'
	};
</script>

<button
	{type}
	{disabled}
	class="inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-60 {toneClasses[tone]} {sizeClasses[size]}"
	{onclick}
>
	{@render children()}
</button>
