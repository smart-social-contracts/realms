<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Card, Badge, Button, Spinner, Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell } from 'flowbite-svelte';
	import { EyeSolid, ClockSolid, UserSolid } from 'flowbite-svelte-icons';
	import { _ } from 'svelte-i18n';
	import VotingCard from './VotingCard.svelte';
	import ProposalDetail from './ProposalDetail.svelte';
	
	export let proposals = [];
	export let loading = false;
	
	const dispatch = createEventDispatcher();
	
	let selectedProposal = null;
	let showDetail = false;
	
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
		selectedProposal = proposal;
		showDetail = true;
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
	{#if showDetail && selectedProposal}
		<ProposalDetail 
			proposal={selectedProposal}
			on:close={() => { showDetail = false; selectedProposal = null; }}
			on:vote={handleVote}
		/>
	{:else}
		<div class="space-y-4">
			{#each proposals as proposal}
				<Card class="hover:shadow-lg transition-shadow">
					<div class="flex justify-between items-start">
						<div class="flex-1">
							<div class="flex items-center gap-3 mb-2">
								<h3 class="text-lg font-semibold text-gray-900">
									{proposal.title}
								</h3>
								<Badge color={getStatusColor(proposal.status)}>
									{$_(`extensions.voting.status.${proposal.status}`)}
								</Badge>
							</div>
							
							<p class="text-gray-600 mb-3 line-clamp-2">
								{proposal.description}
							</p>
							
							<div class="flex items-center gap-4 text-sm text-gray-500">
								<div class="flex items-center gap-1">
									<UserSolid class="w-4 h-4" />
									<span>{proposal.proposer}</span>
								</div>
								<div class="flex items-center gap-1">
									<ClockSolid class="w-4 h-4" />
									<span>{formatDate(proposal.created_at)}</span>
								</div>
								{#if proposal.voting_deadline}
									<div class="flex items-center gap-1">
										<ClockSolid class="w-4 h-4" />
										<span>{$_('extensions.voting.deadline')}: {formatDate(proposal.voting_deadline)}</span>
									</div>
								{/if}
							</div>
						</div>
						
						<div class="flex flex-col items-end gap-2 ml-4">
							<Button 
								size="sm" 
								color="light"
								on:click={() => handleViewDetails(proposal)}
							>
								<EyeSolid class="w-4 h-4 mr-1" />
								{$_('extensions.voting.view_details')}
							</Button>
							
							{#if proposal.status === 'voting'}
								<div class="text-right">
									<VotingCard 
										{proposal}
										compact={true}
										on:vote={handleVote}
									/>
								</div>
							{/if}
						</div>
					</div>
					
					{#if proposal.status === 'voting'}
						<div class="mt-4 pt-4 border-t border-gray-200">
							<div class="flex justify-between items-center text-sm">
								<div class="flex gap-4">
									<span class="text-green-600">
										{$_('extensions.voting.votes.yes')}: {proposal.votes.yes}
									</span>
									<span class="text-red-600">
										{$_('extensions.voting.votes.no')}: {proposal.votes.no}
									</span>
									<span class="text-gray-600">
										{$_('extensions.voting.votes.abstain')}: {proposal.votes.abstain}
									</span>
								</div>
								<span class="text-gray-500">
									{$_('extensions.voting.total_votes')}: {proposal.total_voters}
								</span>
							</div>
							
							<div class="mt-2">
								<div class="w-full bg-gray-200 rounded-full h-2">
									<div 
										class="bg-green-600 h-2 rounded-full" 
										style="width: {(proposal.votes.yes / Math.max(proposal.total_voters, 1)) * 100}%"
									></div>
								</div>
								<p class="text-xs text-gray-500 mt-1">
									{$_('extensions.voting.threshold_required')}: {(proposal.required_threshold * 100).toFixed(0)}%
								</p>
							</div>
						</div>
					{/if}
				</Card>
			{/each}
		</div>
	{/if}
{/if}
