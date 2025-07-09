<script>
	import { Card, Button, Badge } from 'flowbite-svelte';
	import { 
		WalletSolid, 
		ChartPieOutline, 
		BellSolid, 
		LockSolid, 
		ClipboardListSolid 
	} from 'flowbite-svelte-icons';

	const extensions = [
		{
			id: 'vault_manager',
			name: 'Vault Manager',
			description: 'Manage your cryptocurrency vault and transactions',
			icon: WalletSolid,
			version: '1.0.0',
			author: 'Realms Team',
			enabled: true,
			href: '/extensions/vault_manager'
		},
		{
			id: 'citizen_dashboard',
			name: 'Citizen Dashboard',
			description: 'Access public services and citizen information',
			icon: ChartPieOutline,
			version: '1.2.0',
			author: 'Realms Team',
			enabled: true,
			href: '/extensions/citizen_dashboard'
		},
		{
			id: 'notifications',
			name: 'Notifications',
			description: 'Manage and view system notifications',
			icon: BellSolid,
			version: '1.1.0',
			author: 'Realms Team',
			enabled: true,
			href: '/extensions/notifications'
		},
		{
			id: 'justice_litigation',
			name: 'Justice & Litigation',
			description: 'Handle legal cases and litigation processes',
			icon: LockSolid,
			version: '0.9.0',
			author: 'Realms Team',
			enabled: true,
			href: '/extensions/justice_litigation'
		},
		{
			id: 'land_registry',
			name: 'Land Registry',
			description: 'Manage land ownership and property records',
			icon: ClipboardListSolid,
			version: '1.0.0',
			author: 'Realms Team',
			enabled: true,
			href: '/extensions/land_registry'
		}
	];
</script>

<div class="py-6">
	<div class="mb-8">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Extensions</h1>
		<p class="text-gray-600 dark:text-gray-400">Manage and access available system extensions</p>
	</div>

	<div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
		{#each extensions as extension}
			<Card class="flex flex-col">
				<div class="flex items-center mb-4">
					<div class="p-3 mr-4 text-purple-600 bg-purple-100 rounded-full dark:bg-purple-900 dark:text-purple-200">
						<svelte:component this={extension.icon} class="w-6 h-6" />
					</div>
					<div class="flex-1">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">{extension.name}</h3>
						<div class="flex items-center space-x-2">
							<Badge color="blue">v{extension.version}</Badge>
							{#if extension.enabled}
								<Badge color="green">Enabled</Badge>
							{:else}
								<Badge color="gray">Disabled</Badge>
							{/if}
						</div>
					</div>
				</div>
				
				<p class="text-gray-600 dark:text-gray-400 mb-4 flex-1">{extension.description}</p>
				
				<div class="flex items-center justify-between">
					<span class="text-sm text-gray-500 dark:text-gray-400">by {extension.author}</span>
					<Button size="sm" href={extension.href}>
						Open Extension
					</Button>
				</div>
			</Card>
		{/each}
	</div>
</div>
