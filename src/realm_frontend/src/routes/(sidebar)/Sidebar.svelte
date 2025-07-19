<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import type { SvelteComponent } from 'svelte';

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
		WalletSolid,
		ObjectsColumnOutline
	} from 'flowbite-svelte-icons';
	
	// Import extension system
	import { getAllExtensions, type ExtensionMetadata } from '$lib/extensions';
	import { getIcon } from '$lib/utils/iconMap';
	// Import user profiles store
	import { userProfiles } from '$lib/stores/profiles';
	
	// Import i18n functionality
	import { _, locale, isLoading, getLocaleFromNavigator } from 'svelte-i18n';
	import { onMount } from 'svelte';

	export let drawerHidden: boolean = false;

	$: {
		if ($locale) {
			console.log('Sidebar: Current locale:', $locale);
			// Debug translation for Vault Manager
			const vaultManagerTranslation = $_('extensions.vault_manager.sidebar');
			console.log('Sidebar: Vault Manager translation key result:', vaultManagerTranslation);
		}
	}

	const closeDrawer = () => {
		drawerHidden = true;
	};
	
	// Function to check if a URL is an extension link
	function isExtensionLink(href: string | undefined): boolean {
		if (!href) return false;
		return href.startsWith('/extensions/') && href !== '/extensions';
	}
	
	// Define types for navigation items
	type NavItemWithHref = {
		name?: string;
		translationKey?: string; // Added translation key property for i18n
		icon: typeof TableColumnSolid;
		href: string;
		children?: never;
		// Add profile restrictions
		profiles?: string[];
	};
	
	type NavItemWithChildren = {
		name: string;
		icon: typeof TableColumnSolid; 
		children: Record<string, string>;
		href?: never;
		// Add profile restrictions
		profiles?: string[];
	};
	
	type NavItem = NavItemWithHref | NavItemWithChildren;
	
	type Link = {
		label: string;
		href: string;
		icon: typeof TableColumnSolid;
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
	
	// Filter extensions based on their manifest profiles and enabled status
	function filterExtensionsForSidebar(extensions: ExtensionMetadata[]): ExtensionMetadata[] {
		return extensions.filter(ext => {
			// Skip if extension is not enabled
			if (ext.enabled === false) return false;
			
			// If no profiles specified in extension manifest, show to all users
			if (!ext.profiles || !Array.isArray(ext.profiles) || ext.profiles.length === 0) return true;
			
			// Check if current user has any of the profiles required by the extension
			return ext.profiles.some((profile: string) => $userProfiles.includes(profile));
		});
	}

	// Core navigation items with translation keys
	const coreNavItems: NavItemWithHref[] = [
		{ translationKey: 'extensions.public_dashboard.sidebar', icon: ChartPieOutline, href: '/extensions/public_dashboard' }, // For all users
		{ name: $_('common.identities') || 'My Identities', icon: UsersOutline, href: '/identities' }, // For all users
		{ name: $_('navigation.admin_dashboard') || 'Admin Dashboard', icon: TableColumnSolid, href: '/ggg', profiles: ['admin'] }, // Admin only
		{ name: $_('common.settings'), icon: CogOutline, href: '/settings' }, // For all users
	];

	// Filter core navigation items based on user profiles
	$: filteredCoreNavItems = coreNavItems.filter(item => {
		// If no profiles are available, only show Dashboard
		if (!$userProfiles || $userProfiles.length === 0) {
			return item.name === $_('navigation.dashboard');
		}
		
		// If no profiles restriction on the item, show to everyone with a profile
		if (!item.profiles || !item.profiles.length) return true;
		
		// Check if user has any of the required profiles
		return item.profiles.some(profile => $userProfiles.includes(profile));
	});

	// Filter extensions based on user profiles and create menu items
	$: filteredExtensions = filterExtensionsForSidebar(extensions);

	// Create individual menu items for extensions instead of dropdown
	// Exclude vault_manager and public_dashboard since they're handled separately with translation keys
	$: extensionItems = filteredExtensions
		.filter(ext => ext.id !== 'vault_manager' && ext.id !== 'public_dashboard')
		.map(ext => ({
			name: ext.name,
			icon: getIcon(ext.icon) || TableColumnSolid,
			href: `/extensions/${ext.id}`
		}));

	// Extensions Marketplace (admin only)
	const marketplaceItem = { 
		name: $_('navigation.extensions_marketplace') || 'Extensions Marketplace', 
		icon: LayersSolid, 
		href: '/extensions',
		profiles: ['admin']
	};

	// Create combined navigation items with filtered core items and extensions as separate items
	let posts: NavItem[];
	$: posts = [
		...filteredCoreNavItems,
		// Only show Extensions items if user has profiles and there are valid extensions
		...($userProfiles && $userProfiles.length > 0 && extensionItems.length > 0 ? extensionItems : []),
		// Only show Extensions Marketplace for admin
		...($userProfiles && $userProfiles.includes('admin') ? [marketplaceItem] : [])
	];

	// Special case for Citizen Dashboard extension (for members)
	$: {
		const citizenDashboardExt = extensions.find((ext: ExtensionMetadata) => ext.id === 'citizen_dashboard');
		if (citizenDashboardExt && $userProfiles && $userProfiles.includes('member')) {
			// Make sure it's not already in the list
			const existingIndex = posts.findIndex(item => item.href === `/extensions/${citizenDashboardExt.id}`);
			if (existingIndex === -1) {
				posts = [
					...posts, 
					{ 
						name: $_('navigation.citizen_dashboard') || 'Citizen Dashboard', 
						icon: getIcon(citizenDashboardExt.icon) || TableColumnSolid, 
						href: `/extensions/${citizenDashboardExt.id}` 
					}
				];
			}
		}
	}
	
	// Special case for Vault Manager extension (for admin)
	$: {
		const vaultManagerExt = extensions.find((ext: ExtensionMetadata) => ext.id === 'vault_manager');
		if (vaultManagerExt && $userProfiles && $userProfiles.includes('admin')) {
			// Make sure it's not already in the list
			const existingIndex = posts.findIndex(item => item.href === `/extensions/${vaultManagerExt.id}`);
			if (existingIndex === -1) {
				console.log('Vault Manager extension found for admin');
				console.log('Current locale when adding to posts:', $locale);
				
				// Using standard reactive Svelte approach for translations
				posts = [
					...posts, 
					{ 
						// Store the translation key instead of the translated value
						translationKey: 'extensions.vault_manager.sidebar',
						icon: getIcon(vaultManagerExt.icon) || WalletSolid, 
						href: `/extensions/${vaultManagerExt.id}` 
					}
				];
			}
		}
	}

	let links: Link[] = [
		// External links removed for brevity
	];
	
	// Make dropdowns reactive based on posts
	$: dropdowns = posts ? Object.fromEntries(posts.map((post, index) => [index, false])) : {};

	afterNavigate((navigation) => {
		// this fixes https://github.com/themesberg/flowbite-svelte/issues/364
		document.getElementById('svelte')?.scrollTo({ top: 0 });
		closeDrawer();
	});
</script>

<Sidebar
	class={drawerHidden ? 'hidden' : ''}
	activeUrl={mainSidebarUrl}
	activeClass="bg-gray-100 dark:bg-gray-700"
	asideClass="fixed inset-0 z-30 flex-none h-full w-64 lg:h-auto border-e border-gray-200 dark:border-gray-600 lg:overflow-y-visible lg:pt-16 lg:block"
>
	<h4 class="sr-only">{$_('common.main_menu')}</h4>
	<SidebarWrapper
		divClass="overflow-y-auto h-full bg-white px-3 pb-4 dark:bg-gray-800"
		asideClass="fixed top-0 left-0 z-40 w-64 h-screen pt-14 transition-transform border-r lg:translate-x-0 bg-white border-gray-200 dark:bg-gray-800 dark:border-gray-700 {drawerHidden ? '-translate-x-full' : ''}"
	>
		>
			<nav class="divide-y divide-gray-200 dark:divide-gray-700">
				<SidebarGroup ulClass={groupClass} class="mb-3">
					{#each posts as { name, translationKey, icon, children, href }, index}
						{#if href && href.includes('vault_manager')}
							{console.log('Vault Manager item:', { name, translationKey, href })}
						{/if}
						{#if href && href.includes('public_dashboard')}
							{console.log('Public Dashboard item:', { name, translationKey, href })}
						{/if}
						{#if children}
							<SidebarDropdownWrapper bind:isOpen={dropdowns[index]} label={name} class="pr-3">
								<AngleDownOutline slot="arrowdown" strokeWidth="3.3" size="sm" />
								<AngleUpOutline slot="arrowup" strokeWidth="3.3" size="sm" />
								<svelte:component this={icon} slot="icon" class={iconClass} />

								{#each Object.entries(children) as [title, href]}
									{#if isExtensionLink(href?.toString())}
										<!-- Use classic browser navigation for extension links -->
										<li>
											<a 
												href={href.toString()} 
												data-sveltekit-reload 
												class={itemClass} 
												on:click={closeDrawer}
											>
												<span class="ml-9">{$_(title)}</span>
											</a>
										</li>
									{:else}
										<SidebarItem label={$_(title)} href={href.toString()} spanClass="ml-9" class={itemClass} />
									{/if}
								{/each}
							</SidebarDropdownWrapper>
						{:else}
							{#if isExtensionLink(href)}
								<!-- Use classic browser navigation for extension links -->
								<li>
									<a 
										href={href} 
										data-sveltekit-reload 
										class={itemClass} 
										on:click={closeDrawer}
									>
										<svelte:component this={icon} class={iconClass} />
										<span class="ml-3">{translationKey ? $_(translationKey) : name}</span>
									</a>
								</li>
							{:else}
								<SidebarItem label={name} {href} spanClass="ml-3" class={itemClass}>
									<svelte:component this={icon} slot="icon" class={iconClass} />
								</SidebarItem>
							{/if}
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
	class="fixed inset-0 z-20 bg-gray-900/50 dark:bg-gray-900/60 lg:hidden"
	on:click={closeDrawer}
	on:keydown={closeDrawer}
	role="presentation"
></div>
