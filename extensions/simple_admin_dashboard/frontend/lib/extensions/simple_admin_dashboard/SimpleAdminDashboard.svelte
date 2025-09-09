<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Spinner, Alert } from 'flowbite-svelte';
	import { UserCircleOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { _ } from 'svelte-i18n';
	
	let loading = true;
	let error = '';
	let users = [];
	let pagination = null;
	
	async function loadUsers() {
		try {
			loading = true;
			error = '';
			
			console.log('Loading users...');
			
			const response = await backend.get_users(0, 20);
			console.log('Users response:', response);
			
			if (response && response.success && response.data && response.data.UsersList) {
				const usersList = response.data.UsersList.users || [];
				users = usersList.map(userJson => {
					try {
						return JSON.parse(userJson);
					} catch (e) {
						console.error('Error parsing user JSON:', e, userJson);
						return null;
					}
				}).filter(user => user !== null);
				
				pagination = response.data.UsersList.pagination;
				console.log('Loaded users:', users.length);
			} else {
				error = 'Failed to load users: Invalid response format';
				console.error('Invalid response:', response);
			}
		} catch (err) {
			console.error('Error loading users:', err);
			error = `Error loading users: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	function getUserDisplayName(user) {
		if (user.metadata) {
			try {
				const metadata = JSON.parse(user.metadata);
				return metadata.name || metadata.username || user._id;
			} catch (e) {
				return user._id;
			}
		}
		return user._id;
	}
	
	function formatTimestamp(timestamp) {
		if (!timestamp) return 'N/A';
		try {
			return new Date(timestamp).toLocaleDateString();
		} catch (e) {
			return timestamp;
		}
	}
	
	onMount(async () => {
		await loadUsers();
	});
</script>

<div class="w-full max-w-none px-4">
	<h2 class="text-2xl font-bold mb-4 flex items-center">
		<UserCircleOutline class="w-6 h-6 mr-2" />
		Simple Admin Dashboard
	</h2>
	<p class="text-gray-600 mb-6">Manage and monitor user accounts in the system</p>
	
	{#if loading}
		<div class="flex justify-center items-center p-8">
			<Spinner size="8" />
			<p class="ml-4 text-lg text-gray-500 dark:text-gray-400">Loading users...</p>
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">Error:</span> {error}
		</Alert>
	{:else}
		<Card padding="md" class="mb-4 w-full max-w-none">
			<div class="flex justify-between items-center mb-4">
				<h3 class="text-xl font-semibold">Users ({users.length})</h3>
				<button 
					class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
					on:click={loadUsers}
				>
					Refresh
				</button>
			</div>
			
			{#if users.length === 0}
				<div class="text-center py-8 text-gray-500">
					No users found
				</div>
			{:else}
				<div class="space-y-3">
					{#each users as user}
						<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
							<div class="flex justify-between items-start">
								<div class="flex-1">
									<h4 class="font-semibold text-gray-900 mb-1">
										{getUserDisplayName(user)}
									</h4>
									<p class="text-sm text-gray-600">ID: {user._id}</p>
									{#if user.timestamp_created}
										<p class="text-xs text-gray-500">
											Created: {formatTimestamp(user.timestamp_created)}
										</p>
									{/if}
								</div>
								<div class="flex items-center space-x-2">
									<span class="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
										Active
									</span>
								</div>
							</div>
							
							{#if user.metadata}
								<div class="mt-3 p-3 bg-gray-50 rounded text-sm">
									<strong class="text-gray-700">Metadata:</strong>
									<pre class="text-xs text-gray-600 whitespace-pre-wrap mt-1">{JSON.stringify(JSON.parse(user.metadata), null, 2)}</pre>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
			
			{#if pagination}
				<div class="mt-4 text-sm text-gray-500 text-center">
					Showing {users.length} of {pagination.total_items_count} users
					{#if pagination.total_pages > 1}
						(Page {pagination.page_num + 1} of {pagination.total_pages})
					{/if}
				</div>
			{/if}
		</Card>
	{/if}
</div>
