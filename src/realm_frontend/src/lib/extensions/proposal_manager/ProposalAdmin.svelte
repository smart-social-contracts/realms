<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell, Button, Badge, Spinner, Alert, Modal, Label, Input, Textarea, Select } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	
	export let userPrincipal: string;
	
	const dispatch = createEventDispatcher();
	
	let proposals = [];
	let loading = true;
	let error = '';
	let pagination = { page_num: 0, page_size: 10, total_items: 0, total_pages: 0 };
	
	let showEditModal = false;
	let editingProposal = null;
	let editFormData = {
		title: '',
		description: '',
		status: '',
		voting_deadline: ''
	};
	let editLoading = false;
	let editError = '';
	
	let showDeleteModal = false;
	let deletingProposal = null;
	let deleteLoading = false;
	let deleteError = '';
	
	const statusOptions = [
		{ value: 'pending_review', name: 'Pending Review' },
		{ value: 'voting', name: 'Voting' },
		{ value: 'approved', name: 'Approved' },
		{ value: 'rejected', name: 'Rejected' },
		{ value: 'cancelled', name: 'Cancelled' },
		{ value: 'paused', name: 'Paused' }
	];
	
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
	
	function openEditModal(proposal) {
		const metadata = parseMetadata(proposal.metadata);
		editingProposal = proposal;
		editFormData = {
			title: metadata.title || '',
			description: metadata.description || '',
			status: metadata.status || 'pending_review',
			voting_deadline: metadata.voting_deadline || ''
		};
		showEditModal = true;
		editError = '';
	}
	
	async function updateProposal() {
		try {
			editLoading = true;
			editError = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "proposal_manager",
				function_name: "update_proposal",
				args: JSON.stringify({
					proposal_id: editingProposal.id,
					...editFormData,
					updated_by: userPrincipal
				})
			});
			
			if (response.success) {
				const result = JSON.parse(response.response);
				if (result.success) {
					showEditModal = false;
					editingProposal = null;
					await loadProposals();
					dispatch('proposalUpdated', { proposalId: editingProposal.id });
				} else {
					editError = result.error || 'Failed to update proposal';
				}
			} else {
				editError = response.response || 'Failed to call extension';
			}
		} catch (e) {
			console.error('Error updating proposal:', e);
			editError = 'Failed to update proposal';
		} finally {
			editLoading = false;
		}
	}
	
	function openDeleteModal(proposal) {
		deletingProposal = proposal;
		showDeleteModal = true;
		deleteError = '';
	}
	
	async function deleteProposal() {
		try {
			deleteLoading = true;
			deleteError = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "proposal_manager",
				function_name: "delete_proposal",
				args: JSON.stringify({
					proposal_id: deletingProposal.id,
					cancelled_by: userPrincipal
				})
			});
			
			if (response.success) {
				const result = JSON.parse(response.response);
				if (result.success) {
					showDeleteModal = false;
					deletingProposal = null;
					await loadProposals();
				} else {
					deleteError = result.error || 'Failed to cancel proposal';
				}
			} else {
				deleteError = response.response || 'Failed to call extension';
			}
		} catch (e) {
			console.error('Error cancelling proposal:', e);
			deleteError = 'Failed to cancel proposal';
		} finally {
			deleteLoading = false;
		}
	}
	
	async function toggleProposalStatus(proposal, newStatus) {
		try {
			const response = await backend.extension_sync_call({
				extension_name: "proposal_manager",
				function_name: "update_proposal",
				args: JSON.stringify({
					proposal_id: proposal.id,
					status: newStatus,
					updated_by: userPrincipal
				})
			});
			
			if (response.success) {
				const result = JSON.parse(response.response);
				if (result.success) {
					await loadProposals();
				} else {
					error = result.error || 'Failed to update proposal status';
				}
			} else {
				error = response.response || 'Failed to call extension';
			}
		} catch (e) {
			console.error('Error updating proposal status:', e);
			error = 'Failed to update proposal status';
		}
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
		return `${total} votes`;
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

<div class="proposal-admin">
	<div class="flex justify-between items-center mb-4">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Admin Panel</h3>
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
			No proposals found to manage.
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
								<div class="flex gap-1">
									<Button size="xs" color="primary" on:click={() => openEditModal(proposal)}>
										Edit
									</Button>
									
									{#if metadata.status === 'paused'}
										<Button size="xs" color="green" on:click={() => toggleProposalStatus(proposal, 'voting')}>
											Resume
										</Button>
									{:else if metadata.status === 'voting'}
										<Button size="xs" color="yellow" on:click={() => toggleProposalStatus(proposal, 'paused')}>
											Pause
										</Button>
									{/if}
									
									{#if metadata.status !== 'cancelled'}
										<Button size="xs" color="red" on:click={() => openDeleteModal(proposal)}>
											Cancel
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

<Modal bind:open={showEditModal} title="Edit Proposal" size="lg">
	{#if editingProposal}
		<div class="space-y-4">
			{#if editError}
				<Alert color="red">
					<span class="font-medium">Error:</span> {editError}
				</Alert>
			{/if}
			
			<div>
				<Label for="edit-title" class="mb-2">Title</Label>
				<Input
					id="edit-title"
					bind:value={editFormData.title}
					disabled={editLoading}
					required
				/>
			</div>
			
			<div>
				<Label for="edit-description" class="mb-2">Description</Label>
				<Textarea
					id="edit-description"
					bind:value={editFormData.description}
					rows="4"
					disabled={editLoading}
					required
				/>
			</div>
			
			<div>
				<Label for="edit-status" class="mb-2">Status</Label>
				<Select
					id="edit-status"
					bind:value={editFormData.status}
					disabled={editLoading}
					items={statusOptions}
				/>
			</div>
			
			<div>
				<Label for="edit-deadline" class="mb-2">Voting Deadline</Label>
				<Input
					id="edit-deadline"
					bind:value={editFormData.voting_deadline}
					type="datetime-local"
					disabled={editLoading}
				/>
			</div>
		</div>
	{/if}
	
	<svelte:fragment slot="footer">
		<Button color="primary" disabled={editLoading} on:click={updateProposal}>
			{#if editLoading}
				<Spinner class="mr-2" size="4" />
				Updating...
			{:else}
				Update Proposal
			{/if}
		</Button>
		<Button color="alternative" disabled={editLoading} on:click={() => showEditModal = false}>
			Cancel
		</Button>
	</svelte:fragment>
</Modal>

<Modal bind:open={showDeleteModal} title="Cancel Proposal">
	{#if deletingProposal}
		{@const metadata = parseMetadata(deletingProposal.metadata)}
		<div class="space-y-4">
			<p class="text-gray-600 dark:text-gray-400">
				Are you sure you want to cancel the proposal "<strong>{metadata.title}</strong>"?
			</p>
			<p class="text-sm text-gray-500 dark:text-gray-500">
				This action will mark the proposal as cancelled and cannot be undone.
			</p>
			
			{#if deleteError}
				<Alert color="red">
					<span class="font-medium">Error:</span> {deleteError}
				</Alert>
			{/if}
		</div>
	{/if}
	
	<svelte:fragment slot="footer">
		<Button color="red" disabled={deleteLoading} on:click={deleteProposal}>
			{#if deleteLoading}
				<Spinner class="mr-2" size="4" />
				Cancelling...
			{:else}
				Cancel Proposal
			{/if}
		</Button>
		<Button color="alternative" disabled={deleteLoading} on:click={() => showDeleteModal = false}>
			Keep Proposal
		</Button>
	</svelte:fragment>
</Modal>
