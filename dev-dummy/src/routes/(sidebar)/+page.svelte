<script>
	import { Card, Button } from 'flowbite-svelte';
	import { ChartPieOutline, UsersOutline, LayersSolid, BellSolid } from 'flowbite-svelte-icons';
	import { mockOrganizations, mockTrafficData } from '$lib/dummy-data/organizations';
	import { mockNotifications } from '$lib/dummy-data/extensions';

	const stats = [
		{
			title: 'Total Organizations',
			value: mockOrganizations.length,
			icon: UsersOutline,
			color: 'text-blue-600'
		},
		{
			title: 'Active Extensions',
			value: 5,
			icon: LayersSolid,
			color: 'text-green-600'
		},
		{
			title: 'Unread Notifications',
			value: mockNotifications.filter(n => !n.read).length,
			icon: BellSolid,
			color: 'text-yellow-600'
		},
		{
			title: 'Page Views',
			value: mockTrafficData.pageViews.toLocaleString(),
			icon: ChartPieOutline,
			color: 'text-purple-600'
		}
	];
</script>

<div class="py-6">
	<div class="mb-8">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Dashboard</h1>
		<p class="text-gray-600 dark:text-gray-400">Welcome to Realms gOS Development Mode</p>
	</div>

	<div class="grid gap-6 mb-8 md:grid-cols-2 xl:grid-cols-4">
		{#each stats as stat}
			<Card class="flex items-center p-4">
				<div class="p-3 mr-4 {stat.color} bg-gray-100 rounded-full dark:bg-gray-700">
					<svelte:component this={stat.icon} class="w-5 h-5" />
				</div>
				<div>
					<p class="mb-2 text-sm font-medium text-gray-600 dark:text-gray-400">
						{stat.title}
					</p>
					<p class="text-lg font-semibold text-gray-700 dark:text-gray-200">
						{stat.value}
					</p>
				</div>
			</Card>
		{/each}
	</div>

	<div class="grid gap-6 mb-8 md:grid-cols-2">
		<Card>
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Recent Organizations</h2>
				<Button size="xs" href="/organizations">View All</Button>
			</div>
			<div class="space-y-3">
				{#each mockOrganizations.slice(0, 3) as org}
					<div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg dark:bg-gray-700">
						<div>
							<h3 class="font-medium text-gray-900 dark:text-gray-200">{org.name}</h3>
							<p class="text-sm text-gray-600 dark:text-gray-400">{org.members} members</p>
						</div>
						<span class="px-2 py-1 text-xs font-medium text-green-800 bg-green-100 rounded-full dark:bg-green-900 dark:text-green-200">
							{org.status}
						</span>
					</div>
				{/each}
			</div>
		</Card>

		<Card>
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Recent Notifications</h2>
				<Button size="xs" href="/extensions/notifications">View All</Button>
			</div>
			<div class="space-y-3">
				{#each mockNotifications.slice(0, 3) as notification}
					<div class="flex items-start p-3 bg-gray-50 rounded-lg dark:bg-gray-700">
						<div class="flex-1">
							<h3 class="font-medium text-gray-900 dark:text-gray-200">{notification.title}</h3>
							<p class="text-sm text-gray-600 dark:text-gray-400">{notification.message}</p>
						</div>
						{#if !notification.read}
							<span class="w-2 h-2 bg-blue-600 rounded-full"></span>
						{/if}
					</div>
				{/each}
			</div>
		</Card>
	</div>

	<Card>
		<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-200">Quick Actions</h2>
		<div class="grid gap-4 md:grid-cols-3">
			<Button href="/extensions/vault_manager" class="flex items-center justify-center p-4">
				<LayersSolid class="w-5 h-5 mr-2" />
				Manage Vault
			</Button>
			<Button href="/extensions/citizen_dashboard" class="flex items-center justify-center p-4">
				<ChartPieOutline class="w-5 h-5 mr-2" />
				Citizen Services
			</Button>
			<Button href="/organizations" class="flex items-center justify-center p-4">
				<UsersOutline class="w-5 h-5 mr-2" />
				View Organizations
			</Button>
		</div>
	</Card>
</div>
