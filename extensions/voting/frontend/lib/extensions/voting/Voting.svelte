<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Tabs, TabItem, Button, Alert } from 'flowbite-svelte';
	import { PlusOutline, CheckCircleOutline, ListOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { principal } from '$lib/stores/auth';
	import { _ } from 'svelte-i18n';
	import ProposalList from './ProposalList.svelte';
	import ProposalForm from './ProposalForm.svelte';
	
	// Component state
	let loading = true;
	let error = '';
	let proposals = [];
	let activeTab = 'list';
	let showForm = false;
	
	// Load proposals on component mount
	onMount(async () => {
		await loadProposals();
	});
	
	async function loadProposals() {
		try {
			loading = true;
			error = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "voting",
				function_name: "get_proposals",
				args: JSON.stringify({})
			});
			
			console.log('Proposals response:', response);
			console.log('Step 1: About to check response.success');
			
			if (response.success && response.response) {
				console.log('Step 2: Response success check passed');
				// The backend returns response.response as an already parsed object
				const backendData = response.response;
				console.log('Step 3: Backend data extracted:', backendData);
				
				// Check if backendData.success exists and what type it is
				console.log('Step 4: Backend success value:', backendData.success, 'type:', typeof backendData.success);
				
				// Simple success check first
				if (backendData.success && backendData.data && backendData.data.proposals) {
					console.log('Step 5: Simple success check passed');
					proposals = backendData.data.proposals;
					console.log('Step 6: Successfully loaded proposals:', proposals.length);
				} else {
					console.log('Step 5: Simple success check failed');
					console.log('  - backendData.success:', backendData.success);
					console.log('  - backendData.data:', backendData.data);
					console.log('  - backendData.data.proposals:', backendData.data?.proposals);
					error = backendData.error || 'No proposals found';
				}
			} else {
				console.log('Step 2: Response success check failed');
				console.log('  - response.success:', response.success);
				console.log('  - response.response:', response.response);
				error = 'Failed to communicate with backend';
			}
		} catch (e) {
			console.error('Error loading proposals:', e);
			error = 'Error loading proposals: ' + e.message;
		} finally {
			loading = false;
		}
	}
	
	function handleProposalSubmitted() {
		showForm = false;
		activeTab = 'list';
		loadProposals();
	}
	
	function handleVoteCast() {
		loadProposals();
	}
</script>

<svelte:head>
	<title>{$_('extensions.voting.title')}</title>
</svelte:head>

<div class="container mx-auto p-6 max-w-6xl">
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">
			{$_('extensions.voting.title')}
		</h1>
		<p class="text-gray-600">
			{$_('extensions.voting.description')}
		</p>
	</div>

	{#if error}
		<Alert color="red" class="mb-6">
			<span class="font-medium">{$_('extensions.voting.error')}</span>
			{error}
		</Alert>
	{/if}

	<Card class="mb-6">
		<div class="flex justify-between items-center mb-4">
			<div class="flex space-x-4">
				<Button 
					color={activeTab === 'list' ? 'blue' : 'light'}
					on:click={() => { activeTab = 'list'; showForm = false; }}
				>
					<ListOutline class="w-4 h-4 mr-2" />
					{$_('extensions.voting.tabs.proposals')}
				</Button>
				<Button 
					color={showForm ? 'blue' : 'light'}
					on:click={() => { showForm = true; activeTab = 'form'; }}
				>
					<PlusOutline class="w-4 h-4 mr-2" />
					{$_('extensions.voting.tabs.submit')}
				</Button>
			</div>
			
			<Button 
				color="alternative" 
				size="sm"
				on:click={loadProposals}
				disabled={loading}
			>
				{#if loading}
					{$_('extensions.voting.loading')}
				{:else}
					{$_('extensions.voting.refresh')}
				{/if}
			</Button>
		</div>

		{#if showForm}
			<ProposalForm 
				on:submitted={handleProposalSubmitted}
				on:cancelled={() => { showForm = false; activeTab = 'list'; }}
			/>
		{:else}
			<ProposalList 
				{proposals} 
				{loading}
				on:vote={handleVoteCast}
			/>
		{/if}
	</Card>
</div>
