<script lang="ts">
	import { Avatar, Button, Card, Heading, Badge } from 'flowbite-svelte';
	import { PenOutline, TrashBinOutline, CheckCircleSolid } from 'flowbite-svelte-icons';

	export let src: string;
	export let title: string;
	export let description: string;
	export let status: string = 'Verified'; // Default status is Verified
</script>

<Card
	size="xl"
	class="h-full block bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 hover:border-blue-200 dark:hover:border-blue-700 transition-all duration-200"
>
	<div class="flex flex-col sm:flex-row gap-6">
		<!-- Logo Container -->
		<div class="flex items-center justify-center h-28 w-28 bg-gray-100 dark:bg-gray-700 rounded-lg p-2 border border-gray-200 dark:border-gray-600">
			<img src={src} alt={title} class="h-full w-full object-contain" />
		</div>

		<div class="flex-1">
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
					<Badge color="gray" class="px-2.5 py-1">{status}</Badge>
				{/if}
			</div>
			
			<p class="mb-4 text-sm text-gray-600 dark:text-gray-400">{description}</p>
			
			<div class="flex items-center gap-3 mt-auto">
				<Button size="xs" color="light" class="px-3 py-1.5 flex items-center gap-1 border border-gray-200 dark:border-gray-600">
					<PenOutline class="w-3.5 h-3.5" />
					Update
				</Button>
				<Button size="xs" color="light" class="px-3 py-1.5 flex items-center gap-1 text-red-600 hover:text-red-700 dark:text-red-500 border border-gray-200 dark:border-gray-600">
					<TrashBinOutline class="w-3.5 h-3.5" />
					Delete
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
