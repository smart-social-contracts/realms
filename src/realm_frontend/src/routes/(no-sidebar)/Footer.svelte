<script>
	import { testMode } from '$lib/stores/realmInfo';
	import TestFlagsModal from '$lib/components/TestFlagsModal.svelte';

	let testFlagsOpen = false;
</script>

<footer class="px-4 py-6 md:flex md:items-center md:justify-center md:py-10 2xl:px-0">
	{#if $testMode}
		<button
			type="button"
			class="rounded border border-amber-400 px-2 py-0.5 text-xs font-medium text-amber-600 hover:bg-amber-50 dark:border-amber-500 dark:text-amber-400 dark:hover:bg-gray-700"
			on:click={() => (testFlagsOpen = true)}
		>
			Test flags
		</button>
		<TestFlagsModal bind:open={testFlagsOpen} />
	{/if}
</footer>
