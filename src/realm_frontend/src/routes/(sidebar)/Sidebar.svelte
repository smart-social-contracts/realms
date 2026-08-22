<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount, tick } from 'svelte';
	import { get } from 'svelte/store';
	import type { SidebarConfig } from '$lib/config/sidebar';
	import { locale } from 'svelte-i18n';
	
	import { styles, cn } from '$lib/theme/utilities';
	import { topUtilityItems, SECTION_HEADER_ME, SECTION_HEADER_REALM, SECTION_HEADER_MUNDUS } from '$lib/config/sidebar';
	import { sidebarConfig, sidebarLoading, loadSidebar } from '$lib/stores/sidebar';
	import { profilesLoading } from '$lib/stores/profiles';
	import { isAuthenticated } from '$lib/stores/auth';
	import { unreadCount } from '$lib/stores/notifications';
	import { getTablerIcon } from '$lib/utils/tablerIcons';
	import { isNavItemActive } from '$lib/utils/breadcrumb';
	import { IconLogin, IconLayoutDashboard } from '@tabler/icons-svelte';
	import SidebarFold from './SidebarFold.svelte';
	// @ts-ignore
	import { backend, quarterBackendStore } from '$lib/canisters';

	export let drawerHidden: boolean = false;
	export let desktopHidden: boolean = false;
	
	let showScrollIndicator = true;
	let sidebarContainer: HTMLElement;
	let lastSidebarActor: unknown = null;

	const ACTIVE_ITEM_CLASSES =
		'sidebar-nav-active bg-gray-200 text-gray-900 font-medium hover:bg-gray-200 hover:text-gray-900 dark:bg-[var(--color-gray-700)] dark:hover:bg-[var(--color-gray-600)]';

	$: navPathname = $page.url.pathname;
	$: navSearch = $page.url.search;

	function navIsActive(href: string, pathname = navPathname, search = navSearch): boolean {
		return isNavItemActive(href, pathname, search);
	}

	function isActive(href: string, pathname = navPathname, search = navSearch): boolean {
		return navIsActive(href, pathname, search);
	}

	function itemClasses(href: string, pathname: string, search: string): string {
		return cn(
			styles.sidebar.item(),
			navIsActive(href, pathname, search) ? cn(ACTIVE_ITEM_CLASSES, styles.sidebar.itemActive()) : '',
		);
	}

	function iconClasses(href: string, extra = '', pathname = navPathname, search = navSearch): string {
		return cn(
			extra,
			navIsActive(href, pathname, search) ? 'text-gray-900' : 'text-gray-500 group-hover:text-gray-900',
		);
	}

	let collapsedCategories: Set<string> = new Set();
	let categoriesInitialized = false;
	let knownCategoryIds = new Set<string>();

	function defaultCollapsedCategories(config: SidebarConfig): Set<string> {
		const ids = new Set<string>(['__section_me__', '__section_realm__']);
		if (config.mundusItems.length > 0) {
			ids.add('__section_mundus__');
		}
		for (const category of config.categories) {
			ids.add(category.id);
		}
		return ids;
	}

	function initCollapsedCategories(config: SidebarConfig) {
		if (!categoriesInitialized) {
			categoriesInitialized = true;
			knownCategoryIds = new Set(config.categories.map((category) => category.id));
			collapsedCategories = defaultCollapsedCategories(config);
			return;
		}

		let changed = false;
		for (const category of config.categories) {
			if (!knownCategoryIds.has(category.id)) {
				knownCategoryIds.add(category.id);
				collapsedCategories.add(category.id);
				changed = true;
			}
		}
		if (changed) {
			collapsedCategories = collapsedCategories;
		}
	}

	function toggleCategory(id: string) {
		if (collapsedCategories.has(id)) {
			collapsedCategories.delete(id);
		} else {
			collapsedCategories.add(id);
		}
		collapsedCategories = collapsedCategories;
	}

	function sectionOpen(id: string): boolean {
		return !collapsedCategories.has(id);
	}

	// get_sidebar resolves visibility from the *caller's* user record, which in
	// a federation lives on the member's home quarter — not the capital. Route
	// through the quarter-aware actor and reload whenever it swaps (quarter
	// activation, re-authentication), otherwise the capital answers with the
	// guest menu and admin/member extensions vanish from the sidebar.
	$: {
		const actor = $quarterBackendStore || backend;
		if (actor && actor !== lastSidebarActor) {
			lastSidebarActor = actor;
			loadSidebar(actor, get(locale) || 'en');
		}
	}
	
	function checkScrollPosition() {
		if (sidebarContainer) {
			const { scrollTop, scrollHeight, clientHeight } = sidebarContainer;
			showScrollIndicator = scrollTop + clientHeight < scrollHeight - 20;
		}
	}
	
	onMount(() => {
		if (sidebarContainer) {
			sidebarContainer.addEventListener('scroll', checkScrollPosition);
			checkScrollPosition();
		}

		return () => {
			if (sidebarContainer) {
				sidebarContainer.removeEventListener('scroll', checkScrollPosition);
			}
		};
	});
	
	function closeDrawer() {
		drawerHidden = true;
	}

	function handleNavClick() {
		if (typeof window !== 'undefined' && window.innerWidth < 1024) {
			closeDrawer();
		}
	}

	afterNavigate(() => {
		document.getElementById('svelte')?.scrollTo({ top: 0 });
	});

	function expandForActivePage(
		config: SidebarConfig,
		pathname = navPathname,
		search = navSearch,
	) {
		// Always start from the folded default, then open only the sections that
		// contain the current route. Avoids stale expanded categories from prior
		// navigation or old localStorage entries.
		const next = defaultCollapsedCategories(config);

		if (topUtilityItems.some((item) => navIsActive(item.href, pathname, search))) {
			next.delete('__section_me__');
		}

		const activeCategory = config.categories.find((category) =>
			category.items.some((item) => navIsActive(item.href, pathname, search)),
		);
		const inRealm =
			config.welcomeItems.some((item) => navIsActive(item.href, pathname, search)) ||
			activeCategory ||
			config.mundusItems.some((item) => navIsActive(item.href, pathname, search));

		if (inRealm) {
			next.delete('__section_realm__');
		}

		if (activeCategory) {
			next.delete(activeCategory.id);
		}

		if (config.mundusItems.some((item) => navIsActive(item.href, pathname, search))) {
			next.delete('__section_mundus__');
		}

		collapsedCategories = next;
	}

	function scrollActiveIntoView() {
		if (!sidebarContainer) return;

		requestAnimationFrame(() => {
			const activeLink = sidebarContainer.querySelector('[data-sidebar-active="true"]');
			if (!activeLink) return;

			const containerRect = sidebarContainer.getBoundingClientRect();
			const linkRect = activeLink.getBoundingClientRect();
			const offset =
				linkRect.top - containerRect.top - containerRect.height / 2 + linkRect.height / 2;

			sidebarContainer.scrollTo({
				top: sidebarContainer.scrollTop + offset,
				behavior: 'smooth',
			});
			checkScrollPosition();
		});
	}

	$: if ($sidebarConfig) {
		initCollapsedCategories($sidebarConfig);
	}

	// Expand the section that contains the current page, but only when the
	// route changes. Re-running on every sidebarConfig refresh (cache, then
	// live fetch) would snap user-toggled folds back open.
	let lastFoldExpandKey = '';
	$: if ($sidebarConfig && $isAuthenticated && $page.url.pathname) {
		const path = $page.url.pathname;
		const search = $page.url.search;
		const hasItems =
			($sidebarConfig.welcomeItems?.length || 0) +
				($sidebarConfig.categories?.length || 0) +
				($sidebarConfig.mundusItems?.length || 0) >
			0;
		const key = `${path}${search}`;
		if (hasItems && lastFoldExpandKey !== key) {
			expandForActivePage($sidebarConfig, path, search);
			lastFoldExpandKey = key;
			void tick().then(() => scrollActiveIntoView());
		}
	}

	function sidebarTooltip(node: HTMLElement, text: string | undefined) {
		if (!text) return {};
		let tip: HTMLDivElement | null = null;

		function show() {
			const rect = node.getBoundingClientRect();
			tip = document.createElement('div');
			tip.textContent = text;
			tip.className = [
				'fixed z-[9999] px-2.5 py-1.5',
				'bg-gray-900 text-white text-xs rounded-md',
				'pointer-events-none whitespace-nowrap shadow-lg',
				'transition-opacity duration-150'
			].join(' ');
			tip.style.top = `${rect.top + rect.height / 2}px`;
			tip.style.left = `${rect.right + 10}px`;
			tip.style.transform = 'translateY(-50%)';
			document.body.appendChild(tip);
		}

		function hide() {
			tip?.remove();
			tip = null;
		}

		node.addEventListener('mouseenter', show);
		node.addEventListener('mouseleave', hide);

		return {
			update(newText: string | undefined) {
				text = newText ?? '';
			},
			destroy() {
				node.removeEventListener('mouseenter', show);
				node.removeEventListener('mouseleave', hide);
				hide();
			}
		};
	}

