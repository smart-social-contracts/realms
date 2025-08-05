<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Spinner, Alert, Table, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell, Badge } from 'flowbite-svelte';
	import { DollarOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	
	// Props
	export let userId: string;
	
	// Component state
	let loading = true;
	let error = '';
	let taxData = null;
	
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
	
	// Format currency for display
	function formatCurrency(amount) {
		if (amount === undefined || amount === null) return 'N/A';
		return new Intl.NumberFormat('en-US', { 
			style: 'currency', 
			currency: 'USD' 
		}).format(amount);
	}
	
	// Get status badge color based on status value
	function getStatusColor(status) {
		switch(status.toLowerCase()) {
			case 'paid':
				return 'green';
			case 'pending':
				return 'yellow';
			case 'overdue':
				return 'red';
			case 'processing':
				return 'purple';
			default:
				return 'blue';
		}
	}
	
	// Get tax information for the user
	async function getTaxInformation() {
		try {
			// Prepare call parameters
			const callParams = { 
				user_id: userId
			};
			
			// Log the request details
			console.log('Calling get_tax_information with parameters:', callParams);
			
			// Use the extension_async_call API method
			const response = await backend.extension_sync_call({
				extension_name: "citizen_dashboard",
				function_name: "get_tax_information",
				args: JSON.stringify(callParams)
			});
			
			console.log('Tax information response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed tax data:', data);
				
				if (data.success) {
					// Handle successful response
					taxData = data.data;
					console.log('Tax data set:', taxData);
				} else {
					// Handle error
					error = `Failed to get tax information: ${data.error || 'Unknown error'}`;
					console.error(error);
				}
			} else {
				error = `Failed to get tax information: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching tax information:', err);
			error = `Error fetching tax information: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	// Initialize component
	onMount(async () => {
		await getTaxInformation();
	});
</script>

<div class="w-full">
	<h3 class="text-xl font-semibold mb-4">My Tax Information</h3>
	
	{#if loading}
		<div class="flex justify-center items-center p-8">
			<Spinner size="8" />
			<p class="ml-4 text-lg text-gray-500 dark:text-gray-400">Loading tax information...</p>
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">Error:</span> {error}
		</Alert>
	{:else if taxData}
		<!-- Tax Summary Cards -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
			<!-- Total Paid -->
			<Card padding="sm" class="w-full">
				<div class="flex items-center">
					<div class="inline-flex items-center justify-center w-10 h-10 mr-3 bg-green-100 text-green-500 dark:bg-green-900 dark:text-green-300 rounded-full">
						<DollarOutline class="w-5 h-5" />
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Paid</p>
						<p class="text-xl font-bold">{formatCurrency(taxData.summary.total_paid)}</p>
					</div>
				</div>
			</Card>
			
			<!-- Pending Payments -->
			<Card padding="sm" class="w-full">
				<div class="flex items-center">
					<div class="inline-flex items-center justify-center w-10 h-10 mr-3 bg-yellow-100 text-yellow-500 dark:bg-yellow-900 dark:text-yellow-300 rounded-full">
						<DollarOutline class="w-5 h-5" />
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Pending Payments</p>
						<p class="text-xl font-bold">{formatCurrency(taxData.summary.total_pending)}</p>
					</div>
				</div>
			</Card>
			
			<!-- Overdue Payments -->
			<Card padding="sm" class="w-full">
				<div class="flex items-center">
					<div class="inline-flex items-center justify-center w-10 h-10 mr-3 bg-red-100 text-red-500 dark:bg-red-900 dark:text-red-300 rounded-full">
						<DollarOutline class="w-5 h-5" />
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Overdue Payments</p>
						<p class="text-xl font-bold">{formatCurrency(taxData.summary.total_overdue)}</p>
					</div>
				</div>
			</Card>
		</div>
		
		<!-- Tax Records Table -->
		<Card>
			<Table striped={true}>
				<TableHead>
					<TableHeadCell>Tax Type</TableHeadCell>
					<TableHeadCell>Period</TableHeadCell>
					<TableHeadCell>Amount</TableHeadCell>
					<TableHeadCell>Due Date</TableHeadCell>
					<TableHeadCell>Status</TableHeadCell>
				</TableHead>
				<TableBody tableBodyClass="divide-y">
					{#each taxData.tax_records as record}
						<TableBodyRow>
							<TableBodyCell>
								<div class="font-medium">{record.tax_type}</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">{record.description}</div>
							</TableBodyCell>
							<TableBodyCell>
								{record.period}
							</TableBodyCell>
							<TableBodyCell>
								{formatCurrency(record.amount)}
							</TableBodyCell>
							<TableBodyCell>
								{formatDate(record.due_date)}
							</TableBodyCell>
							<TableBodyCell>
								<Badge color={getStatusColor(record.status)} rounded>{record.status}</Badge>
							</TableBodyCell>
						</TableBodyRow>
					{/each}
				</TableBody>
			</Table>
		</Card>
		
		<!-- Tax Info Alert -->
		<Alert color="blue" class="mt-4">
			<p class="font-medium">Need help with your taxes?</p>
			<p class="text-sm mt-1">Contact the citizen tax help desk at <span class="font-medium">tax-help@city.gov</span> or visit your local tax office.</p>
		</Alert>
	{:else}
		<Alert color="blue" class="mb-4">
			No tax information available at this time.
		</Alert>
	{/if}
</div>
