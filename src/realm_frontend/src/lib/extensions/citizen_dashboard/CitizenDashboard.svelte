<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Spinner, Alert, Tabs, TabItem } from 'flowbite-svelte';
	import { UserCircleOutline, FileDocOutline, DollarOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { principal } from '$lib/stores/auth';
	import { _ } from 'svelte-i18n';
	import ServicesList from './ServicesList.svelte';
	import TaxInformation from './TaxInformation.svelte';
	import PersonalData from './PersonalData.svelte';
	
	// Component state
	let loading = true;
	let error = '';
	let summaryData = null;
	
	// Get dashboard summary data for the user
	async function getDashboardSummary() {
		try {
			// Prepare call parameters
			const callParams = { 
				user_id: $principal || 'demo-user'
			};
			
			// Log the request details
			console.log('Calling get_dashboard_summary with parameters:', callParams);
			
			// Use the extension_async_call API method
			const response = await backend.extension_sync_call({
				extension_name: "citizen_dashboard",
				function_name: "get_dashboard_summary",
				args: JSON.stringify(callParams)
			});
			
			console.log('Dashboard summary response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed dashboard summary:', data);
				
				if (data.success) {
					// Handle successful response
					summaryData = data.data;
					console.log('Dashboard summary set:', summaryData);
				} else {
					// Handle error
					error = `Failed to get dashboard summary: ${data.error || 'Unknown error'}`;
					console.error(error);
				}
			} else {
				error = `Failed to get dashboard summary: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching dashboard summary:', err);
			error = `Error fetching dashboard summary: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	// Initialize component
	onMount(async () => {
		await getDashboardSummary();
	});
</script>

<div class="w-full">
	<h2 class="text-2xl font-bold mb-4">{$_('citizen_dashboard.title')}</h2>
	
	{#if loading}
		<div class="flex justify-center items-center p-8">
			<Spinner size="8" />
			<p class="ml-4 text-lg text-gray-500 dark:text-gray-400">{$_('citizen_dashboard.loading')}</p>
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">{$_('common.error')}:</span> {error}
		</Alert>
	{:else if summaryData}
		<!-- Dashboard Summary -->
		<Card padding="xl" class="mb-6">
			<div class="flex flex-col md:flex-row items-start md:items-center justify-between mb-4">
				<div>
					<h3 class="text-xl font-semibold">{$_('citizen_dashboard.dashboard_overview')}</h3>
					<p class="text-gray-500 dark:text-gray-400">{$_('citizen_dashboard.welcome_back', { values: { name: summaryData.user_name || 'Citizen' } })}</p>
				</div>
				<div class="mt-3 md:mt-0">
					<p class="text-sm text-gray-500 dark:text-gray-400">{$_('citizen_dashboard.last_updated', { values: { date: new Date().toLocaleString() } })}</p>
				</div>
			</div>
			
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<!-- Public Services Summary -->
				<div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-900/30">
					<div class="flex items-center">
						<FileDocOutline class="w-6 h-6 text-blue-600 dark:text-blue-400 mr-2" />
						<h4 class="text-lg font-medium text-blue-600 dark:text-blue-400">{$_('citizen_dashboard.tabs.public_services')}</h4>
					</div>
					<div class="mt-2">
						<p class="font-bold text-2xl">{summaryData.services_count || 0}</p>
						<p class="text-sm text-gray-600 dark:text-gray-400">{$_('citizen_dashboard.services_count', { values: { count: '' } })}</p>
					</div>
					<div class="mt-2 text-sm font-medium">
						<span class="text-yellow-600 dark:text-yellow-400">{$_('citizen_dashboard.approaching_deadlines', { values: { count: summaryData.services_approaching || 0 } })}</span>
					</div>
				</div>
				
				<!-- Tax Summary -->
				<div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-100 dark:border-green-900/30">
					<div class="flex items-center">
						<DollarOutline class="w-6 h-6 text-green-600 dark:text-green-400 mr-2" />
						<h4 class="text-lg font-medium text-green-600 dark:text-green-400">{$_('citizen_dashboard.tabs.my_taxes')}</h4>
					</div>
					<div class="mt-2">
						<p class="font-bold text-2xl">{summaryData.tax_records || 0}</p>
						<p class="text-sm text-gray-600 dark:text-gray-400">{$_('citizen_dashboard.tax_records', { values: { count: '' } })}</p>
					</div>
					<div class="mt-2 text-sm font-medium">
						<span class="text-red-600 dark:text-red-400">{$_('citizen_dashboard.overdue_payments', { values: { count: summaryData.tax_overdue || 0 } })}</span>
					</div>
				</div>
				
				<!-- Personal Data Summary -->
				<div class="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-100 dark:border-purple-900/30">
					<div class="flex items-center">
						<UserCircleOutline class="w-6 h-6 text-purple-600 dark:text-purple-400 mr-2" />
						<h4 class="text-lg font-medium text-purple-600 dark:text-purple-400">{$_('citizen_dashboard.tabs.personal_data')}</h4>
					</div>
					<div class="mt-2">
						<p class="font-bold text-2xl">{summaryData.personal_data_items || 0}</p>
						<p class="text-sm text-gray-600 dark:text-gray-400">{$_('citizen_dashboard.data_records', { values: { count: '' } })}</p>
					</div>
					<div class="mt-2 text-sm font-medium">
						<span class="text-blue-600 dark:text-blue-400">{$_('citizen_dashboard.recently_updated', { values: { count: summaryData.personal_data_updated || 0 } })}</span>
					</div>
				</div>
			</div>
		</Card>
		
		<!-- Tabs for different sections -->
		<Tabs style="underline">
			<TabItem open title={$_('citizen_dashboard.tabs.public_services')} icon={FileDocOutline}>
				<ServicesList userId={$principal || 'demo-user'} />
			</TabItem>
			
			<TabItem title={$_('citizen_dashboard.tabs.my_taxes')} icon={DollarOutline}>
				<TaxInformation userId={$principal || 'demo-user'} />
			</TabItem>
			
			<TabItem title={$_('citizen_dashboard.tabs.personal_data')} icon={UserCircleOutline}>
				<PersonalData userId={$principal || 'demo-user'} />
			</TabItem>
		</Tabs>
	{:else}
		<Alert color="blue" class="mb-4">
			{$_('citizen_dashboard.no_data')}
		</Alert>
	{/if}
</div>
