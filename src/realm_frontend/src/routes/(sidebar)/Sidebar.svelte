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
		ObjectsColumnOutline,

		FingerprintOutline

	} from 'flowbite-svelte-icons';
	
	// Import extension system
	import { type ExtensionMetadata } from '$lib/extensions';
	
	// Extend ExtensionMetadata to include path field and other properties
	interface ExtensionMetadataWithPath extends ExtensionMetadata {
		path?: string | null;
		url_path?: string | null;
		categories?: string[];
		profiles?: string[];
		doc_url?: string;
		show_in_sidebar?: boolean;
		enabled?: boolean;
	}
	import { getIcon } from '$lib/utils/iconMap';
	// Import user profiles store
	import { userProfiles, profilesLoading } from '$lib/stores/profiles';
	// Import authentication store
	// @ts-ignore
	import { isAuthenticated } from '$lib/stores/auth';
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
	let extensions: ExtensionMetadataWithPath[] = [];
	let extensionsLoaded = false;
	let extensionsLoading = false;

	async function loadExtensionsFromBackend() {
		extensionsLoading = true;
		try {
			console.log('Calling backend.get_extensions()...');
			const response = await backend.get_extensions();
			console.log('Backend response:', response);
			console.log('Response type:', typeof response);
			console.log('Response success:', response?.success);
			console.log('Response data:', response?.data);
			
			if (response.success && response.data.extensionsList) {
				console.log('Extensions list:', response.data.extensionsList.extensions);
				const extensionData = response.data.extensionsList.extensions.map(ext => JSON.parse(ext));
				console.log('Raw extension data:', extensionData);
				
				extensions = extensionData.map(ext => ({
					id: ext.name,
					name: ext.name,
					icon: ext.icon,
					url_path: ext.url_path,
					categories: ext.categories || ['other'],
					profiles: ext.profiles || [],
					show_in_sidebar: ext.show_in_sidebar !== false
				}));
				console.log('Processed extensions:', extensions);
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
		} finally {
			extensionsLoading = false;
		}
	}

	// Load extensions on component mount
	onMount(() => {
		loadExtensionsFromBackend();
	});
	
	/**
	 * SIDEBAR EXTENSION FILTERING RULES
	 * 
	 * This function implements the following filtering logic for sidebar extension visibility:
	 * 
	 * 1. SHOW_IN_SIDEBAR CHECK:
	 *    - If show_in_sidebar is false, do not show the extension icon in the sidebar
	 * 
	 * 2. UNAUTHENTICATED USERS (neither admin nor member):
	 *    - Only show llm_chat extension (AI Assistant) and Public Dashboard
	 * 
	 * 3. MEMBER USERS:
	 *    - Show extensions that contain "member" among the list of values of the "profiles" attribute in manifest
	 * 
	 * 4. ADMIN USERS:
	 *    - Show extensions that contain "admin" among the list of values of the "profiles" attribute in manifest
	 * 
	 * 5. ADDITIONAL FILTERS:
	 *    - Skip if extension is explicitly disabled (enabled: false)
	 *    - Skip if path is explicitly set to null (hide from sidebar)
	 */
	function filterExtensionsForSidebar(extensions: ExtensionMetadataWithPath[], userProfiles: string[]): ExtensionMetadataWithPath[] {
		if (!extensionsLoaded) {
			console.log('Extensions not loaded yet, returning empty array');
			return [];
		}
		console.log('Filtering extensions:', extensions.length, 'User profiles:', userProfiles);
		
		return extensions.filter(ext => {
			console.log('Checking extension:', ext.name, 'enabled:', ext.enabled, 'show_in_sidebar:', ext.show_in_sidebar, 'profiles:', ext.profiles);
			
			// Skip if extension is not enabled
			if (ext.enabled === false) return false;
			
			// RULE 1: Skip if show_in_sidebar is explicitly set to false
			if (ext.show_in_sidebar === false) return false;
			
			// Note: url_path can be null (which means use default /extensions/{name} route)
			// We don't filter based on url_path being null
			
			// RULE 2: If user is neither admin nor member, only show llm_chat and public_dashboard
			if (!userProfiles || userProfiles.length === 0 || 
				(!userProfiles.includes('admin') && !userProfiles.includes('member'))) {
				const allowedForUnauthenticated = ['llm_chat', 'public_dashboard'];
				const isAllowed = allowedForUnauthenticated.includes(ext.name);
				console.log('Unauthenticated user - extension allowed:', isAllowed);
				return isAllowed;
			}
			
			// If no profiles specified in extension manifest, show to all authenticated users
			if (!ext.profiles || !Array.isArray(ext.profiles) || ext.profiles.length === 0) {
				console.log('Extension has no profile restrictions, showing to authenticated users');
				return true;
			}
			
			// RULE 3 & 4: Check if current user has any of the profiles required by the extension
			const hasProfile = ext.profiles.some((profile: string) => userProfiles.includes(profile));
			console.log('Profile check result:', hasProfile);
			return hasProfile;
		});
	}

	// Core navigation items with translation keys
	const coreNavItems: NavItemWithHref[] = [
		{ name: $_('common.identities') || 'My Identities', icon: FingerprintOutline, href: '/identities' }, // For all users
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
	let filteredExtensions: ExtensionMetadataWithPath[] = [];
	
	// Reactive statement with explicit dependency tracking
	$: {
		console.log('=== SIDEBAR REACTIVE UPDATE ===');
		console.log('extensionsLoaded:', extensionsLoaded);
		console.log('profilesLoading:', $profilesLoading);
		console.log('userProfiles:', $userProfiles);
		console.log('extensions count:', extensions.length);
		console.log('raw extensions:', extensions);
		
		if (extensionsLoaded && !$profilesLoading) {
			console.log('Both extensions and profiles are ready, filtering...');
			filteredExtensions = filterExtensionsForSidebar(extensions, $userProfiles);
			console.log('Filtered extensions result:', filteredExtensions);
		} else {
			console.log('Waiting for data - extensionsLoaded:', extensionsLoaded, 'profilesLoading:', $profilesLoading);
			filteredExtensions = [];
		}
	}

	// Group extensions by categories
	$: extensionsByCategory = (() => {
		const categories: Record<string, ExtensionMetadataWithPath[]> = {};
		
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
		console.log('=== CREATING CATEGORIZED NAV ITEMS ===');
		console.log('extensionsByCategory:', extensionsByCategory);
		
		const result: Record<string, NavItemWithHref[]> = {};
		
		Object.entries(extensionsByCategory).forEach(([category, exts]) => {
			console.log(`Processing category: ${category}, extensions:`, exts);
			result[category] = exts
				.filter(ext => {
					// Exclude extensions that are handled separately or have special logic
					const excluded = [
						'demo_loader',
						'test_bench'
					];
					const isExcluded = excluded.includes(ext.id);
					console.log(`Extension ${ext.id} excluded:`, isExcluded);
					return !isExcluded;
				})
				.map(ext => {
					console.log(`Mapping extension ${ext.id}:`, ext);
					// Determine href based on url_path field (new manifest schema)
					let href: string;
					if (ext.url_path === undefined || ext.url_path === null) {
						// Default behavior: use extensions/<extension_id> route
						href = `/extensions/${ext.id}`;
					} else {
						// Use custom path from url_path field
						href = `/${ext.url_path}`;
					}
					
					// Consistent handling for all extensions
					const iconComponent = getIcon(ext.icon) || LayersSolid;
					console.log(`Extension ${ext.id}: icon="${ext.icon}", resolved to:`, iconComponent);
					console.log(`Extension ${ext.id}: href="${href}"`);
					
					const navItem = {
						translationKey: `extensions.${ext.id}.sidebar`,
						name: ext.name || ext.id, // Fallback if translation doesn't exist
						icon: iconComponent,
						href
					};
					console.log(`Created nav item for ${ext.id}:`, navItem);
					return navItem;
				});
		});
		
		console.log('Final categorized nav items:', result);
		return result;
	})();

	function formatCategoryName(category: string): string {
		return category
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

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
				<SidebarGroup ulClass={groupClass} class="mb-3 pt-5 lg:pt-0">
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

				<!-- Loading State -->
				{#if extensionsLoading || $profilesLoading}
					<SidebarGroup ulClass={groupClass} class="mb-3">
						<li class="px-3 py-2 flex items-center">
							<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900 dark:border-gray-100"></div>
						</li>
					</SidebarGroup>
				{/if}

				<!-- Categorized Extension Items -->
				{#each ['public_services', 'finances', 'oversight', 'other'] as category}
					{@const items = categorizedNavItems[category] || []}
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
