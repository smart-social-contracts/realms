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
		console.log('onMount called - about to load proposals');
		try {
			await loadProposals();
			console.log('loadProposals completed');
		} catch (error) {
			console.error('Error in onMount:', error);
		}
	});
	
	async function loadProposals() {
		console.log('loadProposals function started');
		try {
			loading = true;
			error = '';
			
			console.log('About to call backend.extension_sync_call');
			const response = await backend.extension_sync_call({
				extension_name: "voting",
				function_name: "get_proposals",
				args: JSON.stringify({})
			});
			
			console.log('Proposals response:', response);
			console.log('Response type:', typeof response.response);
			console.log('Response content:', response.response);
			
			if (response.success) {
				try {
					// Check if response.response is already an object or needs parsing
					let data;
					if (typeof response.response === 'string') {
						console.log('Parsing JSON string...');
						data = JSON.parse(response.response);
					} else {
						console.log('Using response as object...');
						data = response.response;
					}
					console.log('Parsed data:', data);
					
					if (data.success) {
						proposals = data.data.proposals;
						console.log('Successfully loaded proposals:', proposals.length);
					} else {
						error = data.error || 'Failed to load proposals';
						console.log('Backend error:', error);
					}
				} catch (parseError) {
					console.error('JSON parse error:', parseError);
					console.log('Raw response that failed to parse:', response.response);
					error = 'Failed to parse backend response';
				}
			} else {
				error = 'Failed to communicate with backend';
				console.log('Communication error:', error);
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

<div class="w-full px-6 max-w-none">
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

	<Card class="mb-6 w-full max-w-none">
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
