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
		// Layered Realm extras (Issue #168) — populated by get_sidebar_manifests()
		// or back-filled from list_runtime_extensions for runtime entries.
		version?: string;
		sidebar_label?: Record<string, string> | string | null;
		kind?: 'runtime' | 'bundled';
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
	
	let showScrollIndicator = true;
	let sidebarContainer: HTMLElement;
	
	$: {
		if ($locale) {
			console.log('Sidebar: Current locale:', $locale);
		}
	}
	
	function checkScrollPosition() {
		if (sidebarContainer) {
			const { scrollTop, scrollHeight, clientHeight } = sidebarContainer;
			showScrollIndicator = scrollTop + clientHeight < scrollHeight - 20;
		}
	}
	
	onMount(() => {
		// Find the scrollable sidebar div after component mounts
		setTimeout(() => {
			const sidebar = document.querySelector('aside.fixed');
			if (sidebar) {
				const scrollDiv = sidebar.querySelector('.overflow-y-auto');
				if (scrollDiv) {
					sidebarContainer = scrollDiv as HTMLElement;
					sidebarContainer.addEventListener('scroll', checkScrollPosition);
					checkScrollPosition(); // Initial check
				}
			}
		}, 100);
		
		return () => {
			if (sidebarContainer) {
				sidebarContainer.removeEventListener('scroll', checkScrollPosition);
			}
		};
	});
	
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
		// Note: Do not close drawer here - sidebar state is persisted
		activeMainSidebar = navigation.to?.url.pathname ?? '';
	});

	// ---------------------------------------------------------------------
	// Sidebar data source — unified across bundled + runtime extensions
	// ---------------------------------------------------------------------
	// Issue #168 (Layered Realm): the sidebar gets ALL extension metadata
	// from realm_backend.get_sidebar_manifests(), which returns a single
	// shape regardless of whether an extension is baked into the WASM
	// ("bundled") or installed at runtime from file_registry ("runtime").
	//
	// This means the sidebar code does not need to special-case runtime
	// extensions. It also means an operator can flip a realm from bundled
	// to layered without ANY frontend changes — only the install method
	// changes; the metadata contract is identical.
	//
	// For older realm_backend WASMs that don't yet expose this method,
	// we fall back to the previous code paths (get_extensions() for
	// bundled, list_runtime_extensions() for runtime) so the sidebar
	// keeps working during the rollout window.
	let extensions: ExtensionMetadataWithPath[] = [];
	let extensionsLoaded = false;
	let extensionsLoading = false;

	function manifestEntryToExtension(entry: any): ExtensionMetadataWithPath {
		return {
			id: entry.id,
			name: entry.name ?? entry.id,
			icon: entry.icon,
			url_path: entry.url_path ?? null,
			categories: Array.isArray(entry.categories) && entry.categories.length > 0
				? entry.categories
				: ['other'],
			profiles: Array.isArray(entry.profiles) ? entry.profiles : [],
			show_in_sidebar: entry.show_in_sidebar !== false,
			// Carry version + sidebar_label + kind through so we can render
			// nicer tooltips and use localized labels below.
			...(entry.version ? { version: entry.version } : {}),
			...(entry.sidebar_label ? { sidebar_label: entry.sidebar_label } : {}),
			...(entry.kind ? { kind: entry.kind } : {}),
		} as any;
	}

	async function loadFromGetSidebarManifests(): Promise<boolean> {
		const fn = (backend as any)?.get_sidebar_manifests;
		if (typeof fn !== 'function') return false;
		try {
			const raw = await fn.call(backend);
			const parsed = JSON.parse(raw);
			if (!parsed?.success || !Array.isArray(parsed.manifests)) {
				return false;
			}
			extensions = parsed.manifests.map(manifestEntryToExtension);
			console.log(
				'[Sidebar] get_sidebar_manifests →',
				extensions.length,
				'entries (',
				extensions.filter((e: any) => e.kind === 'runtime').length,
				'runtime,',
				extensions.filter((e: any) => e.kind !== 'runtime').length,
				'bundled )',
			);
			return true;
		} catch (e) {
			console.warn('[Sidebar] get_sidebar_manifests failed, will fall back:', e);
			return false;
		}
	}

	async function loadFromLegacyEndpoints(): Promise<void> {
		// Bundled extensions (legacy realm_backend without get_sidebar_manifests).
		const bundled: ExtensionMetadataWithPath[] = [];
		try {
			const response = await backend.get_extensions();
			if (response?.success && response.data?.extensionsList) {
				const extensionData = response.data.extensionsList.extensions.map(
					(ext: string) => JSON.parse(ext),
				);
				for (const ext of extensionData) {
					bundled.push({
						id: ext.name,
						name: ext.name,
						icon: ext.icon,
						url_path: ext.url_path,
						categories: ext.categories || ['other'],
						profiles: ext.profiles || [],
						show_in_sidebar: ext.show_in_sidebar !== false,
						...(ext.kind ? { kind: ext.kind } : { kind: 'bundled' }),
					} as any);
				}
			}
		} catch (e) {
			console.warn('[Sidebar] get_extensions() fallback failed:', e);
		}

		// Runtime extensions (still loaded from list_runtime_extensions on legacy).
		const runtime: ExtensionMetadataWithPath[] = [];
		try {
			const raw = await (backend as any).list_runtime_extensions();
			const parsed = JSON.parse(raw);
			if (parsed?.success) {
				const ids: string[] = parsed.runtime_extensions ?? [];
				const manifests: Record<string, any> = parsed.all_manifests ?? {};
				for (const id of ids) {
					const m = manifests?.[id] ?? {};
					runtime.push(
						manifestEntryToExtension({
							id,
							name: m.name ?? id,
							version: m.version,
							icon: m.icon,
							url_path: m.url_path,
							categories: m.categories,
							profiles: m.profiles,
							show_in_sidebar: m.show_in_sidebar,
							sidebar_label: m.sidebar_label,
							kind: 'runtime',
						}),
					);
				}
			}
		} catch (e) {
			console.warn('[Sidebar] list_runtime_extensions fallback failed:', e);
		}

		// Runtime takes precedence over bundled with the same id.
		const byId = new Map<string, ExtensionMetadataWithPath>();
		for (const e of bundled) byId.set(e.id as string, e);
		for (const e of runtime) byId.set(e.id as string, e);
		extensions = Array.from(byId.values());
	}

	async function loadSidebarExtensions() {
		extensionsLoading = true;
		try {
			const ok = await loadFromGetSidebarManifests();
			if (!ok) {
				console.log('[Sidebar] Falling back to legacy get_extensions + list_runtime_extensions');
				await loadFromLegacyEndpoints();
			}
			extensionsLoaded = true;
		} catch (e) {
			console.error('[Sidebar] Failed to load extensions:', e);
			extensions = [];
			extensionsLoaded = true;
		} finally {
			extensionsLoading = false;
		}
	}

	onMount(() => {
		loadSidebarExtensions();
		// Re-load when an extension is installed or uninstalled at runtime
		// (e.g. via the package_manager extension), so the new entry appears
		// without a full page reload. Components dispatch this event after
		// a successful install_*/uninstall_* call.
		const onChanged = () => {
			console.log('[Sidebar] realms:extensions-changed → reloading manifests');
			loadSidebarExtensions();
		};
		if (typeof window !== 'undefined') {
			window.addEventListener('realms:extensions-changed', onChanged);
		}
		return () => {
			if (typeof window !== 'undefined') {
				window.removeEventListener('realms:extensions-changed', onChanged);
			}
		};
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

					// Resolve a display label, in this order:
					//   1) manifest.sidebar_label[currentLocale] (or "en" or first key)
					//   2) i18n key extensions.<id>.sidebar (legacy bundled-style)
					//   3) manifest.name
					//   4) ext.id
					let inlineLabel: string | undefined;
					const sl = ext.sidebar_label as any;
					if (sl) {
						if (typeof sl === 'string') {
							inlineLabel = sl;
						} else if (typeof sl === 'object') {
							const cur = ($locale ?? 'en') as string;
							inlineLabel =
								sl[cur] ??
								sl[cur.split('-')[0]] ??
								sl.en ??
								sl[Object.keys(sl)[0]];
						}
					}

					const navItem = {
						translationKey: inlineLabel ? undefined : `extensions.${ext.id}.sidebar`,
						name: inlineLabel ?? ext.name ?? ext.id,
						icon: iconComponent,
						href,
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
		// Note: Do not close drawer here - state is persisted via localStorage
	});
</script>

<Sidebar
	class=""
	activeUrl={mainSidebarUrl}
	activeClass="bg-gray-50 dark:bg-gray-700"
	asideClass="fixed top-0 left-0 z-40 flex-none h-[calc(100vh-4rem)] w-64 mt-16 border-r border-gray-200 dark:border-gray-600 transition-transform duration-500 ease-in-out {drawerHidden ? '-translate-x-full' : 'translate-x-0'}"
>
	<h4 class="sr-only">{$_('common.main_menu')}</h4>
	<SidebarWrapper
		divClass={cn(styles.sidebar.container(), "overflow-y-auto h-full px-3 pb-12 scrollbar-hide overscroll-contain")}
		asideClass=""
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


				<!--
					NOTE: Runtime extensions used to render in their own
					"Runtime Extensions" group here. With Layered Realm
					(Issue #168) they are now indistinguishable from
					bundled ones at the sidebar level — they appear in
					their proper category above, sourced from the same
					get_sidebar_manifests() call.
				-->

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
	<!-- Fixed scroll indicator at bottom of sidebar -->
	{#if showScrollIndicator}
		<div class="absolute bottom-0 left-0 right-0 h-12 pointer-events-none bg-gradient-to-t from-white to-transparent flex items-end justify-center pb-2">
			<span class="text-gray-400 text-lg animate-bounce">⌄</span>
		</div>
	{/if}
</Sidebar>

<div
	hidden={drawerHidden}
	class="fixed inset-0 z-20 bg-gray-900/50 dark:bg-gray-900/60 lg:hidden touch-none overscroll-none"
	on:click={closeDrawer}
	on:keydown={closeDrawer}
	on:touchmove|preventDefault
	role="presentation"
></div>
