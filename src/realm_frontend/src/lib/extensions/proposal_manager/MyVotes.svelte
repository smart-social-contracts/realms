<script lang="ts">
	import { onMount } from 'svelte';
	import { Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell, Badge, Spinner, Alert, Button } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	
	export let userPrincipal: string;
	
	let votes = [];
	let loading = true;
	let error = '';
	
	onMount(() => {
		loadMyVotes();
	});
	
	async function loadMyVotes() {
		try {
			loading = true;
			error = '';
			
			const votesResponse = await backend.get_votes(0, 100);
			
			if (votesResponse.success && votesResponse.data.VotesList) {
				const allVotes = votesResponse.data.VotesList.votes.map(voteStr => {
					try {
						return JSON.parse(voteStr);
					} catch {
						return null;
					}
				}).filter(vote => vote !== null);
				
				const myVotes = [];
				for (const vote of allVotes) {
					try {
						const metadata = JSON.parse(vote.metadata || '{}');
						if (metadata.voter_id === userPrincipal) {
							const proposalResponse = await backend.extension_sync_call({
								extension_name: "proposal_manager",
								function_name: "get_proposal_details",
								args: JSON.stringify({ proposal_id: metadata.proposal_id })
							});
							
							if (proposalResponse.success) {
								const proposalResult = JSON.parse(proposalResponse.response);
								if (proposalResult.success) {
									const proposalMetadata = proposalResult.proposal.parsed_metadata || {};
									myVotes.push({
										vote_id: vote.id,
										proposal_id: metadata.proposal_id,
										proposal_title: proposalMetadata.title || 'Untitled Proposal',
										vote_value: metadata.vote_value,
										created_at: vote.created_at,
										proposal_status: proposalMetadata.status
									});
								}
							}
						}
					} catch (e) {
						console.error('Error processing vote:', e);
					}
				}
				
				votes = myVotes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
			} else {
				error = 'Failed to load votes';
			}
		} catch (e) {
			console.error('Error loading votes:', e);
			error = 'Failed to load your votes';
		} finally {
			loading = false;
		}
	}
	
	function getVoteBadge(voteValue: string) {
		const voteMap = {
			'yes': { color: 'green', text: 'Yes' },
			'no': { color: 'red', text: 'No' },
			'abstain': { color: 'yellow', text: 'Abstain' },
			'null': { color: 'gray', text: 'Null Vote' }
		};
		return voteMap[voteValue] || { color: 'gray', text: voteValue };
	}
	
	function getStatusBadge(status: string) {
		const statusMap = {
			'pending_review': { color: 'yellow', text: 'Pending Review' },
			'voting': { color: 'blue', text: 'Voting' },
			'approved': { color: 'green', text: 'Approved' },
			'rejected': { color: 'red', text: 'Rejected' },
			'cancelled': { color: 'gray', text: 'Cancelled' },
			'paused': { color: 'orange', text: 'Paused' }
		};
		return statusMap[status] || { color: 'gray', text: status };
	}
	
	function formatDate(dateStr: string) {
		try {
			return new Date(dateStr).toLocaleDateString();
		} catch {
			return 'Unknown';
		}
	}
</script>

<div class="my-votes">
	<div class="flex justify-between items-center mb-4">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white">My Votes</h3>
		<Button size="sm" on:click={loadMyVotes} disabled={loading}>
			{loading ? 'Loading...' : 'Refresh'}
		</Button>
	</div>
	
	{#if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">Error:</span> {error}
		</Alert>
	{/if}
	
	{#if loading}
		<div class="flex justify-center items-center p-8">
			<Spinner size="6" />
		</div>
	{:else if votes.length === 0}
		<div class="text-center p-8 text-gray-500 dark:text-gray-400">
			<p>You haven't cast any votes yet.</p>
			<p class="text-sm mt-2">Visit the Proposals tab to participate in voting.</p>
		</div>
	{:else}
		<div class="overflow-x-auto">
			<Table hoverable={true}>
				<TableHead>
					<TableHeadCell>Proposal</TableHeadCell>
					<TableHeadCell>My Vote</TableHeadCell>
					<TableHeadCell>Proposal Status</TableHeadCell>
					<TableHeadCell>Vote Date</TableHeadCell>
				</TableHead>
				<TableBody>
					{#each votes as vote}
						{@const voteBadge = getVoteBadge(vote.vote_value)}
						{@const statusBadge = getStatusBadge(vote.proposal_status)}
						<TableBodyRow>
							<TableBodyCell>
								<div class="font-medium text-gray-900 dark:text-white">
									{vote.proposal_title}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									ID: {vote.proposal_id}
								</div>
							</TableBodyCell>
							<TableBodyCell>
								<Badge color={voteBadge.color}>{voteBadge.text}</Badge>
							</TableBodyCell>
							<TableBodyCell>
								<Badge color={statusBadge.color}>{statusBadge.text}</Badge>
							</TableBodyCell>
							<TableBodyCell>
								<div class="text-sm text-gray-600 dark:text-gray-400">
									{formatDate(vote.created_at)}
								</div>
							</TableBodyCell>
						</TableBodyRow>
					{/each}
				</TableBody>
			</Table>
		</div>
		
		<div class="mt-4 text-sm text-gray-500 dark:text-gray-400">
			Total votes cast: {votes.length}
		</div>
	{/if}
</div>
