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
	import { type ExtensionMetadata } from '$lib/extensions';
	import { getIcon } from '$lib/utils/iconMap';
	// Import user profiles store
	import { userProfiles } from '$lib/stores/profiles';
	// Import backend for extension loading
	import { backend } from '$lib/canisters';
	
	// Import i18n functionality
	import { _, locale, isLoading, getLocaleFromNavigator } from 'svelte-i18n';
	import { onMount } from 'svelte';
	
	// Import theme utilities
	import { styles, cn } from '$lib/theme/utilities';

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

	// Use theme utilities for consistent styling
	let iconClass = styles.sidebar.icon();
	let itemClass = styles.sidebar.item();
	let groupClass = 'pt-2 space-y-2';

	$: mainSidebarUrl = $page.url.pathname;
	let activeMainSidebar: string;

	afterNavigate((navigation) => {
		// this fixes https://github.com/themesberg/flowbite-svelte/issues/364
		document.getElementById('svelte')?.scrollTo({ top: 0 });
		closeDrawer();

		activeMainSidebar = navigation.to?.url.pathname ?? '';
	});

	// Get all extensions from backend instead of filesystem
	let extensions: ExtensionMetadata[] = [];
	let extensionsLoaded = false;

	async function loadExtensionsFromBackend() {
		try {
			console.log('Calling backend.get_extensions()...');
			const response = await backend.get_extensions();
			console.log('Backend response:', response);
			console.log('Response type:', typeof response);
			console.log('Response success:', response?.success);
			console.log('Response data:', response?.data);
			
			if (response.success && response.data.ExtensionsList) {
				console.log('Extensions list:', response.data.ExtensionsList.extensions);
				const extensionData = response.data.ExtensionsList.extensions.map(ext => JSON.parse(ext));
				console.log('Parsed extension data:', extensionData);
				
				extensions = extensionData.map(ext => ({
					id: ext.name,
					name: ext.name,
					description: ext.description,
					version: ext.version,
					icon: ext.icon,
					author: ext.author,
					permissions: ext.required_permissions || ext.permissions || [],
					enabled: true,
					profiles: ext.profiles || [],
					categories: ext.categories || ['other']
				}));
				console.log('Mapped extensions:', extensions);
				extensionsLoaded = true;
			} else {
				console.log('Invalid response format or no extensions data');
				extensions = [];
				extensionsLoaded = true;
			}
		} catch (error) {
			console.error('Error loading extensions from backend:', error);
			extensions = [];
			extensionsLoaded = true;
		}
	}

	// Load extensions on component mount
	onMount(() => {
		loadExtensionsFromBackend();
	});
	
	// Filter extensions based on their manifest profiles and enabled status
	function filterExtensionsForSidebar(extensions: ExtensionMetadata[], userProfiles: string[]): ExtensionMetadata[] {
		if (!extensionsLoaded) return [];
		return extensions.filter(ext => {
			// Skip if extension is not enabled
			if (ext.enabled === false) return false;
			
			// If no profiles specified in extension manifest, show to all users
			if (!ext.profiles || !Array.isArray(ext.profiles) || ext.profiles.length === 0) {
				return true;
			}
			
			// Check if current user has any of the profiles required by the extension
			return ext.profiles.some((profile: string) => userProfiles.includes(profile));
		});
	}

	// Core navigation items with translation keys
	const coreNavItems: NavItemWithHref[] = [
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
	let filteredExtensions: ExtensionMetadata[] = [];
	$: filteredExtensions = filterExtensionsForSidebar(extensions, $userProfiles);

	// Group extensions by categories
	$: extensionsByCategory = (() => {
		const categories: Record<string, ExtensionMetadata[]> = {};
		
		filteredExtensions.forEach(ext => {
			// Get categories from manifest, default to 'other' if none specified
			const extCategories = ext.categories || ['other'];
			
			extCategories.forEach(category => {
				if (!categories[category]) {
					categories[category] = [];
				}
				categories[category].push(ext);
			});
		});
		
		return categories;
	})();

	// Create navigation items for each category
	$: categorizedNavItems = (() => {
		const result: Record<string, NavItemWithHref[]> = {};
		
		Object.entries(extensionsByCategory).forEach(([category, exts]) => {
			result[category] = exts
				.filter(ext => {
					// Exclude extensions that are handled separately or have special logic
					const excluded = [
						'demo_loader',
						'test_bench'
					];
					return !excluded.includes(ext.id);
				})
				.map(ext => {
					// Handle special cases with translation keys
					if (ext.id === 'public_dashboard') {
						return {
							translationKey: 'extensions.public_dashboard.sidebar',
							icon: getIcon(ext.icon) || ChartPieOutline,
							href: `/extensions/${ext.id}`
						};
					}
					if (ext.id === 'citizen_dashboard') {
						return {
							translationKey: 'extensions.citizen_dashboard.sidebar',
							icon: getIcon(ext.icon) || RectangleListSolid,
							href: `/extensions/${ext.id}`
						};
					}
					if (ext.id === 'vault_manager') {
						return {
							translationKey: 'extensions.vault_manager.sidebar',
							icon: getIcon(ext.icon) || WalletSolid,
							href: `/extensions/${ext.id}`
						};
					}
					if (ext.id === 'notifications') {
						return {
							translationKey: 'extensions.notifications.sidebar',
							icon: getIcon(ext.icon) || LifeSaverSolid,
							href: `/extensions/${ext.id}`
						};
					}
					
					// Default case for other extensions
					return {
						name: ext.name || ext.id,
						icon: getIcon(ext.icon) || LayersSolid,
						href: `/extensions/${ext.id}`
					};
				});
		});
		
		return result;
	})();

	// Function to format category names for display
	function formatCategoryName(category: string): string {
		return category
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	// Marketplace item for admin users
	const marketplaceItem: NavItemWithHref = {
		name: $_('navigation.extensions_marketplace') || 'Extensions Marketplace',
		icon: WandMagicSparklesOutline,
		href: '/extensions'
	};


	let links: Link[] = [
		// External links removed for brevity
	];
	
	// Make dropdowns reactive based on core nav items
	$: dropdowns = filteredCoreNavItems ? Object.fromEntries(filteredCoreNavItems.map((item, index) => [index, false])) : {};

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
	asideClass="fixed inset-0 z-30 flex-none h-full w-64 lg:h-auto lg:top-16 border-e border-gray-200 dark:border-gray-600 lg:overflow-y-visible lg:pt-0 lg:block"
>
	<h4 class="sr-only">{$_('common.main_menu')}</h4>
	<SidebarWrapper
		divClass={cn(styles.sidebar.container(), "overflow-y-auto h-full px-3 pb-4")}
		asideClass="fixed top-0 left-0 z-40 w-64 h-screen pt-14 transition-transform border-r lg:translate-x-0 {styles.sidebar.container()} {drawerHidden ? '-translate-x-full' : ''}"
	>
			<nav class="divide-y divide-gray-200 dark:divide-gray-700">
				<!-- Core Navigation Items -->
				<SidebarGroup ulClass={groupClass} class="mb-3">
					{#each filteredCoreNavItems as { name, translationKey, icon, href }}
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
					{/each}
				</SidebarGroup>

				<!-- Categorized Extension Items -->
				{#each Object.entries(categorizedNavItems) as [category, items]}
					{#if items.length > 0}
						<SidebarGroup ulClass={groupClass} class="mb-3">
							<!-- Category Header -->
							<li class="px-3 py-2">
								<h3 class={styles.sidebar.categoryHeader()}>
									{formatCategoryName(category)}
								</h3>
							</li>
							
							<!-- Category Items -->
							{#each items as { name, translationKey, icon, href }}
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
							{/each}
						</SidebarGroup>
					{/if}
				{/each}

				<!-- Admin-only Extensions Marketplace -->
				{#if $userProfiles && $userProfiles.includes('admin')}
					<SidebarGroup ulClass={groupClass}>
						<SidebarItem label={marketplaceItem.name} href={marketplaceItem.href} spanClass="ml-3" class={itemClass}>
							<svelte:component this={marketplaceItem.icon} slot="icon" class={iconClass} />
						</SidebarItem>
					</SidebarGroup>
				{/if}

				<!-- External Links -->
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
