<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Spinner, Alert, Table, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell, Badge, Button } from 'flowbite-svelte';
	import { ArrowRightOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	
	// Props
	export let userId: string;
	
	// Component state
	let loading = true;
	let error = '';
	let services = [];
	
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
	
	// Determine if a date is approaching (within 7 days)
	function isDateApproaching(dateStr) {
		if (!dateStr) return false;
		const today = new Date();
		const dueDate = new Date(dateStr);
		const diffTime = dueDate.getTime() - today.getTime();
		const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
		return diffDays >= 0 && diffDays <= 7;
	}
	
	// Get status badge color based on status value
	function getStatusColor(status) {
		switch(status.toLowerCase()) {
			case 'active':
				return 'green';
			case 'pending':
				return 'yellow';
			case 'expired':
				return 'red';
			case 'suspended':
				return 'purple';
			default:
				return 'blue';
		}
	}
	
	// Get services for the user
	async function getServices() {
		try {
			// Prepare call parameters
			const callParams = { 
				user_id: userId
			};
			
			// Log the request details
			console.log('Calling get_public_services with parameters:', callParams);
			
			// Use the extension_async_call API method
			const response = await backend.extension_sync_call({
				extension_name: "member_dashboard",
				function_name: "get_public_services",
				args: JSON.stringify(callParams)
			});
			
			console.log('Services response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed services data:', data);
				
				if (data.success) {
					// Handle successful response
					services = data.data.services;
					console.log('Services set:', services);
				} else {
					// Handle error
					error = `Failed to get services: ${data.error || 'Unknown error'}`;
					console.error(error);
				}
			} else {
				error = `Failed to get services: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching services:', err);
			error = `Error fetching services: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	// Initialize component
	onMount(async () => {
		await getServices();
	});
</script>

<div class="w-full">
	<div class="flex items-center justify-between mb-4">
		<h3 class="text-xl font-semibold">My Public Services</h3>
		<Button size="xs" color="blue">Request New Service</Button>
	</div>
	
	{#if loading}
		<div class="flex justify-center items-center p-8">
			<Spinner size="8" />
			<p class="ml-4 text-lg text-gray-500 dark:text-gray-400">Loading services...</p>
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">Error:</span> {error}
		</Alert>
	{:else if services && services.length > 0}
		<Card>
			<Table striped={true}>
				<TableHead>
					<TableHeadCell>Service Name</TableHeadCell>
					<TableHeadCell>Status</TableHeadCell>
					<TableHeadCell>Due Date</TableHeadCell>
					<TableHeadCell>Provider</TableHeadCell>
					<TableHeadCell>Actions</TableHeadCell>
				</TableHead>
				<TableBody tableBodyClass="divide-y">
					{#each services as service}
						<TableBodyRow>
							<TableBodyCell>
								<div class="font-medium">{service.name}</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">{service.description}</div>
							</TableBodyCell>
							<TableBodyCell>
								<Badge color={getStatusColor(service.status)} rounded>{service.status}</Badge>
							</TableBodyCell>
							<TableBodyCell>
								<div class={isDateApproaching(service.due_date) ? 'text-yellow-600 dark:text-yellow-400 font-medium' : ''}>
									{formatDate(service.due_date)}
									{#if isDateApproaching(service.due_date)}
										<div class="text-xs">Approaching</div>
									{/if}
								</div>
							</TableBodyCell>
							<TableBodyCell>
								{service.provider}
							</TableBodyCell>
							<TableBodyCell>
								<Button size="xs" href={service.link || '#'} class="flex items-center">
									Details <ArrowRightOutline class="w-3 h-3 ml-1" />
								</Button>
							</TableBodyCell>
						</TableBodyRow>
					{/each}
				</TableBody>
			</Table>
		</Card>
	{:else}
		<Alert color="blue" class="mb-4">
			No public services available at this time.
		</Alert>
	{/if}
</div>
