<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Spinner, Alert, Button } from 'flowbite-svelte';
	import { EditOutline, ShieldCheckSolid } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	
	// Props
	export let userId: string;
	
	// Component state
	let loading = true;
	let error = '';
	let personalData = null;
	
	// Format date for display
	function formatDate(dateStr) {
		if (!dateStr) return 'N/A';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { 
			year: 'numeric', 
			month: 'short', 
			day: 'numeric' 
		});
	}
	
	// Get personal data for the user
	async function getPersonalData() {
		try {
			// Prepare call parameters
			const callParams = { 
				user_id: userId
			};
			
			// Log the request details
			console.log('Calling get_personal_data with parameters:', callParams);
			
			// Use the extension_async_call API method
			const response = await backend.extension_sync_call({
				extension_name: "citizen_dashboard",
				function_name: "get_personal_data",
				args: JSON.stringify(callParams)
			});
			
			console.log('Personal data response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed personal data:', data);
				
				if (data.success) {
					// Handle successful response
					personalData = data.data.personal_data;
					console.log('Personal data set:', personalData);
				} else {
					// Handle error
					error = `Failed to get personal data: ${data.error || 'Unknown error'}`;
					console.error(error);
				}
			} else {
				error = `Failed to get personal data: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching personal data:', err);
			error = `Error fetching personal data: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	// Initialize component
	onMount(async () => {
		await getPersonalData();
	});
</script>

<div class="w-full">
	<div class="flex items-center justify-between mb-4">
		<h3 class="text-xl font-semibold">My Personal Data</h3>
		<div class="flex items-center text-sm text-gray-500 dark:text-gray-400">
			<ShieldCheckSolid class="w-4 h-4 mr-1 text-green-500" />
			<span>Secured with End-to-End Encryption</span>
		</div>
	</div>
	
	{#if loading}
		<div class="flex justify-center items-center p-8">
			<Spinner size="8" />
			<p class="ml-4 text-lg text-gray-500 dark:text-gray-400">Loading personal data...</p>
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">Error:</span> {error}
		</Alert>
	{:else if personalData}
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<!-- Personal Information Card -->
			<Card padding="lg" class="w-full">
				<div class="flex justify-between items-start mb-4">
					<h4 class="text-lg font-semibold">Personal Information</h4>
					<Button size="xs" color="light" class="flex items-center">
						<EditOutline class="w-3 h-3 mr-1" /> Edit
					</Button>
				</div>
				
				<div class="space-y-3">
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Full Name</p>
						<p class="font-medium">{personalData.name}</p>
					</div>
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Citizen ID</p>
						<p class="font-medium">{personalData.id_number}</p>
					</div>
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Date of Birth</p>
						<p class="font-medium">{formatDate(personalData.date_of_birth)}</p>
					</div>
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Citizenship Status</p>
						<p class="font-medium">{personalData.citizenship_status}</p>
					</div>
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Registration Date</p>
						<p class="font-medium">{formatDate(personalData.registration_date)}</p>
					</div>
				</div>
			</Card>
			
			<!-- Contact Information Card -->
			<Card padding="lg" class="w-full">
				<div class="flex justify-between items-start mb-4">
					<h4 class="text-lg font-semibold">Contact Information</h4>
					<Button size="xs" color="light" class="flex items-center">
						<EditOutline class="w-3 h-3 mr-1" /> Edit
					</Button>
				</div>
				
				<div class="space-y-3">
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Address</p>
						<p class="font-medium">{personalData.address}</p>
					</div>
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Email</p>
						<p class="font-medium">{personalData.email}</p>
					</div>
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Phone</p>
						<p class="font-medium">{personalData.phone}</p>
					</div>
					<div class="pt-2">
						<Alert color="blue" class="text-sm">
							You can update your contact information at any time. Ensure that your details are kept up to date to receive important notifications.
						</Alert>
					</div>
				</div>
			</Card>
			
			<!-- Privacy Controls -->
			<Card padding="lg" class="w-full md:col-span-2">
				<h4 class="text-lg font-semibold mb-4">Privacy and Data Sharing Controls</h4>
				
				<div class="text-sm text-gray-500 dark:text-gray-400 mb-4">
					<p>Your personal data is only shared with authorized government services. You can manage your data sharing preferences below.</p>
				</div>
				
				<div class="flex justify-end">
					<Button color="light" class="mr-2">Manage Data Sharing</Button>
					<Button color="blue">Download My Data</Button>
				</div>
			</Card>
		</div>
	{:else}
		<Alert color="blue" class="mb-4">
			No personal data available at this time.
		</Alert>
	{/if}
</div>
