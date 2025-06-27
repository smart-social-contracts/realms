<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Tabs, TabItem, Spinner, Alert } from 'flowbite-svelte';
	import { principal } from '$lib/stores/auth';
	import { userProfiles, isAdmin } from '$lib/stores/profiles';
	import { backend } from '$lib/canisters';
	
	import ProposalList from './ProposalList.svelte';
	import ProposalForm from './ProposalForm.svelte';
	import ProposalAdmin from './ProposalAdmin.svelte';
	import MyVotes from './MyVotes.svelte';
	
	let loading = true;
	let error = '';
	let activeTab = 0;
	
	$: userPrincipal = $principal || "";
	$: currentUserProfiles = $userProfiles || [];
	$: isUserAdmin = isAdmin();
	$: isMember = currentUserProfiles.includes('member') || isUserAdmin;
	
	onMount(async () => {
		try {
			loading = false;
		} catch (e) {
			console.error('Error initializing Proposal Manager:', e);
			error = 'Failed to initialize Proposal Manager';
			loading = false;
		}
	});
	
	function handleProposalCreated() {
		activeTab = 0;
	}
	
	function handleProposalUpdated() {
		activeTab = 0;
	}
</script>

<div class="proposal-manager">
	{#if loading}
		<div class="flex justify-center items-center p-8">
			<Spinner size="8" />
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">Error:</span> {error}
		</Alert>
	{:else if !isMember}
		<Alert color="yellow" class="mb-4">
			<span class="font-medium">Access Restricted:</span> You need member or admin privileges to access the Proposal Manager.
		</Alert>
	{:else}
		<Card class="w-full">
			<div class="flex items-center gap-2 mb-4">
				<span class="text-primary-600 font-bold">📋</span>
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Proposal Manager</h2>
			</div>
			
			<Tabs bind:activeTabValue={activeTab} contentClass="p-4 bg-gray-50 rounded-lg dark:bg-gray-800 mt-4">
				<TabItem open title="Proposals">
					<span>📋 Proposals</span>
				</TabItem>
				
				<TabItem title="Submit Proposal">
					<span>➕ Submit Proposal</span>
				</TabItem>
				
				<TabItem title="My Votes">
					<span>📊 My Votes</span>
				</TabItem>
				
				{#if isUserAdmin}
					<TabItem title="Admin Panel">
						<span>⚙️ Admin Panel</span>
					</TabItem>
				{/if}
				
				<div slot="content" class="p-4">
					{#if activeTab === 0}
						<ProposalList {userPrincipal} isAdmin={isUserAdmin} />
					{:else if activeTab === 1}
						<ProposalForm {userPrincipal} on:proposalCreated={handleProposalCreated} />
					{:else if activeTab === 2}
						<MyVotes {userPrincipal} />
					{:else if activeTab === 3 && isUserAdmin}
						<ProposalAdmin {userPrincipal} on:proposalUpdated={handleProposalUpdated} />
					{/if}
				</div>
			</Tabs>
		</Card>
	{/if}
</div>

<style>
	.proposal-manager {
		max-width: 100%;
		margin: 0 auto;
	}
</style>
