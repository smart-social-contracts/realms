<script>
	import { page } from '$app/stores';
	import { _ } from 'svelte-i18n';
	import { 
		HomeOutline, 
		LayersSolid, 
		UsersOutline, 
		CogOutline,
		BellSolid,
		WalletSolid,
		ChartPieOutline,
		LockSolid,
		ClipboardListSolid
	} from 'flowbite-svelte-icons';

	const menuItems = [
		{ href: '/', icon: HomeOutline, label: 'Dashboard' },
		{ href: '/extensions', icon: LayersSolid, label: 'Extensions' },
		{ href: '/organizations', icon: UsersOutline, label: 'Organizations' },
		{ href: '/settings', icon: CogOutline, label: 'Settings' }
	];

	const extensions = [
		{ href: '/extensions/vault_manager', icon: WalletSolid, label: 'Vault Manager' },
		{ href: '/extensions/citizen_dashboard', icon: ChartPieOutline, label: 'Citizen Dashboard' },
		{ href: '/extensions/notifications', icon: BellSolid, label: 'Notifications' },
		{ href: '/extensions/justice_litigation', icon: LockSolid, label: 'Justice & Litigation' },
		{ href: '/extensions/land_registry', icon: ClipboardListSolid, label: 'Land Registry' }
	];

	$: currentPath = $page.url.pathname;
</script>

<aside class="z-20 hidden w-64 overflow-y-auto bg-white dark:bg-gray-800 md:block flex-shrink-0">
	<div class="py-4 text-gray-500 dark:text-gray-400">
		<a class="ml-6 text-lg font-bold text-gray-800 dark:text-gray-200" href="/">
			Realms gOS
			<span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded ml-2">DEV</span>
		</a>
		
		<ul class="mt-6">
			{#each menuItems as item}
				<li class="relative px-6 py-3">
					{#if currentPath === item.href}
						<span class="absolute inset-y-0 left-0 w-1 bg-purple-600 rounded-tr-lg rounded-br-lg" aria-hidden="true"></span>
					{/if}
					<a
						class="inline-flex items-center w-full text-sm font-semibold transition-colors duration-150 hover:text-gray-800 dark:hover:text-gray-200 {currentPath === item.href ? 'text-gray-800 dark:text-gray-100' : ''}"
						href={item.href}
					>
						<svelte:component this={item.icon} class="w-5 h-5" />
						<span class="ml-4">{item.label}</span>
					</a>
				</li>
			{/each}
		</ul>

		<div class="px-6 my-6">
			<div class="text-xs font-semibold text-gray-400 uppercase tracking-wide">Extensions</div>
		</div>

		<ul>
			{#each extensions as extension}
				<li class="relative px-6 py-3">
					{#if currentPath === extension.href}
						<span class="absolute inset-y-0 left-0 w-1 bg-purple-600 rounded-tr-lg rounded-br-lg" aria-hidden="true"></span>
					{/if}
					<a
						class="inline-flex items-center w-full text-sm font-semibold transition-colors duration-150 hover:text-gray-800 dark:hover:text-gray-200 {currentPath === extension.href ? 'text-gray-800 dark:text-gray-100' : ''}"
						href={extension.href}
					>
						<svelte:component this={extension.icon} class="w-5 h-5" />
						<span class="ml-4">{extension.label}</span>
					</a>
				</li>
			{/each}
		</ul>
	</div>
</aside>
