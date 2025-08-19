<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Tabs, TabItem, Spinner, Button, Alert } from 'flowbite-svelte';
	import { LockSolid, ClipboardListSolid, CheckOutline, ClockSolid } from 'flowbite-svelte-icons';
	import { principal } from '$lib/stores/auth';
	import { backend } from '$lib/canisters';
	import LitigationsList from './LitigationsList.svelte';
	import CreateLitigationForm from './CreateLitigationForm.svelte';
	import { _ } from 'svelte-i18n';
	import SafeText from '$lib/components/SafeText.svelte';
	
	// Note: Using SafeText component instead of safeTranslate for elegant spinner
	
	let loading = true;
	let error = '';
	let activeTab = 0;
	let litigations = [];
	let totalCount = 0;
	let userProfile = 'member';
	let userPrincipalId = $principal || "";
	
	async function loadLitigations() {
		loading = true;
		error = '';
		
		try {
			const callParams = {
				user_principal: userPrincipalId,
				user_profile: userProfile
			};
			
			console.log('Calling get_litigations with parameters:', callParams);
			
			const response = await backend.extension_sync_call({
				extension_name: "justice_litigation",
				function_name: "get_litigations", 
				args: JSON.stringify(callParams)
			});
			
			console.log('Litigations response:', response);
			
			if (response.success) {
				const data = JSON.parse(response.response);
				console.log('Parsed litigations data:', data);
				
				if (data.success) {
					litigations = data.data.litigations || [];
					totalCount = data.data.total_count || 0;
					userProfile = data.data.user_profile || 'member';
					console.log('Litigations loaded:', litigations);
				} else {
					error = `Failed to load litigations: ${data.error}`;
					console.error(error);
				}
			} else {
				error = `Failed to load litigations: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error loading litigations:', err);
			error = `Error loading litigations: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	async function handleLitigationCreated() {
		await loadLitigations();
		activeTab = 0;
	}
	
	async function handleVerdictExecuted() {
		await loadLitigations();
	}
	
	onMount(async () => {
		if (userPrincipalId) {
			await loadLitigations();
		} else {
			loading = false;
			error = 'User not authenticated';
		}
	});
</script>

<div class="w-full max-w-none px-4">
	<div class="flex items-center mb-4">
		<LockSolid class="mr-2 h-8 w-8 text-primary-600" />
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">
		<SafeText key="extensions.justice_litigation.title" spinnerSize="sm" />
	</h2>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="relative">
				<svg class="animate-spin h-16 w-16" viewBox="0 0 24 24">
					<defs>
						<linearGradient id="spinner-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
							<stop offset="0%" stop-color="#60A5FA" />
							<stop offset="100%" stop-color="#3B82F6" />
						</linearGradient>
					</defs>
					<circle 
						class="opacity-25" 
						cx="12" cy="12" r="10" 
						stroke="currentColor" 
						stroke-width="4"
						fill="none"
						stroke-dasharray="32"
						stroke-dashoffset="12"
						stroke-linecap="round"
					></circle>
					<path
						class="opacity-75"
						fill="url(#spinner-gradient)"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
				<p class="mt-4 text-center text-gray-600 dark:text-gray-400 animate-pulse">{$_('extensions.justice_litigation.loading_data')}</p>
			</div>
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">{$_('common.error')}:</span> {error}
		</Alert>
	{:else}
		<div class="mb-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<div class="text-sm text-gray-600 dark:text-gray-400">
						{$_('extensions.justice_litigation.profile')}: <span class="font-semibold capitalize">{userProfile}</span>
					</div>
					<div class="text-sm text-gray-600 dark:text-gray-400">
						{$_('extensions.justice_litigation.total_cases')}: <span class="font-semibold">{totalCount}</span>
					</div>
				</div>
				<Button color="alternative" size="sm" on:click={loadLitigations} disabled={loading}>
					{#if loading}
						<div class="flex items-center">
							<span class="animate-spin inline-block w-4 h-4 border-2 border-t-transparent border-primary-500 rounded-full mr-2"></span>
							<span>{$_('common.loading')}</span>
						</div>
					{:else}
						{$_('extensions.justice_litigation.refresh_data')}
					{/if}
				</Button>
			</div>
		</div>

		<Tabs style="underline" contentClass="p-4 mt-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
			<TabItem open={activeTab === 0} on:click={() => activeTab = 0}>
				<span slot="title" class="flex items-center gap-2">
					<ClipboardListSolid class="w-5 h-5" />
					{userProfile === 'admin' ? $_('extensions.justice_litigation.all_litigations') : $_('extensions.justice_litigation.my_litigations')}
				</span>
				<LitigationsList 
					{litigations} 
					{userProfile} 
					{userPrincipalId}
					on:verdictExecuted={handleVerdictExecuted}
				/>
			</TabItem>
			
			<TabItem open={activeTab === 1} on:click={() => activeTab = 1}>
				<span slot="title" class="flex items-center gap-2">
					<CheckOutline class="w-5 h-5" />
					{$_('extensions.justice_litigation.create_litigation')}
				</span>
				<CreateLitigationForm 
					{userPrincipalId}
					on:litigationCreated={handleLitigationCreated}
				/>
			</TabItem>
			
			<TabItem open={activeTab === 2} on:click={() => activeTab = 2}>
				<span slot="title" class="flex items-center gap-2">
					<ClockSolid class="w-5 h-5" />
					{$_('extensions.justice_litigation.statistics')}
				</span>
				<div class="space-y-6">
					<div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
						<div class="bg-white dark:bg-gray-700 p-4 rounded-lg shadow">
							<h3 class="text-lg font-semibold mb-2">{$_('extensions.justice_litigation.total_cases')}</h3>
							<p class="text-2xl font-bold text-primary-600">{totalCount}</p>
						</div>
						
						<div class="bg-white dark:bg-gray-700 p-4 rounded-lg shadow">
							<h3 class="text-lg font-semibold mb-2">{$_('extensions.justice_litigation.pending')}</h3>
							<p class="text-2xl font-bold text-yellow-600">
								{litigations.filter(lit => lit.status === 'pending').length}
							</p>
						</div>
						
						<div class="bg-white dark:bg-gray-700 p-4 rounded-lg shadow">
							<h3 class="text-lg font-semibold mb-2">{$_('extensions.justice_litigation.resolved')}</h3>
							<p class="text-2xl font-bold text-green-600">
								{litigations.filter(lit => lit.status === 'resolved').length}
							</p>
						</div>
					</div>
				</div>
			</TabItem>
		</Tabs>
	{/if}
</div>
