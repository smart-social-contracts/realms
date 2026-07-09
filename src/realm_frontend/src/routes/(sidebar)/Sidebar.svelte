<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { locale } from 'svelte-i18n';
	
	import { styles, cn } from '$lib/theme/utilities';
	import { topUtilityItems, SECTION_HEADER_ME, SECTION_HEADER_REALM, SECTION_HEADER_MUNDUS } from '$lib/config/sidebar';
	import { sidebarConfig, sidebarLoading, loadSidebar } from '$lib/stores/sidebar';
	import { profilesLoading } from '$lib/stores/profiles';
	import { isAuthenticated } from '$lib/stores/auth';
	import { getTablerIcon } from '$lib/utils/tablerIcons';
	import { IconLogin, IconLayoutDashboard } from '@tabler/icons-svelte';
	// @ts-ignore
	import { backend, quarterBackendStore } from '$lib/canisters';

	export let drawerHidden: boolean = false;
	
	let showScrollIndicator = true;
	let sidebarContainer: HTMLElement;
	let lastSidebarActor: unknown = null;

	const STORAGE_KEY = 'sidebar_collapsed';

	let collapsedCategories: Set<string> = new Set();

	onMount(() => {
		try {
			const saved = localStorage.getItem(STORAGE_KEY);
			if (saved) collapsedCategories = new Set(JSON.parse(saved));
		} catch {}
	});

	function toggleCategory(id: string) {
		if (collapsedCategories.has(id)) {
			collapsedCategories.delete(id);
		} else {
			collapsedCategories.add(id);
		}
		collapsedCategories = collapsedCategories;
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify([...collapsedCategories]));
		} catch {}
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
		setTimeout(() => {
			const sidebar = document.querySelector('aside.fixed');
			if (sidebar) {
				const scrollDiv = sidebar.querySelector('.overflow-y-auto');
				if (scrollDiv) {
					sidebarContainer = scrollDiv as HTMLElement;
					sidebarContainer.addEventListener('scroll', checkScrollPosition);
					checkScrollPosition();
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

	afterNavigate((navigation) => {
		document.getElementById('svelte')?.scrollTo({ top: 0 });
		activeUrl = navigation.to?.url.pathname ?? '';
	});

	let activeUrl = '';

	function isActive(href: string): boolean {
		const pagePath = $page.url.pathname + $page.url.search;
		if (href === pagePath) return true;
		if (href.includes('?')) return false;
		return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
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

<aside
	class="fixed top-0 left-0 z-40 flex-none h-[calc(100vh-4rem)] w-64 mt-16 border-r border-gray-200 transition-transform duration-500 ease-in-out {drawerHidden ? '-translate-x-full' : 'translate-x-0'}"
>
	<h4 class="sr-only">Main menu</h4>
	<div class={cn(styles.sidebar.container(), "overflow-y-auto h-full px-3 pb-12 scrollbar-hide overscroll-contain")}>
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
							class={cn(
								styles.sidebar.item(),
								isActive('/extensions/public_dashboard') ? 'bg-gray-100 font-medium' : ''
							)}
						>
							<IconLayoutDashboard size={22} class="flex-shrink-0 w-5 h-5 text-gray-500 group-hover:text-gray-900" />
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
						on:click={() => toggleCategory('__section_me__')}
					>
						<h3 class={styles.sidebar.sectionHeader()}>
							{SECTION_HEADER_ME}
						</h3>
						<svg
							class="w-3.5 h-3.5 text-gray-400 transition-transform duration-200 {collapsedCategories.has('__section_me__') ? '-rotate-90' : ''}"
							fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
						</svg>
					</button>
				</li>
				{#if !collapsedCategories.has('__section_me__')}
					{#each topUtilityItems as item}
						{@const IconComp = getTablerIcon(item.icon)}
						<li>
							<a 
								href={item.href}
								use:sidebarTooltip={item.tooltip}
								class={cn(
									styles.sidebar.item(),
									isActive(item.href) ? 'bg-gray-100 font-medium' : ''
								)}
							>
								<svelte:component this={IconComp} size={22} class="flex-shrink-0 w-5 h-5 text-gray-500 group-hover:text-gray-900" />
								<span class="ml-3">{item.label}</span>
							</a>
						</li>
					{/each}
				{/if}
			</ul>

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
							on:click={() => toggleCategory('__section_realm__')}
						>
							<h3 class={styles.sidebar.sectionHeader()}>
								{SECTION_HEADER_REALM}
							</h3>
							<svg
								class="w-3.5 h-3.5 text-gray-400 transition-transform duration-200 {collapsedCategories.has('__section_realm__') ? '-rotate-90' : ''}"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</li>
				</ul>

				{#if !collapsedCategories.has('__section_realm__')}
					<!-- Welcome items (My Dashboard, etc.) -->
					<ul class="pb-1 space-y-1">
						{#each $sidebarConfig.welcomeItems as item}
							{@const IconComp = getTablerIcon(item.icon)}
							<li>
								<a 
									href={item.href}
									use:sidebarTooltip={item.tooltip}
									class={styles.sidebar.item()}
								>
									<svelte:component this={IconComp} size={22} class="flex-shrink-0 w-5 h-5 text-gray-500 group-hover:text-gray-900" />
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
									on:click={() => toggleCategory(category.id)}
								>
									<h3 class={styles.sidebar.categoryHeader()}>
										{category.label}
									</h3>
									<svg
										class="w-3.5 h-3.5 text-gray-400 transition-transform duration-200 {collapsedCategories.has(category.id) ? '-rotate-90' : ''}"
										fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
									</svg>
								</button>
							</li>
						{#if !collapsedCategories.has(category.id)}
							{#each category.items as item}
								{@const IconComp = getTablerIcon(item.icon)}
								<li>
									<a 
										href={item.href}
										use:sidebarTooltip={item.tooltip}
										class={cn(
											styles.sidebar.item(),
											isActive(item.href) ? 'bg-gray-100 font-medium' : ''
										)}
									>
										<svelte:component this={IconComp} size={22} class="flex-shrink-0 w-5 h-5 text-gray-500 group-hover:text-gray-900" />
										<span class="ml-3">{item.label}</span>
									</a>
								</li>
							{/each}
						{/if}
						</ul>
					{/each}

					<!-- MY MUNDUS section (super-category) -->
					{#if $sidebarConfig.mundusItems.length > 0}
						<ul class="pt-4 pb-1 space-y-1">
							<li class="px-3 py-2">
								<h3 class={styles.sidebar.sectionHeader()}>
									{SECTION_HEADER_MUNDUS}
								</h3>
							</li>
						{#each $sidebarConfig.mundusItems as item}
							{@const IconComp = getTablerIcon(item.icon)}
							<li>
								<a 
									href={item.href}
									use:sidebarTooltip={item.tooltip}
									class={cn(
										styles.sidebar.item(),
										isActive(item.href) ? 'bg-gray-100 font-medium' : ''
									)}
								>
									<svelte:component this={IconComp} size={22} class="flex-shrink-0 w-5 h-5 text-gray-500 group-hover:text-gray-900" />
									<span class="ml-3">{item.label}</span>
								</a>
							</li>
						{/each}
						</ul>
					{/if}
				{/if}
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

<!-- Mobile overlay -->
<div
	hidden={drawerHidden}
	class="fixed inset-0 z-20 bg-gray-900/50 lg:hidden touch-none overscroll-none"
	on:click={closeDrawer}
	on:keydown={closeDrawer}
	on:touchmove|preventDefault
	role="presentation"
></div>
