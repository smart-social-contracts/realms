<script>
	import { Card, Tabs, TabItem, Button, Badge, Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell } from 'flowbite-svelte';
	import { LockSolid, ClipboardListSolid, CheckOutline, ClockSolid, PlusOutline } from 'flowbite-svelte-icons';
	import { mockLitigations } from '$lib/dummy-data/extensions';

	function formatDate(dateStr) {
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getStatusColor(status) {
		switch(status.toLowerCase()) {
			case 'pending':
				return 'yellow';
			case 'resolved':
				return 'green';
			case 'dismissed':
				return 'gray';
			case 'appealed':
				return 'blue';
			default:
				return 'gray';
		}
	}

	function getStatusIcon(status) {
		switch(status.toLowerCase()) {
			case 'pending':
				return ClockSolid;
			case 'resolved':
				return CheckOutline;
			default:
				return ClipboardListSolid;
		}
	}
</script>

<div class="py-6">
	<div class="mb-8">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Justice & Litigation</h1>
		<p class="text-gray-600 dark:text-gray-400">Handle legal cases and litigation processes</p>
	</div>

	<Tabs style="underline">
		<TabItem open title="My Cases">
			<Card>
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Litigation Cases</h3>
					<Button size="sm">
						<PlusOutline class="w-4 h-4 mr-2" />
						New Case
					</Button>
				</div>
				
				<Table striped={true}>
					<TableHead>
						<TableHeadCell>Case</TableHeadCell>
						<TableHeadCell>Parties</TableHeadCell>
						<TableHeadCell>Judge</TableHeadCell>
						<TableHeadCell>Status</TableHeadCell>
						<TableHeadCell>Created</TableHeadCell>
						<TableHeadCell>Actions</TableHeadCell>
					</TableHead>
					<TableBody>
						{#each mockLitigations as litigation}
							<TableBodyRow>
								<TableBodyCell>
									<div>
										<div class="font-medium text-gray-900 dark:text-gray-200">{litigation.title}</div>
										<div class="text-sm text-gray-600 dark:text-gray-400">{litigation.description}</div>
									</div>
								</TableBodyCell>
								<TableBodyCell>
									<div class="text-sm">
										<div><strong>Plaintiff:</strong> {litigation.plaintiff}</div>
										<div><strong>Defendant:</strong> {litigation.defendant}</div>
									</div>
								</TableBodyCell>
								<TableBodyCell>{litigation.judge}</TableBodyCell>
								<TableBodyCell>
									<div class="flex items-center">
										<svelte:component this={getStatusIcon(litigation.status)} class="w-4 h-4 mr-2" />
										<Badge color={getStatusColor(litigation.status)}>{litigation.status}</Badge>
									</div>
								</TableBodyCell>
								<TableBodyCell>{formatDate(litigation.created_date)}</TableBodyCell>
								<TableBodyCell>
									<Button size="xs">View Details</Button>
								</TableBodyCell>
							</TableBodyRow>
						{/each}
					</TableBody>
				</Table>
			</Card>
		</TabItem>

		<TabItem title="Create Case">
			<Card>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200 mb-4">Create New Litigation Case</h3>
				
				<form class="space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Case Title</label>
						<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Enter case title">
					</div>
					
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Description</label>
						<textarea rows="4" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Describe the case details"></textarea>
					</div>
					
					<div class="grid gap-4 md:grid-cols-2">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Plaintiff</label>
							<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Plaintiff name">
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Defendant</label>
							<input type="text" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Defendant name">
						</div>
					</div>
					
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Evidence/Documents</label>
						<div class="border-2 border-dashed border-gray-300 rounded-md p-6 text-center">
							<p class="text-gray-600 dark:text-gray-400">Drag and drop files here or click to upload</p>
						</div>
					</div>
					
					<div class="flex justify-end space-x-2">
						<Button color="light">Cancel</Button>
						<Button>Submit Case</Button>
					</div>
				</form>
			</Card>
		</TabItem>
	</Tabs>
</div>
