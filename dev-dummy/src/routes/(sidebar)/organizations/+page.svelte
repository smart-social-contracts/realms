<script>
	import { Card, Button, Badge, Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell } from 'flowbite-svelte';
	import { UsersOutline, PlusOutline, EyeOutline } from 'flowbite-svelte-icons';
	import { mockOrganizations } from '$lib/dummy-data/organizations';

	function formatDate(dateStr) {
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getTypeColor(type) {
		switch(type) {
			case 'government':
				return 'blue';
			case 'business':
				return 'green';
			case 'community':
				return 'purple';
			default:
				return 'gray';
		}
	}
</script>

<div class="py-6">
	<div class="mb-8">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Organizations</h1>
				<p class="text-gray-600 dark:text-gray-400">Manage and view organizational entities</p>
			</div>
			<Button>
				<PlusOutline class="w-4 h-4 mr-2" />
				Create Organization
			</Button>
		</div>
	</div>

	<div class="grid gap-6 mb-8 md:grid-cols-3">
		<Card>
			<div class="flex items-center">
				<div class="p-3 mr-4 text-blue-600 bg-blue-100 rounded-full dark:bg-blue-900 dark:text-blue-200">
					<UsersOutline class="w-6 h-6" />
				</div>
				<div>
					<p class="mb-2 text-sm font-medium text-gray-600 dark:text-gray-400">Total Organizations</p>
					<p class="text-lg font-semibold text-gray-700 dark:text-gray-200">{mockOrganizations.length}</p>
				</div>
			</div>
		</Card>
		
		<Card>
			<div class="flex items-center">
				<div class="p-3 mr-4 text-green-600 bg-green-100 rounded-full dark:bg-green-900 dark:text-green-200">
					<UsersOutline class="w-6 h-6" />
				</div>
				<div>
					<p class="mb-2 text-sm font-medium text-gray-600 dark:text-gray-400">Active Organizations</p>
					<p class="text-lg font-semibold text-gray-700 dark:text-gray-200">
						{mockOrganizations.filter(org => org.status === 'active').length}
					</p>
				</div>
			</div>
		</Card>
		
		<Card>
			<div class="flex items-center">
				<div class="p-3 mr-4 text-purple-600 bg-purple-100 rounded-full dark:bg-purple-900 dark:text-purple-200">
					<UsersOutline class="w-6 h-6" />
				</div>
				<div>
					<p class="mb-2 text-sm font-medium text-gray-600 dark:text-gray-400">Total Members</p>
					<p class="text-lg font-semibold text-gray-700 dark:text-gray-200">
						{mockOrganizations.reduce((sum, org) => sum + org.members, 0)}
					</p>
				</div>
			</div>
		</Card>
	</div>

	<Card>
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">All Organizations</h3>
		</div>
		
		<Table striped={true}>
			<TableHead>
				<TableHeadCell>Organization</TableHeadCell>
				<TableHeadCell>Type</TableHeadCell>
				<TableHeadCell>Members</TableHeadCell>
				<TableHeadCell>Status</TableHeadCell>
				<TableHeadCell>Created</TableHeadCell>
				<TableHeadCell>Actions</TableHeadCell>
			</TableHead>
			<TableBody>
				{#each mockOrganizations as org}
					<TableBodyRow>
						<TableBodyCell>
							<div>
								<div class="font-medium text-gray-900 dark:text-gray-200">{org.name}</div>
								<div class="text-sm text-gray-600 dark:text-gray-400">{org.description}</div>
							</div>
						</TableBodyCell>
						<TableBodyCell>
							<Badge color={getTypeColor(org.type)}>{org.type}</Badge>
						</TableBodyCell>
						<TableBodyCell>
							<div class="flex items-center">
								<UsersOutline class="w-4 h-4 mr-1 text-gray-500" />
								{org.members}
							</div>
						</TableBodyCell>
						<TableBodyCell>
							<Badge color="green">{org.status}</Badge>
						</TableBodyCell>
						<TableBodyCell>{formatDate(org.created)}</TableBodyCell>
						<TableBodyCell>
							<div class="flex space-x-2">
								<Button size="xs">
									<EyeOutline class="w-3 h-3 mr-1" />
									View
								</Button>
								<Button size="xs" color="light">Edit</Button>
							</div>
						</TableBodyCell>
					</TableBodyRow>
				{/each}
			</TableBody>
		</Table>
	</Card>
</div>
