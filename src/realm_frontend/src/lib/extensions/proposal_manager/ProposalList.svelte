<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell, Button, Badge, Spinner, Alert, Modal } from 'flowbite-svelte';
	import { ThumbsUpSolid, ThumbsDownSolid, EyeSolid } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	
	export let userPrincipal: string;
	export let isAdmin: boolean = false;
	
	const dispatch = createEventDispatcher();
	
	let proposals = [];
	let loading = true;
	let error = '';
	let pagination = { page_num: 0, page_size: 10, total_items: 0, total_pages: 0 };
	let selectedProposal = null;
	let showVoteModal = false;
	let votingProposal = null;
	let voteLoading = false;
	let voteError = '';
	
	onMount(() => {
		loadProposals();
	});
	
	async function loadProposals() {
		try {
			loading = true;
			error = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "proposal_manager",
				function_name: "list_proposals",
				args: JSON.stringify({
					page_num: pagination.page_num,
					page_size: pagination.page_size
				})
			});
			
			if (response.success) {
				const result = JSON.parse(response.response);
				if (result.success) {
					proposals = result.proposals || [];
					pagination = result.pagination || pagination;
				} else {
					error = result.error || 'Failed to load proposals';
				}
			} else {
				error = response.response || 'Failed to call extension';
			}
		} catch (e) {
			console.error('Error loading proposals:', e);
			error = 'Failed to load proposals';
		} finally {
			loading = false;
		}
	}
	
	async function castVote(proposalId: string, voteValue: string) {
		try {
			voteLoading = true;
			voteError = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "proposal_manager",
				function_name: "vote_on_proposal",
				args: JSON.stringify({
					proposal_id: proposalId,
					vote: voteValue,
					voter_id: userPrincipal
				})
			});
			
			if (response.success) {
				const result = JSON.parse(response.response);
				if (result.success) {
					showVoteModal = false;
					votingProposal = null;
					await loadProposals();
					dispatch('votecast', { proposalId, voteValue });
				} else {
					voteError = result.error || 'Failed to cast vote';
				}
			} else {
				voteError = response.response || 'Failed to call extension';
			}
		} catch (e) {
			console.error('Error casting vote:', e);
			voteError = 'Failed to cast vote';
		} finally {
			voteLoading = false;
		}
	}
	
	function openVoteModal(proposal) {
		votingProposal = proposal;
		showVoteModal = true;
		voteError = '';
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
	
	function parseMetadata(metadataStr: string) {
		try {
			return JSON.parse(metadataStr || '{}');
		} catch {
			return {};
		}
	}
	
	function formatVoteCount(counts: any) {
		if (!counts) return 'No votes';
		const total = (counts.yes || 0) + (counts.no || 0) + (counts.abstain || 0) + (counts.null || 0);
		return `${total} votes (${counts.yes || 0}Y, ${counts.no || 0}N, ${counts.abstain || 0}A, ${counts.null || 0}X)`;
	}
	
	async function nextPage() {
		if (pagination.page_num < pagination.total_pages - 1) {
			pagination.page_num++;
			await loadProposals();
		}
	}
	
	async function prevPage() {
		if (pagination.page_num > 0) {
			pagination.page_num--;
			await loadProposals();
		}
	}
</script>

<div class="proposal-list">
	<div class="flex justify-between items-center mb-4">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Proposals</h3>
		<Button size="sm" on:click={loadProposals} disabled={loading}>
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
	{:else if proposals.length === 0}
		<div class="text-center p-8 text-gray-500 dark:text-gray-400">
			No proposals found. Be the first to submit one!
		</div>
	{:else}
		<div class="overflow-x-auto">
			<Table hoverable={true}>
				<TableHead>
					<TableHeadCell>Title</TableHeadCell>
					<TableHeadCell>Author</TableHeadCell>
					<TableHeadCell>Status</TableHeadCell>
					<TableHeadCell>Votes</TableHeadCell>
					<TableHeadCell>Actions</TableHeadCell>
				</TableHead>
				<TableBody>
					{#each proposals as proposal}
						{@const metadata = parseMetadata(proposal.metadata)}
						{@const statusInfo = getStatusBadge(metadata.status)}
						<TableBodyRow>
							<TableBodyCell>
								<div class="font-medium text-gray-900 dark:text-white">
									{metadata.title || 'Untitled Proposal'}
								</div>
								<div class="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
									{metadata.description || 'No description'}
								</div>
							</TableBodyCell>
							<TableBodyCell>
								<div class="text-sm">
									{metadata.author || 'Unknown'}
								</div>
							</TableBodyCell>
							<TableBodyCell>
								<Badge color={statusInfo.color}>{statusInfo.text}</Badge>
							</TableBodyCell>
							<TableBodyCell>
								<div class="text-sm">
									{formatVoteCount(metadata.vote_counts)}
								</div>
							</TableBodyCell>
							<TableBodyCell>
								<div class="flex gap-2">
									<Button size="xs" color="light" on:click={() => selectedProposal = proposal}>
										<EyeSolid class="w-3 h-3 mr-1" />
										View
									</Button>
									{#if metadata.status === 'voting'}
										<Button size="xs" color="primary" on:click={() => openVoteModal(proposal)}>
											Vote
										</Button>
									{/if}
								</div>
							</TableBodyCell>
						</TableBodyRow>
					{/each}
				</TableBody>
			</Table>
		</div>
		
		<div class="flex justify-between items-center mt-4">
			<div class="text-sm text-gray-500 dark:text-gray-400">
				Showing {pagination.page_num * pagination.page_size + 1} to {Math.min((pagination.page_num + 1) * pagination.page_size, pagination.total_items)} of {pagination.total_items} proposals
			</div>
			<div class="flex gap-2">
				<Button size="sm" disabled={pagination.page_num === 0} on:click={prevPage}>
					Previous
				</Button>
				<Button size="sm" disabled={pagination.page_num >= pagination.total_pages - 1} on:click={nextPage}>
					Next
				</Button>
			</div>
		</div>
	{/if}
</div>

<Modal bind:open={showVoteModal} title="Cast Your Vote" autoclose={false}>
	{#if votingProposal}
		{@const metadata = parseMetadata(votingProposal.metadata)}
		<div class="space-y-4">
			<div>
				<h4 class="font-semibold text-gray-900 dark:text-white">{metadata.title}</h4>
				<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{metadata.description}</p>
			</div>
			
			{#if voteError}
				<Alert color="red">
					<span class="font-medium">Error:</span> {voteError}
				</Alert>
			{/if}
			
			<div class="grid grid-cols-2 gap-3">
				<Button color="green" disabled={voteLoading} on:click={() => castVote(votingProposal.id, 'yes')}>
					<ThumbsUpSolid class="w-4 h-4 mr-2" />
					Yes
				</Button>
				<Button color="red" disabled={voteLoading} on:click={() => castVote(votingProposal.id, 'no')}>
					<ThumbsDownSolid class="w-4 h-4 mr-2" />
					No
				</Button>
				<Button color="yellow" disabled={voteLoading} on:click={() => castVote(votingProposal.id, 'abstain')}>
					Abstain
				</Button>
				<Button color="gray" disabled={voteLoading} on:click={() => castVote(votingProposal.id, 'null')}>
					Null Vote
				</Button>
			</div>
			
			{#if voteLoading}
				<div class="flex justify-center">
					<Spinner size="4" />
				</div>
			{/if}
		</div>
	{/if}
	
	<svelte:fragment slot="footer">
		<Button color="alternative" on:click={() => showVoteModal = false}>Cancel</Button>
	</svelte:fragment>
</Modal>

<Modal bind:open={selectedProposal} title="Proposal Details" size="lg">
	{#if selectedProposal}
		{@const metadata = parseMetadata(selectedProposal.metadata)}
		{@const statusInfo = getStatusBadge(metadata.status)}
		<div class="space-y-4">
			<div>
				<h4 class="text-lg font-semibold text-gray-900 dark:text-white">{metadata.title}</h4>
				<Badge color={statusInfo.color} class="mt-2">{statusInfo.text}</Badge>
			</div>
			
			<div>
				<h5 class="font-medium text-gray-900 dark:text-white">Description</h5>
				<p class="text-gray-600 dark:text-gray-400 mt-1">{metadata.description}</p>
			</div>
			
			<div class="grid grid-cols-2 gap-4">
				<div>
					<h5 class="font-medium text-gray-900 dark:text-white">Author</h5>
					<p class="text-gray-600 dark:text-gray-400">{metadata.author}</p>
				</div>
				{#if metadata.forum_url}
					<div>
						<h5 class="font-medium text-gray-900 dark:text-white">Forum</h5>
						<a href={metadata.forum_url} target="_blank" class="text-blue-600 hover:underline">
							Discussion Link
						</a>
					</div>
				{/if}
			</div>
			
			{#if metadata.vote_counts}
				<div>
					<h5 class="font-medium text-gray-900 dark:text-white">Vote Results</h5>
					<div class="grid grid-cols-4 gap-2 mt-2">
						<div class="text-center p-2 bg-green-100 dark:bg-green-900 rounded">
							<div class="font-semibold text-green-800 dark:text-green-200">{metadata.vote_counts.yes || 0}</div>
							<div class="text-xs text-green-600 dark:text-green-400">Yes</div>
						</div>
						<div class="text-center p-2 bg-red-100 dark:bg-red-900 rounded">
							<div class="font-semibold text-red-800 dark:text-red-200">{metadata.vote_counts.no || 0}</div>
							<div class="text-xs text-red-600 dark:text-red-400">No</div>
						</div>
						<div class="text-center p-2 bg-yellow-100 dark:bg-yellow-900 rounded">
							<div class="font-semibold text-yellow-800 dark:text-yellow-200">{metadata.vote_counts.abstain || 0}</div>
							<div class="text-xs text-yellow-600 dark:text-yellow-400">Abstain</div>
						</div>
						<div class="text-center p-2 bg-gray-100 dark:bg-gray-700 rounded">
							<div class="font-semibold text-gray-800 dark:text-gray-200">{metadata.vote_counts.null || 0}</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Null</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	{/if}
	
	<svelte:fragment slot="footer">
		<Button color="alternative" on:click={() => selectedProposal = null}>Close</Button>
	</svelte:fragment>
</Modal>
