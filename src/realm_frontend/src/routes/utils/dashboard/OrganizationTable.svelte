<script lang="ts">
	import { onMount } from 'svelte';
	import LastRange from '../widgets/LastRange.svelte';
	import {
		Button,
		Card,
		Heading,
		Spinner,
		Table,
		TableBody,
		TableBodyCell,
		TableBodyRow,
		TableHead,
		TableHeadCell
	} from 'flowbite-svelte';
	import {
		CalendarMonthSolid,
		CaretRightSolid,
		UsersSolid,
		BuildingSolid
	} from 'flowbite-svelte-icons';

	import { backend } from '$lib/canisters';

	export let dark: boolean = false;

	const headers = [
		{ text: 'Name', icon: BuildingSolid },
		{ text: 'Type', icon: null },
		{ text: 'Members', icon: UsersSolid },
		{ text: 'Created', icon: CalendarMonthSolid },
		{ text: 'Actions', icon: null }
	];

	let data: any[] = [];
	let loading = true;

	function formatDate(ts: string): string {
		if (!ts) return '-';
		try {
			const d = new Date(ts.replace(' ', 'T'));
			return d.toLocaleDateString('en', { year: 'numeric', month: '2-digit', day: '2-digit' });
		} catch {
			return ts;
		}
	}

	async function fetchOrganizations() {
		loading = true;
		try {
			const response = await backend.get_objects_paginated("Organization", 0, 50, "desc");
			if (response?.success && response?.data?.objectsListPaginated) {
				const objects = response.data.objectsListPaginated.objects || [];
				data = objects.map((s: string) => {
					const org = JSON.parse(s);
					return {
						id: org.id || org._id || '',
						name: org.name || org.id || 'Unnamed',
						type: org.type || org.governance_type || '-',
						members: org.member_count || org.population || 0,
						creationTime: formatDate(org.timestamp_created),
					};
				});
			}
		} catch (error) {
			console.error('Error fetching organizations:', error);
		}
		loading = false;
	}

	onMount(fetchOrganizations);
</script>

<Card size="xl" class="max-w-none shadow-md rounded-lg border-0">
	<div class="items-center justify-between lg:flex">
		<div class="mb-4 mt-px lg:mb-0">
			<Heading tag="h3" class="-ml-0.25 mb-2 text-xl font-semibold dark:text-white flex items-center gap-2">
				<svelte:component this={BuildingSolid} class="w-6 h-6" />
				Organizations
			</Heading>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				Registered organizations in the realm
			</p>
		</div>
	</div>
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<Spinner size="6" />
			<span class="ml-3 text-gray-400 text-sm">Loading organizations...</span>
		</div>
	{:else if data.length === 0}
		<div class="flex items-center justify-center py-12">
			<p class="text-gray-400">No organizations found</p>
		</div>
	{:else}
		<Table
			hoverable={true}
			noborder
			striped
			class="mt-6 min-w-full divide-y divide-gray-200 dark:divide-gray-600 rounded-lg overflow-hidden"
		>
			<TableHead class="bg-gray-50 dark:bg-gray-700">
				{#each headers as header}
					<TableHeadCell class="whitespace-nowrap p-4 font-medium text-gray-700 dark:text-gray-300">
						<div class="flex items-center gap-2">
							{#if header.icon}
								<svelte:component this={header.icon} class="w-4 h-4" />
							{/if}
							{header.text}
						</div>
					</TableHeadCell>
				{/each}
			</TableHead>
			<TableBody>
				{#each data as org}
					<TableBodyRow class="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150">
						<TableBodyCell class="px-4">
							<a href="/ggg?type=Organization&id={org.id}" 
							   class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium">
								{org.name}
							</a>
						</TableBodyCell>
						<TableBodyCell class="px-4">
							<span class="text-sm text-gray-600">{org.type}</span>
						</TableBodyCell>
						<TableBodyCell class="px-4">
							<div class="font-medium">{org.members}</div>
						</TableBodyCell>
						<TableBodyCell class="px-4">
							<div class="text-sm text-gray-600 dark:text-gray-300">
								{org.creationTime}
							</div>
						</TableBodyCell>
						<TableBodyCell class="px-4">
							<Button size="xs" color="blue" href="/ggg?type=Organization&id={org.id}" class="rounded-lg font-medium">
								View Details
								<svelte:component this={CaretRightSolid} class="w-4 h-4 ml-1" />
							</Button>
						</TableBodyCell>
					</TableBodyRow>
				{/each}
			</TableBody>
		</Table>
	{/if}
</Card>
