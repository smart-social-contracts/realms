<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, Badge, Button, Spinner, Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell } from 'flowbite-svelte';
	import { EyeSolid, ClockSolid, UserSolid } from 'flowbite-svelte-icons';
	import { _ } from 'svelte-i18n';
	import VotingCard from './VotingCard.svelte';
	
	export let proposals = [];
	export let loading = false;
	
	const dispatch = createEventDispatcher();
	
	function getStatusColor(status: string) {
		switch (status) {
			case 'pending_review': return 'yellow';
			case 'pending_vote': return 'blue';
			case 'voting': return 'green';
			case 'accepted': return 'green';
			case 'rejected': return 'red';
			default: return 'gray';
		}
	}
	
	function formatDate(dateString: string) {
		if (!dateString) return 'N/A';
		return new Date(dateString).toLocaleDateString();
	}
	
	function handleViewDetails(proposal) {
		goto(`/extensions/voting/${proposal.id}`);
	}
	
	function handleVote(event) {
		dispatch('vote', event.detail);
	}
</script>

{#if loading}
	<div class="flex justify-center items-center py-8">
		<Spinner size="8" />
		<span class="ml-3">{$_('extensions.voting.loading_proposals')}</span>
	</div>
{:else if proposals.length === 0}
	<div class="text-center py-8">
		<p class="text-gray-500 text-lg">{$_('extensions.voting.no_proposals')}</p>
		<p class="text-gray-400 text-sm mt-2">{$_('extensions.voting.no_proposals_hint')}</p>
	</div>
{:else}
	<!-- Desktop Table View -->
		<div class="hidden lg:block">
			<Table hoverable={true} class="w-full">
				<TableHead>
					<TableHeadCell class="w-1/4">{$_('extensions.voting.table.title')}</TableHeadCell>
					<TableHeadCell class="w-1/6">{$_('extensions.voting.table.status')}</TableHeadCell>
					<TableHeadCell class="w-1/6">{$_('extensions.voting.table.proposer')}</TableHeadCell>
					<TableHeadCell class="w-1/6">{$_('extensions.voting.table.created')}</TableHeadCell>
					<TableHeadCell class="w-1/6">{$_('extensions.voting.table.votes')}</TableHeadCell>
					<TableHeadCell class="w-1/6">{$_('extensions.voting.table.actions')}</TableHeadCell>
				</TableHead>
				<TableBody>
					{#each proposals as proposal}
						<TableBodyRow class="hover:bg-gray-50">
							<TableBodyCell class="font-medium">
								<div>
									<h3 class="text-sm font-semibold text-gray-900 mb-1">
										{proposal.title}
									</h3>
									<p class="text-xs text-gray-600 line-clamp-2">
										{proposal.description}
									</p>
								</div>
							</TableBodyCell>
							<TableBodyCell>
								<Badge color={getStatusColor(proposal.status)} class="text-xs">
									{$_(`extensions.voting.status.${proposal.status}`)}
								</Badge>
							</TableBodyCell>
							<TableBodyCell class="text-sm text-gray-600">
								{proposal.proposer}
							</TableBodyCell>
							<TableBodyCell class="text-sm text-gray-600">
								{formatDate(proposal.created_at)}
							</TableBodyCell>
							<TableBodyCell>
								{#if proposal.status === 'voting'}
									<div class="text-xs space-y-1">
										<div class="flex gap-2">
											<span class="text-green-600">Y: {proposal.votes.yes}</span>
											<span class="text-red-600">N: {proposal.votes.no}</span>
											<span class="text-gray-600">A: {proposal.votes.abstain}</span>
										</div>
										<div class="w-full bg-gray-200 rounded-full h-1">
											<div 
												class="bg-green-600 h-1 rounded-full" 
												style="width: {(proposal.votes.yes / Math.max(proposal.total_voters, 1)) * 100}%"
											></div>
										</div>
									</div>
								{:else}
									<span class="text-xs text-gray-400">-</span>
								{/if}
							</TableBodyCell>
							<TableBodyCell>
								<div class="flex gap-2">
									<Button 
										size="xs" 
										color="light"
										on:click={() => handleViewDetails(proposal)}
									>
										<EyeSolid class="w-3 h-3 mr-1" />
										{$_('extensions.voting.view')}
									</Button>
									{#if proposal.status === 'voting'}
										<VotingCard 
											{proposal}
											compact={true}
											on:vote={handleVote}
										/>
									{/if}
								</div>
							</TableBodyCell>
						</TableBodyRow>
					{/each}
				</TableBody>
			</Table>
		</div>

		<!-- Mobile Card View -->
		<div class="lg:hidden space-y-3">
			{#each proposals as proposal}
				<Card class="hover:shadow-md transition-shadow p-4">
					<div class="space-y-3">
						<div class="flex items-start justify-between">
							<div class="flex-1 min-w-0">
								<h3 class="text-base font-semibold text-gray-900 truncate">
									{proposal.title}
								</h3>
								<Badge color={getStatusColor(proposal.status)} class="text-xs mt-1">
									{$_(`extensions.voting.status.${proposal.status}`)}
								</Badge>
							</div>
							<Button 
								size="xs" 
								color="light"
								on:click={() => handleViewDetails(proposal)}
								class="ml-2"
							>
								<EyeSolid class="w-3 h-3" />
							</Button>
						</div>
						
						<p class="text-sm text-gray-600 line-clamp-2">
							{proposal.description}
						</p>
						
						<div class="flex items-center justify-between text-xs text-gray-500">
							<span>{proposal.proposer}</span>
							<span>{formatDate(proposal.created_at)}</span>
						</div>
						
						{#if proposal.status === 'voting'}
							<div class="pt-2 border-t border-gray-100">
								<div class="flex justify-between items-center mb-2">
									<div class="flex gap-3 text-xs">
										<span class="text-green-600">Y: {proposal.votes.yes}</span>
										<span class="text-red-600">N: {proposal.votes.no}</span>
										<span class="text-gray-600">A: {proposal.votes.abstain}</span>
									</div>
									<VotingCard 
										{proposal}
										compact={true}
										on:vote={handleVote}
									/>
								</div>
								<div class="w-full bg-gray-200 rounded-full h-1.5">
									<div 
										class="bg-green-600 h-1.5 rounded-full" 
										style="width: {(proposal.votes.yes / Math.max(proposal.total_voters, 1)) * 100}%"
									></div>
								</div>
							</div>
						{/if}
					</div>
				</Card>
			{/each}
		</div>
{/if}
