<script lang="ts">
	import { Avatar, Button, Card, Heading, Badge } from 'flowbite-svelte';
	import { PenOutline, TrashBinOutline, CheckCircleSolid } from 'flowbite-svelte-icons';
	import { styles, cn } from '$lib/theme/utilities';

	export let src: string;
	export let title: string;
	export let description: string;
	export let status: string = 'Verified'; // Default status is Verified
	
	let isEnabled = true; // Track enable/disable state
</script>

<Card
	size="xl"
	class="h-full block bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-blue-200 dark:hover:border-blue-700 transition-all duration-200"
>
	<div class="flex flex-col gap-4">
		<!-- Logo Container - Full Width at Top -->
		<div class="flex items-center justify-center h-20 w-full p-3">
			<img src={src} alt={title} class="h-full max-w-full object-contain" />
		</div>

		<div class="flex-1 flex flex-col">
			<div class="flex flex-wrap justify-between items-start gap-2 mb-2">
				<Heading tag="h3" class="text-xl font-semibold text-gray-900 dark:text-white">{title}</Heading>
				{#if status === 'Verified'}
					<Badge color="green" class="flex items-center gap-1 px-2.5 py-1">
						<CheckCircleSolid class="w-3 h-3" />
						Verified
					</Badge>
				{:else if status === 'Pending'}
					<Badge color="yellow" class="px-2.5 py-1">Pending</Badge>
				{:else}
					<Badge color="dark" class="px-2.5 py-1">{status}</Badge>
				{/if}
			</div>
			
			<p class="mb-4 text-sm text-gray-600 dark:text-gray-400 flex-grow min-h-[40px]">{description}</p>
			
			<div class="flex items-center gap-3 mt-auto">
				<Button
					size="sm"
					class={cn(
						'w-full sm:w-auto',
						isEnabled ? styles.button.secondary() : styles.button.success()
					)}
					on:click={() => (isEnabled = !isEnabled)}
				>
					{isEnabled ? 'Disable' : 'Enable'}
				</Button>
			</div>
		</div>
	</div>
</Card>

<!--
@component
[Go to docs](https://flowbite-svelte-admin-dashboard.vercel.app/)
## Props
@prop export let src: string;
-->
