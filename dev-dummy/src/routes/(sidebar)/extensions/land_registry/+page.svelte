<script>
	import { Card, Button, Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell, Badge, Tabs, TabItem } from 'flowbite-svelte';
	import { ClipboardListSolid, PlusOutline, EditOutline, HomeOutline } from 'flowbite-svelte-icons';
	import { mockLandRegistry } from '$lib/dummy-data/extensions';

	function formatCurrency(amount) {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD'
		}).format(amount);
	}

	function formatDate(dateStr) {
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getOwnerTypeColor(type) {
		return type === 'individual' ? 'blue' : 'green';
	}
</script>

<div class="py-6">
	<div class="mb-8">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Land Registry</h1>
		<p class="text-gray-600 dark:text-gray-400">Manage land ownership and property records</p>
	</div>

	<Tabs style="underline">
		<TabItem open title="Property Records">
			<Card>
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Land Registry Records</h3>
					<Button size="sm">
						<PlusOutline class="w-4 h-4 mr-2" />
						Register New Property
					</Button>
				</div>
				
				<Table striped={true}>
					<TableHead>
						<TableHeadCell>Parcel ID</TableHeadCell>
						<TableHeadCell>Address</TableHeadCell>
						<TableHeadCell>Size</TableHeadCell>
						<TableHeadCell>Owner</TableHeadCell>
						<TableHeadCell>Value</TableHeadCell>
						<TableHeadCell>Last Updated</TableHeadCell>
						<TableHeadCell>Actions</TableHeadCell>
					</TableHead>
					<TableBody>
						{#each mockLandRegistry as property}
							<TableBodyRow>
								<TableBodyCell>
									<div class="flex items-center">
										<HomeOutline class="w-4 h-4 mr-2 text-gray-500" />
										<span class="font-mono text-sm">{property.parcel_id}</span>
									</div>
								</TableBodyCell>
								<TableBodyCell>
									<div class="font-medium text-gray-900 dark:text-gray-200">{property.address}</div>
								</TableBodyCell>
								<TableBodyCell>{property.size}</TableBodyCell>
								<TableBodyCell>
									<div>
										<div class="font-medium text-gray-900 dark:text-gray-200">{property.owner_name}</div>
										<Badge color={getOwnerTypeColor(property.owner_type)} size="sm">
											{property.owner_type}
										</Badge>
									</div>
								</TableBodyCell>
								<TableBodyCell>
									<span class="font-medium">{formatCurrency(property.value)}</span>
								</TableBodyCell>
								<TableBodyCell>{formatDate(property.last_updated)}</TableBodyCell>
								<TableBodyCell>
									<div class="flex space-x-2">
										<Button size="xs">
											<EditOutline class="w-3 h-3 mr-1" />
											Edit
										</Button>
										<Button size="xs" color="light">View</Button>
									</div>
								</TableBodyCell>
							</TableBodyRow>
						{/each}
					</TableBody>
				</Table>
			</Card>
		</TabItem>

		<TabItem title="Register Property">
			<Card>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200 mb-4">Register New Property</h3>
				
				<form class="space-y-4">
					<div class="grid gap-4 md:grid-cols-2">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Parcel ID</label>
							<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="LAND-XXX">
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Property Size</label>
							<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="e.g., 0.25 acres">
						</div>
					</div>
					
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Property Address</label>
						<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Full property address">
					</div>
					
					<div class="grid gap-4 md:grid-cols-2">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Owner Type</label>
							<select class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700">
								<option value="individual">Individual</option>
								<option value="organization">Organization</option>
							</select>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Owner Name</label>
							<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Owner name">
						</div>
					</div>
					
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Property Value (USD)</label>
						<input type="number" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="250000">
					</div>
					
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Supporting Documents</label>
						<div class="border-2 border-dashed border-gray-300 rounded-md p-6 text-center">
							<ClipboardListSolid class="w-8 h-8 mx-auto text-gray-400 mb-2" />
							<p class="text-gray-600 dark:text-gray-400">Upload property deeds, surveys, and other documents</p>
						</div>
					</div>
					
					<div class="flex justify-end space-x-2">
						<Button color="light">Cancel</Button>
						<Button>Register Property</Button>
					</div>
				</form>
			</Card>
		</TabItem>

		<TabItem title="Transfer Ownership">
			<Card>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200 mb-4">Transfer Property Ownership</h3>
				
				<form class="space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Select Property</label>
						<select class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700">
							<option value="">Choose a property...</option>
							{#each mockLandRegistry as property}
								<option value={property.id}>{property.parcel_id} - {property.address}</option>
							{/each}
						</select>
					</div>
					
					<div class="grid gap-4 md:grid-cols-2">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">New Owner Type</label>
							<select class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700">
								<option value="individual">Individual</option>
								<option value="organization">Organization</option>
							</select>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">New Owner Name</label>
							<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="New owner name">
						</div>
					</div>
					
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Transfer Reason</label>
						<textarea rows="3" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Reason for ownership transfer"></textarea>
					</div>
					
					<div class="flex justify-end space-x-2">
						<Button color="light">Cancel</Button>
						<Button>Transfer Ownership</Button>
					</div>
				</form>
			</Card>
		</TabItem>
	</Tabs>
</div>
