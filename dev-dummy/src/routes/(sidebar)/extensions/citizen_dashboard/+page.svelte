<script>
	import { Card, Tabs, TabItem } from 'flowbite-svelte';
	import { ChartPieOutline, UserCircleOutline, DollarOutline, ClipboardListSolid } from 'flowbite-svelte-icons';
	import { mockCitizenServices, mockPersonalData, mockTaxInformation } from '$lib/dummy-data/extensions';

	function formatDate(dateStr) {
		if (!dateStr) return 'N/A';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { 
			year: 'numeric', 
			month: 'short', 
			day: 'numeric' 
		});
	}

	function getStatusColor(status) {
		switch(status.toLowerCase()) {
			case 'active':
				return 'green';
			case 'pending':
				return 'yellow';
			case 'expired':
				return 'red';
			case 'filed':
				return 'blue';
			case 'paid':
				return 'green';
			default:
				return 'gray';
		}
	}
</script>

<div class="py-6">
	<div class="mb-8">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Citizen Dashboard</h1>
		<p class="text-gray-600 dark:text-gray-400">Access public services and citizen information</p>
	</div>

	<Tabs style="underline">
		<TabItem open title="Services">
			<Card>
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">My Public Services</h3>
				</div>
				
				<div class="space-y-4">
					{#each mockCitizenServices as service}
						<div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg dark:bg-gray-700">
							<div class="flex-1">
								<h4 class="font-medium text-gray-900 dark:text-gray-200">{service.name}</h4>
								<p class="text-sm text-gray-600 dark:text-gray-400">{service.description}</p>
								<p class="text-sm text-gray-500 dark:text-gray-500">Provider: {service.provider}</p>
							</div>
							<div class="flex items-center space-x-4">
								<div class="text-right">
									<div class="text-sm text-gray-600 dark:text-gray-400">Due: {formatDate(service.due_date)}</div>
									<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{getStatusColor(service.status)}-100 text-{getStatusColor(service.status)}-800">
										{service.status}
									</span>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</Card>
		</TabItem>

		<TabItem title="Personal Data">
			<Card>
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Personal Information</h3>
				</div>
				
				<div class="grid gap-6 md:grid-cols-2">
					<div class="space-y-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Full Name</label>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">{mockPersonalData.name}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">{mockPersonalData.email}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Phone</label>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">{mockPersonalData.phone}</p>
						</div>
					</div>
					<div class="space-y-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Address</label>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">{mockPersonalData.address}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Date of Birth</label>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">{formatDate(mockPersonalData.dateOfBirth)}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Citizenship</label>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100 flex items-center">
								{mockPersonalData.citizenship}
								{#if mockPersonalData.verified}
									<span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
										Verified
									</span>
								{/if}
							</p>
						</div>
					</div>
				</div>
			</Card>
		</TabItem>

		<TabItem title="Tax Information">
			<Card>
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Tax Information</h3>
				</div>
				
				<div class="space-y-4">
					{#each mockTaxInformation as tax}
						<div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg dark:bg-gray-700">
							<div class="flex-1">
								<h4 class="font-medium text-gray-900 dark:text-gray-200">Tax Year {tax.year}</h4>
								<p class="text-sm text-gray-600 dark:text-gray-400">Filed: {formatDate(tax.filed_date)}</p>
							</div>
							<div class="flex items-center space-x-4">
								<div class="text-right">
									<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
										${tax.amount_paid.toLocaleString()} paid
									</div>
									{#if tax.amount_owed > 0}
										<div class="text-sm text-red-600">
											${tax.amount_owed.toLocaleString()} owed
										</div>
									{/if}
								</div>
								<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{getStatusColor(tax.status)}-100 text-{getStatusColor(tax.status)}-800">
									{tax.status}
								</span>
							</div>
						</div>
					{/each}
				</div>
			</Card>
		</TabItem>
	</Tabs>
</div>
