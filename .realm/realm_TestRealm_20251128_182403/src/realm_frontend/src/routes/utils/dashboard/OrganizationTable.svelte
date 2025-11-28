<script lang="ts">
	import { onMount } from 'svelte';
	import LastRange from '../widgets/LastRange.svelte';
	import {
		Button,
		Card,
		Checkbox,
		Dropdown,
		Heading,
		Input,
		Table,
		TableBody,
		TableBodyCell,
		TableBodyRow,
		TableHead,
		TableHeadCell
	} from 'flowbite-svelte';
	import {
		CalendarMonthSolid,
		CaretDownSolid,
		CaretRightSolid,
		UsersSolid,
		DollarOutline,
		ClipboardCheckSolid,
		BuildingSolid
	} from 'flowbite-svelte-icons';

	import { backend } from '$lib/canisters';
	import { snapshots } from '$lib/stores/auth';

	export let dark: boolean = false;

	const headers = [
		{ text: 'Id', icon: BuildingSolid },
		{ text: 'Members', icon: UsersSolid },
		{ text: 'Token Balance', icon: DollarOutline },
		{ text: 'Proposals', icon: ClipboardCheckSolid },
		{ text: 'Creation Time', icon: CalendarMonthSolid },
		{ text: 'Actions', icon: null }
	];
	
	// Mock data for organizations
	export let data = [
		{
			id: 'org-acme-corp',
			members: 12,
			membersList: 'alice@example.com, bob@example.com, carol@example.com, dave@example.com, eve@example.com, frank@example.com',
			tokenBalance: 150000,
			tokenName: 'ACME Token',
			proposals: 8,
			activeProposals: 2,
			creationTime: '01/01/2023',
			type: 'Corporate'
		},
		{
			id: 'org-techstars',
			members: 8,
			membersList: 'jane@techstars.com, john@techstars.com, sarah@techstars.com',
			tokenBalance: 75000,
			tokenName: 'TECH Token',
			proposals: 5,
			activeProposals: 1,
			creationTime: '03/15/2023',
			type: 'Startup'
		},
		{
			id: 'org-community-dao',
			members: 156,
			membersList: 'community-members (156)',
			tokenBalance: 450000,
			tokenName: 'COMM Token',
			proposals: 24,
			activeProposals: 5,
			creationTime: '11/10/2022',
			type: 'DAO'
		},
		{
			id: 'org-greenfuture',
			members: 42,
			membersList: 'environmental-group-members (42)',
			tokenBalance: 210000,
			tokenName: 'GREEN Token',
			proposals: 15,
			activeProposals: 3,
			creationTime: '05/22/2023',
			type: 'Non-profit'
		},
		{
			id: 'org-defi-alliance',
			members: 68,
			membersList: 'defi-partners (68)',
			tokenBalance: 890000,
			tokenName: 'DFI Token',
			proposals: 32,
			activeProposals: 7,
			creationTime: '02/14/2023',
			type: 'DeFi Consortium'
		}
	];

	async function fetchOrganizations() {
		// Using mock data instead of fetching from backend
		console.log('Using mock organization data');
		
		// In a real scenario, you'd fetch from backend:
		/*
		try {
			const organizations = await backend.get_organization_list();
			data = organizations.map(org => ({
				id: org.id,
				members: org.members?.length || 0,
				membersList: org.members?.map(m => m.id).join(', ') || 'No members',
				tokenBalance: org.token?.balances ? Object.values(org.token.balances).reduce((a, b) => a + b, 0) : 0,
				tokenName: org.token?.name || '',
				proposals: org.proposals?.length || 0,
				activeProposals: org.proposals?.filter(p => p.status === 'Submitted').length || 0,
				creationTime: new Date(parseInt(org.timestamp_created.match(/\((\d+)\)/)[1])).toLocaleDateString(),
				type: org.type
			}));
		} catch (error) {
			console.error('Error fetching organizations:', error);
		}
		*/
	}

	onMount(() => {
		fetchOrganizations();
	});
</script>

<Card size="xl" class="max-w-none shadow-md rounded-lg border-0">
	<div class="items-center justify-between lg:flex">
		<div class="mb-4 mt-px lg:mb-0">
			<Heading tag="h3" class="-ml-0.25 mb-2 text-xl font-semibold dark:text-white flex items-center gap-2">
				<svelte:component this={BuildingSolid} class="w-6 h-6" />
				Organizations
			</Heading>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				Manage and monitor your organization network
			</p>
		</div>
		<div class="items-center justify-between gap-3 space-y-4 sm:flex sm:space-y-0">
			<div class="flex items-center">
				<Button color="alternative" class="w-fit whitespace-nowrap px-4 py-2">
					Filter by status
					<svelte:component this={CaretDownSolid} size="lg" />
				</Button>
				<Dropdown class="w-44 space-y-3 p-3 text-sm" placement="bottom-start">
					<li><Checkbox class="accent-primary-600">Completed (56)</Checkbox></li>
					<li><Checkbox checked>Cancelled (56)</Checkbox></li>
					<li><Checkbox class="accent-primary-600">In progress (56)</Checkbox></li>
					<li><Checkbox checked>In review (97)</Checkbox></li>
				</Dropdown>
			</div>
			<div class="flex items-center space-x-4">
				<Input placeholder="From" class="w-full">
					<svelte:component this={CalendarMonthSolid} slot="left" size="md" />
				</Input>
				<Input placeholder="To" class="w-full">
					<svelte:component this={CalendarMonthSolid} slot="left" size="md" />
				</Input>
			</div>
		</div>
	</div>
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
						<div>
							<a href="/organization?id={org.id}" 
							   class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium">
								{org.id}
							</a>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								{org.type}
							</div>
						</div>
					</TableBodyCell>
					<TableBodyCell class="px-4">
						<div>
							<div class="font-medium">{org.members} members</div>
							<div class="text-xs text-gray-500 dark:text-gray-400" title={org.membersList}>
								{org.membersList.length > 30 ? org.membersList.substring(0, 30) + '...' : org.membersList}
							</div>
						</div>
					</TableBodyCell>
					<TableBodyCell class="px-4">
						<div>
							<div class="font-medium">{org.tokenBalance} tokens</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								{org.tokenName}
							</div>
						</div>
					</TableBodyCell>
					<TableBodyCell class="px-4">
						<div>
							<div class="font-medium">{org.proposals} total</div>
							{#if org.activeProposals > 0}
								<div class="text-xs bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded-full inline-block">
									{org.activeProposals} active
								</div>
							{/if}
						</div>
					</TableBodyCell>
					<TableBodyCell class="px-4">
						<div class="text-sm text-gray-600 dark:text-gray-300">
							{org.creationTime}
						</div>
					</TableBodyCell>
					<TableBodyCell class="px-4">
						<Button size="xs" color="blue" href="/organization?id={org.id}" class="rounded-lg font-medium">
							View Details
							<svelte:component this={CaretRightSolid} class="w-4 h-4 ml-1" />
						</Button>
					</TableBodyCell>
				</TableBodyRow>
			{/each}
		</TableBody>
	</Table>
	<div class="-mb-1 flex items-center justify-between pt-3 sm:pt-6">
		<LastRange />
		<a
			href="#top"
			class="text-primary-700 dark:text-primary-500 inline-flex items-center rounded-lg p-1 text-xs font-medium uppercase hover:bg-gray-100 sm:text-sm dark:hover:bg-gray-700"
		>
			Clusters report <svelte:component this={CaretRightSolid} size="lg" />
		</a>
	</div>
</Card>
