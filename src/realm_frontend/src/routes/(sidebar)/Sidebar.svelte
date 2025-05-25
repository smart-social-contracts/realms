<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';

	import {
		Sidebar,
		SidebarDropdownWrapper,
		SidebarGroup,
		SidebarItem,
		SidebarWrapper
	} from 'flowbite-svelte';
	import {
		AngleDownOutline,
		AngleUpOutline,
		ClipboardListSolid,
		CogOutline,
		FileChartBarSolid,
		GithubSolid,
		LayersSolid,
		LifeSaverSolid,
		LockSolid,
		WandMagicSparklesOutline,
		ChartPieOutline,
		RectangleListSolid,
		TableColumnSolid,
		UsersOutline,
		HomeOutline,
		WalletSolid
	} from 'flowbite-svelte-icons';
	
	// Import extension system
	import { getAllExtensions } from '$lib/extensions';
	import { getIcon } from '$lib/utils/iconMap';

	export let drawerHidden: boolean = false;

	const closeDrawer = () => {
		drawerHidden = true;
	};

	let iconClass =
		'flex-shrink-0 w-6 h-6 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white';
	let itemClass =
		'flex items-center p-2 text-base text-gray-900 transition duration-75 rounded-lg hover:bg-gray-100 group dark:text-gray-200 dark:hover:bg-gray-700';
	let groupClass = 'pt-2 space-y-2';

	$: mainSidebarUrl = $page.url.pathname;
	let activeMainSidebar: string;

	afterNavigate((navigation) => {
		// this fixes https://github.com/themesberg/flowbite-svelte/issues/364
		document.getElementById('svelte')?.scrollTo({ top: 0 });
		closeDrawer();

		activeMainSidebar = navigation.to?.url.pathname ?? '';
	});

	// Get all extensions for the sidebar
	const extensions = getAllExtensions();

	// Core navigation items
	const coreNavItems = [
		{ name: 'Dashboard', icon: ChartPieOutline, href: '/dashboard' },
		{ name: 'My social contracts', icon: HomeOutline, href: '/contracts' },
		{ name: 'My identities', icon: UsersOutline, href: '/identities' },
	];

	// Create combined navigation items with core items and extensions
	$: posts = [
		...coreNavItems,
		// Dynamically add extensions
		...extensions.map(ext => ({
			name: ext.name,
			icon: getIcon(ext.icon, WalletSolid),
			href: `/extensions/${ext.id}`
		}))
	];

	let links = [
		// {
		// 	label: 'GitHub Repository',
		// 	href: 'https://github.com/themesberg/flowbite-svelte-admin-dashboard',
		// 	icon: GithubSolid
		// },
		// {
		// 	label: 'Flowbite Svelte',
		// 	href: 'https://flowbite-svelte.com/docs/pages/quickstart',
		// 	icon: ClipboardListSolid
		// },
		// {
		// 	label: 'Components',
		// 	href: 'https://flowbite-svelte.com/docs/components/accordion',
		// 	icon: LayersSolid
		// },
		// {
		// 	label: 'Support',
		// 	href: 'https://github.com/themesberg/flowbite-svelte-admin-dashboard/issues',
		// 	icon: LifeSaverSolid
		// }
	];
	
	// Make dropdowns reactive based on posts
	$: dropdowns = posts ? Object.fromEntries(posts.map((post, index) => [index, false])) : {};
</script>

<Sidebar
	class={drawerHidden ? 'hidden' : ''}
	activeUrl={mainSidebarUrl}
	activeClass="bg-gray-100 dark:bg-gray-700"
	asideClass="fixed inset-0 z-30 flex-none h-full w-64 lg:h-auto border-e border-gray-200 dark:border-gray-600 lg:overflow-y-visible lg:pt-16 lg:block"
>
	<h4 class="sr-only">Main menu</h4>
	<SidebarWrapper
		divClass="overflow-y-auto px-3 pt-20 lg:pt-5 h-full bg-white scrolling-touch max-w-2xs lg:h-[calc(100vh-4rem)] lg:block dark:bg-gray-800 lg:me-0 lg:sticky top-2"
	>
		<nav class="divide-y divide-gray-200 dark:divide-gray-700">
			<SidebarGroup ulClass={groupClass} class="mb-3">
				{#each posts as { name, icon, children, href }, index}
					{#if children}
						<SidebarDropdownWrapper bind:isOpen={dropdowns[index]} label={name} class="pr-3">
							<AngleDownOutline slot="arrowdown" strokeWidth="3.3" size="sm" />
							<AngleUpOutline slot="arrowup" strokeWidth="3.3" size="sm" />
							<svelte:component this={icon} slot="icon" class={iconClass} />

							{#each Object.entries(children) as [title, href]}
								<SidebarItem label={title} {href} spanClass="ml-9" class={itemClass} />
							{/each}
						</SidebarDropdownWrapper>
					{:else}
						<SidebarItem label={name} {href} spanClass="ml-3" class={itemClass}>
							<svelte:component this={icon} slot="icon" class={iconClass} />
						</SidebarItem>
					{/if}
				{/each}
			</SidebarGroup>
			<SidebarGroup ulClass={groupClass}>
				{#each links as { label, href, icon } (label)}
					<SidebarItem {label} {href} spanClass="ml-3" class={itemClass} target="_blank">
						<svelte:component this={icon} slot="icon" class={iconClass} />
					</SidebarItem>
				{/each}
			</SidebarGroup>
		</nav>
	</SidebarWrapper>
</Sidebar>

<div
	hidden={drawerHidden}
	class="fixed inset-0 z-20 bg-gray-900/50 dark:bg-gray-900/60"
	on:click={closeDrawer}
	on:keydown={closeDrawer}
	role="presentation"
></div>