</script>

<!-- Mobile drawer: fill the pane under the header (no guessed top-16 gap). -->
<div
	class="absolute inset-0 z-[60] lg:hidden {drawerHidden ? 'pointer-events-none' : ''}"
	role="dialog"
	aria-modal={!drawerHidden}
	aria-hidden={drawerHidden}
	inert={drawerHidden ? true : undefined}
	aria-label="Navigation menu"
>
	<button
		type="button"
		class="drawer-backdrop absolute inset-0 border-0 bg-gray-900/50 p-0 cursor-pointer touch-manipulation {drawerHidden ? 'is-closed' : ''}"
		aria-label="Close menu"
		tabindex={drawerHidden ? -1 : 0}
		on:click={closeDrawer}
	></button>
	<aside
		class="drawer-panel absolute inset-y-0 left-0 z-10 flex w-64 max-w-[85vw] flex-col border-r border-gray-200 bg-white shadow-xl touch-manipulation {drawerHidden ? 'is-closed' : ''}"
	>
			<h4 class="sr-only">Main menu</h4>
			<div
				class={cn(styles.sidebar.container(), 'overflow-y-auto h-full px-3 pb-12 scrollbar-hide overscroll-contain')}
			>
				<nav>
					{#if !$isAuthenticated}
						<ul class="pt-5 pb-1 space-y-1">
							<li class="px-3 pb-2">
								<p class="text-xs text-gray-500 leading-relaxed">
									Sign in to access your realm navigation and extensions.
								</p>
							</li>
							<li>
								<a href="/join" class={cn(styles.sidebar.item(), 'font-medium')} on:click={handleNavClick}>
									<IconLogin size={22} class="flex-shrink-0 w-5 h-5 text-gray-500 group-hover:text-gray-900" />
									<span class="ml-3">Sign in</span>
								</a>
							</li>
							<li>
								<a
									href="/extensions/public_dashboard"
									class={itemClasses('/extensions/public_dashboard', $page.url.pathname, $page.url.search)}
									data-sidebar-active={isActive('/extensions/public_dashboard', $page.url.pathname, $page.url.search) ? 'true' : undefined}
									aria-current={isActive('/extensions/public_dashboard', $page.url.pathname, $page.url.search) ? 'page' : undefined}
									on:click={handleNavClick}
								>
									<IconLayoutDashboard size={22} class={iconClasses('/extensions/public_dashboard', 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
									<span class="ml-3">Public Dashboard</span>
								</a>
							</li>
						</ul>
					{:else}
						<ul class="pt-5 pb-1 space-y-1">
							<li>
								<button class="flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer" aria-expanded={sectionOpen('__section_me__')} onclick={() => toggleCategory('__section_me__')}>
									<h3 class={styles.sidebar.sectionHeader()}>{SECTION_HEADER_ME}</h3>
									<svg class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen('__section_me__') ? '' : 'is-folded'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>
								</button>
							</li>
						</ul>
						<SidebarFold open={sectionOpen('__section_me__')}>
							<ul class="pb-1 space-y-1">
								{#each topUtilityItems as item}
									{@const IconComp = getTablerIcon(item.icon)}
									<li>
										<a href={item.href} use:sidebarTooltip={item.tooltip} class={itemClasses(item.href, $page.url.pathname, $page.url.search)} data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined} aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined} on:click={handleNavClick}>
											<span class="relative flex-shrink-0">
												<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'w-5 h-5', $page.url.pathname, $page.url.search)} />
												{#if item.href === '/messages' && $unreadCount > 0}
													<span class="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-red-500 ring-2 {isActive(item.href, $page.url.pathname, $page.url.search) ? 'ring-gray-200' : 'ring-white'}" aria-hidden="true"></span>
												{/if}
											</span>
											<span class="ml-3">{item.label}</span>
										</a>
									</li>
								{/each}
							</ul>
						</SidebarFold>
						{#if $profilesLoading || $sidebarLoading}
							<div class="py-4 flex items-center justify-center">
								<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
							</div>
						{/if}
						{#if $sidebarConfig}
							<ul class="pt-3 pb-1 space-y-1">
								<li>
									<button class="flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer" aria-expanded={sectionOpen('__section_realm__')} onclick={() => toggleCategory('__section_realm__')}>
										<h3 class={styles.sidebar.sectionHeader()}>{SECTION_HEADER_REALM}</h3>
										<svg class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen('__section_realm__') ? '' : 'is-folded'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>
									</button>
								</li>
							</ul>
							<SidebarFold open={sectionOpen('__section_realm__')}>
								<ul class="pb-1 space-y-1">
									{#each $sidebarConfig.welcomeItems as item (item.href)}
										{@const IconComp = getTablerIcon(item.icon)}
										<li>
											<a href={item.href} use:sidebarTooltip={item.tooltip} class={itemClasses(item.href, $page.url.pathname, $page.url.search)} data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined} aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined} on:click={handleNavClick}>
												<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
												<span class="ml-3">{item.label}</span>
											</a>
										</li>
									{/each}
								</ul>
								{#each $sidebarConfig.categories as category (category.id)}
									<ul class="pt-2 pb-1 space-y-1">
										<li class="px-3 pt-2 pb-1">
											<button class="flex items-center justify-between w-full cursor-pointer group/cat" aria-expanded={sectionOpen(category.id)} onclick={() => toggleCategory(category.id)}>
												<h3 class={styles.sidebar.categoryHeader()}>{category.label}</h3>
												<svg class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen(category.id) ? '' : 'is-folded'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>
											</button>
										</li>
									</ul>
									<SidebarFold open={sectionOpen(category.id)}>
										<ul class="pb-1 space-y-1">
											{#each category.items as item (item.href)}
												{@const IconComp = getTablerIcon(item.icon)}
												<li>
													<a href={item.href} use:sidebarTooltip={item.tooltip} class={itemClasses(item.href, $page.url.pathname, $page.url.search)} data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined} aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined} on:click={handleNavClick}>
														<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
														<span class="ml-3">{item.label}</span>
													</a>
												</li>
											{/each}
										</ul>
									</SidebarFold>
								{/each}
								{#if $sidebarConfig.mundusItems.length > 0}
									<ul class="pt-4 pb-1 space-y-1">
										<li class="px-3 pt-2 pb-1">
											<button class="flex items-center justify-between w-full cursor-pointer group/cat" aria-expanded={sectionOpen('__section_mundus__')} onclick={() => toggleCategory('__section_mundus__')}>
												<h3 class={styles.sidebar.sectionHeader()}>{SECTION_HEADER_MUNDUS}</h3>
												<svg class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen('__section_mundus__') ? '' : 'is-folded'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>
											</button>
										</li>
									</ul>
									<SidebarFold open={sectionOpen('__section_mundus__')}>
										<ul class="pb-1 space-y-1">
											{#each $sidebarConfig.mundusItems as item (item.href)}
												{@const IconComp = getTablerIcon(item.icon)}
												<li>
													<a href={item.href} use:sidebarTooltip={item.tooltip} class={itemClasses(item.href, $page.url.pathname, $page.url.search)} data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined} aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined} on:click={handleNavClick}>
														<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
														<span class="ml-3">{item.label}</span>
													</a>
												</li>
											{/each}
										</ul>
									</SidebarFold>
								{/if}
							</SidebarFold>
						{/if}
					{/if}
				</nav>
			</div>
		</aside>
</div>

<!-- Desktop sidebar (in-flow beside main; do not pair fixed + ml-64) -->
<aside
	class="hidden lg:flex lg:shrink-0 flex-col min-h-0 h-full bg-white z-30 transition-[width] duration-200 ease-out motion-reduce:transition-none {desktopHidden ? 'w-0 min-w-0 overflow-hidden border-r-0 pointer-events-none' : 'w-64 border-r border-gray-200'}"
	aria-hidden={desktopHidden ? true : undefined}
	inert={desktopHidden ? true : undefined}
>
	<h4 class="sr-only">Main menu</h4>
	<div
		bind:this={sidebarContainer}
		class={cn(styles.sidebar.container(), 'w-64 overflow-y-auto h-full px-3 pb-12 scrollbar-hide overscroll-contain border-r-0')}
	>
		<nav>
			{#if !$isAuthenticated}
				<ul class="pt-5 lg:pt-3 pb-1 space-y-1">
					<li class="px-3 pb-2">
						<p class="text-xs text-gray-500 leading-relaxed">
							Sign in to access your realm navigation and extensions.
						</p>
					</li>
					<li>
						<a
							href="/join"
							class={cn(styles.sidebar.item(), 'font-medium')}
						>
							<IconLogin size={22} class="flex-shrink-0 w-5 h-5 text-gray-500 group-hover:text-gray-900" />
							<span class="ml-3">Sign in</span>
						</a>
					</li>
					<li>
						<a
							href="/extensions/public_dashboard"
							class={itemClasses('/extensions/public_dashboard', $page.url.pathname, $page.url.search)}
							data-sidebar-active={isActive('/extensions/public_dashboard', $page.url.pathname, $page.url.search) ? 'true' : undefined}
							aria-current={isActive('/extensions/public_dashboard', $page.url.pathname, $page.url.search) ? 'page' : undefined}
						>
							<IconLayoutDashboard size={22} class={iconClasses('/extensions/public_dashboard', 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
							<span class="ml-3">Public Dashboard</span>
						</a>
					</li>
				</ul>
			{:else}
			<!-- ME section (super-category) -->
			<ul class="pt-5 lg:pt-3 pb-1 space-y-1">
				<li>
					<button
						class="flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer"
						aria-expanded={sectionOpen('__section_me__')}
						onclick={() => toggleCategory('__section_me__')}
					>
						<h3 class={styles.sidebar.sectionHeader()}>
							{SECTION_HEADER_ME}
						</h3>
						<svg
							class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen('__section_me__') ? '' : 'is-folded'}"
							fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
						</svg>
					</button>
				</li>
			</ul>
			<SidebarFold open={sectionOpen('__section_me__')}>
				<ul class="pb-1 space-y-1">
					{#each topUtilityItems as item}
						{@const IconComp = getTablerIcon(item.icon)}
						<li>
							<a 
								href={item.href}
								use:sidebarTooltip={item.tooltip}
								class={itemClasses(item.href, $page.url.pathname, $page.url.search)}
								data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined}
								aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined}
							>
								<span class="relative flex-shrink-0">
									<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'w-5 h-5', $page.url.pathname, $page.url.search)} />
									{#if item.href === '/messages' && $unreadCount > 0}
										<span
											class="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-red-500 ring-2 {isActive(item.href, $page.url.pathname, $page.url.search) ? 'ring-gray-200' : 'ring-white'}"
											aria-hidden="true"
										></span>
									{/if}
								</span>
								<span class="ml-3">{item.label}</span>
							</a>
						</li>
					{/each}
				</ul>
			</SidebarFold>

			<!-- Loading State -->
			{#if $profilesLoading || $sidebarLoading}
				<div class="py-4 flex items-center justify-center">
					<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
				</div>
			{/if}

			<!-- MY REALM section (super-category) -->
			{#if $sidebarConfig}
				<ul class="pt-3 pb-1 space-y-1">
					<li>
						<button
							class="flex items-center justify-between w-full px-3 py-1.5 rounded-md bg-gray-100 cursor-pointer"
							aria-expanded={sectionOpen('__section_realm__')}
							onclick={() => toggleCategory('__section_realm__')}
						>
							<h3 class={styles.sidebar.sectionHeader()}>
								{SECTION_HEADER_REALM}
							</h3>
							<svg
								class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen('__section_realm__') ? '' : 'is-folded'}"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</li>
				</ul>

				<SidebarFold open={sectionOpen('__section_realm__')}>
					<!-- Welcome items (My Dashboard, etc.) -->
					<ul class="pb-1 space-y-1">
						{#each $sidebarConfig.welcomeItems as item (item.href)}
							{@const IconComp = getTablerIcon(item.icon)}
							<li>
								<a 
									href={item.href}
									use:sidebarTooltip={item.tooltip}
									class={itemClasses(item.href, $page.url.pathname, $page.url.search)}
									data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined}
									aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined}
								>
									<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
									<span class="ml-3">{item.label}</span>
								</a>
							</li>
						{/each}
					</ul>

					<!-- Category sections (collapsible) -->
					{#each $sidebarConfig.categories as category (category.id)}
						<ul class="pt-2 pb-1 space-y-1">
							<li class="px-3 pt-2 pb-1">
								<button
									class="flex items-center justify-between w-full cursor-pointer group/cat"
									aria-expanded={sectionOpen(category.id)}
									onclick={() => toggleCategory(category.id)}
								>
									<h3 class={styles.sidebar.categoryHeader()}>
										{category.label}
									</h3>
									<svg
										class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen(category.id) ? '' : 'is-folded'}"
										fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
									</svg>
								</button>
							</li>
						</ul>
						<SidebarFold open={sectionOpen(category.id)}>
							<ul class="pb-1 space-y-1">
								{#each category.items as item (item.href)}
									{@const IconComp = getTablerIcon(item.icon)}
									<li>
										<a 
											href={item.href}
											use:sidebarTooltip={item.tooltip}
											class={itemClasses(item.href, $page.url.pathname, $page.url.search)}
											data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined}
											aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined}
										>
											<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
											<span class="ml-3">{item.label}</span>
										</a>
									</li>
								{/each}
							</ul>
						</SidebarFold>
					{/each}

					<!-- MY MUNDUS section (super-category) -->
					{#if $sidebarConfig.mundusItems.length > 0}
						<ul class="pt-4 pb-1 space-y-1">
							<li class="px-3 pt-2 pb-1">
								<button
									class="flex items-center justify-between w-full cursor-pointer group/cat"
									aria-expanded={sectionOpen('__section_mundus__')}
									onclick={() => toggleCategory('__section_mundus__')}
								>
									<h3 class={styles.sidebar.sectionHeader()}>
										{SECTION_HEADER_MUNDUS}
									</h3>
									<svg
										class="fold-chevron w-3.5 h-3.5 text-gray-400 {sectionOpen('__section_mundus__') ? '' : 'is-folded'}"
										fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
									</svg>
								</button>
							</li>
						</ul>
						<SidebarFold open={sectionOpen('__section_mundus__')}>
							<ul class="pb-1 space-y-1">
								{#each $sidebarConfig.mundusItems as item (item.href)}
									{@const IconComp = getTablerIcon(item.icon)}
									<li>
										<a 
											href={item.href}
											use:sidebarTooltip={item.tooltip}
											class={itemClasses(item.href, $page.url.pathname, $page.url.search)}
											data-sidebar-active={isActive(item.href, $page.url.pathname, $page.url.search) ? 'true' : undefined}
											aria-current={isActive(item.href, $page.url.pathname, $page.url.search) ? 'page' : undefined}
										>
											<svelte:component this={IconComp} size={22} class={iconClasses(item.href, 'flex-shrink-0 w-5 h-5', $page.url.pathname, $page.url.search)} />
											<span class="ml-3">{item.label}</span>
										</a>
									</li>
								{/each}
							</ul>
						</SidebarFold>
					{/if}
				</SidebarFold>
			{/if}
			{/if}
		</nav>
	</div>

	<!-- Fixed scroll indicator at bottom of sidebar -->
	{#if showScrollIndicator}
		<div class="absolute bottom-0 left-0 right-0 h-12 pointer-events-none bg-gradient-to-t from-white to-transparent flex items-end justify-center pb-2">
			<span class="text-gray-400 text-lg animate-bounce">&#8964;</span>
		</div>
	{/if}
</aside>

<style>
	/* Use real transform/opacity values (not Tailwind translate-* CSS vars) so 200ms interpolates. */
	.drawer-backdrop {
		opacity: 1;
		transition: opacity 200ms ease-out;
	}
	.drawer-backdrop.is-closed {
		opacity: 0;
	}
	.drawer-panel {
		transform: translateX(0);
		transition: transform 200ms ease-out;
	}
	.drawer-panel.is-closed {
		transform: translateX(-100%);
	}
	.fold-chevron {
		transform: rotate(0deg);
		transition: transform 200ms ease-out;
		flex-shrink: 0;
	}
	.fold-chevron.is-folded {
		transform: rotate(-90deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.drawer-backdrop,
		.drawer-panel,
		.fold-chevron {
			transition: none;
		}
	}
</style>
