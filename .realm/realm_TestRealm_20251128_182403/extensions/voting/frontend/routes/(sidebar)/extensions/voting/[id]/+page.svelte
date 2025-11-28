<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { backend } from '$lib/canisters';
	import { _ } from 'svelte-i18n';
	import { Alert, Button, Spinner } from 'flowbite-svelte';
	import { ArrowLeftOutline } from 'flowbite-svelte-icons';
	import ProposalDetail from '$lib/extensions/voting/ProposalDetail.svelte';
	
	let loading = true;
	let error = '';
	let proposal = null;
	
	$: proposalId = $page.params.id;
	
	onMount(async () => {
		await loadProposal();
	});
	
	async function loadProposal() {
		try {
			loading = true;
			error = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "voting",
				function_name: "get_proposal",
				args: JSON.stringify({ proposal_id: proposalId })
			});
			
			console.log('Proposal response:', response);
			
			if (response.success) {
				let data;
				if (typeof response.response === 'string') {
					data = JSON.parse(response.response);
				} else {
					data = response.response;
				}
				
				if (data.success) {
					proposal = data.data;
					console.log('Successfully loaded proposal:', proposal);
				} else {
					error = data.error || 'Failed to load proposal';
				}
			} else {
				error = 'Failed to communicate with backend';
			}
		} catch (e) {
			console.error('Error loading proposal:', e);
			error = 'Error loading proposal: ' + e.message;
		} finally {
			loading = false;
		}
	}
	
	function handleClose() {
		goto('/extensions/voting');
	}
	
	function handleVote() {
		// Reload the proposal after voting
		loadProposal();
	}
</script>

<svelte:head>
	<title>{proposal?.title || $_('extensions.voting.proposal_details')} - {$_('extensions.voting.title')}</title>
</svelte:head>

<div class="w-full px-6 max-w-none">
	<div class="mb-6">
		<Button color="light" size="sm" on:click={handleClose}>
			<ArrowLeftOutline class="w-4 h-4 mr-2" />
			{$_('extensions.voting.back_to_list')}
		</Button>
	</div>
	
	{#if error}
		<Alert color="red" class="mb-6">
			<span class="font-medium">{$_('extensions.voting.error')}</span>
			{error}
		</Alert>
	{/if}
	
	{#if loading}
		<div class="flex justify-center items-center py-12">
			<Spinner size="8" />
			<span class="ml-3">{$_('extensions.voting.loading_proposal')}</span>
		</div>
	{:else if proposal}
		<ProposalDetail 
			{proposal}
			on:close={handleClose}
			on:vote={handleVote}
		/>
	{:else}
		<Alert color="yellow">
			{$_('extensions.voting.proposal_not_found')}
		</Alert>
	{/if}
</div>
