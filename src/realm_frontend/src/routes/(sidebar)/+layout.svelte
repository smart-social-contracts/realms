<script>
	import '../../app.pcss';
	import Navbar from './Navbar.svelte';
	import Sidebar from './Sidebar.svelte';
	import Footer from './Footer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import DelegationBanner from '$lib/components/DelegationBanner.svelte';
	import AiAssistantPanel from '$lib/components/AiAssistantPanel.svelte';
	import PageBreadcrumb from '$lib/components/PageBreadcrumb.svelte';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { hostActionEvents } from '$lib/host-bridge';
	import { realmInfo, aiAssistantEnabled } from '$lib/stores/realmInfo';
	
	const SIDEBAR_STATE_KEY = 'realm_sidebar_state';
	const AI_PANEL_STATE_KEY = 'realm_ai_panel_state';
	
	let drawerHidden = true;
	let aiPanelOpen = false;
	let aiPanelWidth = 320;
	let initialized = false;
	
	function saveSidebarState(hidden) {
		if (browser && initialized) {
			try {
				localStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(hidden));
			} catch {
				// sandbox / private mode
			}
		}
	}

	function saveAiPanelState(open) {
		if (browser && initialized) {
			try {
				localStorage.setItem(AI_PANEL_STATE_KEY, JSON.stringify(open));
			} catch {
				// sandbox / private mode
			}
		}
	}
	
	$: if (browser && initialized) {
		saveSidebarState(drawerHidden);
	}

	$: if (browser && initialized) {
		saveAiPanelState(aiPanelOpen);
	}

	$: if (browser) {
		if (!drawerHidden && typeof window !== 'undefined' && window.innerWidth < 1024) {
			document.body.classList.add('overflow-hidden');
			document.body.style.touchAction = 'none';
		} else {
			document.body.classList.remove('overflow-hidden');
			document.body.style.touchAction = '';
		}
	}

	onMount(() => {
		if (browser) {
			void realmInfo.fetch();
			document.documentElement.classList.remove('dark');
			document.documentElement.classList.add('light');
			
			try {
				const savedSidebar = localStorage.getItem(SIDEBAR_STATE_KEY);
				if (savedSidebar !== null) {
					drawerHidden = JSON.parse(savedSidebar);
				} else {
					drawerHidden = window.innerWidth < 1024;
				}

				const savedAi = localStorage.getItem(AI_PANEL_STATE_KEY);
				if (savedAi !== null) {
					aiPanelOpen = JSON.parse(savedAi);
				}
			} catch {
				drawerHidden = window.innerWidth < 1024;
			}
			
			initialized = true;

			// Only react when crossing the lg breakpoint — not on keyboard-open
			// viewport resizes (those fire `resize` but keep innerWidth < 1024).
			let wasDesktop = window.innerWidth >= 1024;

			const handleResize = () => {
				const isDesktop = window.innerWidth >= 1024;
				if (wasDesktop && !isDesktop) {
					drawerHidden = true;
					aiPanelOpen = false;
				}
				wasDesktop = isDesktop;
			};
			
			window.addEventListener('resize', handleResize);

			const unsubHostActions = hostActionEvents.subscribe((event) => {
				if (event?.action.type === 'assistant.open' && get(aiAssistantEnabled)) {
					aiPanelOpen = true;
				}
			});
			
			return () => {
				window.removeEventListener('resize', handleResize);
				unsubHostActions();
			};
		}
	});

	$: if (browser && initialized && !$aiAssistantEnabled) {
		aiPanelOpen = false;
	}

	$: isFullBleedExtension =
		$page.url.pathname.includes('/extensions/codex_viewer') ||
		($page.url.pathname.includes('/extensions/') && $page.url.pathname.includes('/llm_chat'));
</script>

<div class="flex h-screen flex-col overflow-hidden">
	<header
		class="flex-none z-50 mx-auto w-full border-b border-gray-200 bg-white"
	>
		<Navbar bind:drawerHidden bind:aiPanelOpen />
	</header>
	<div class="flex flex-1 overflow-hidden">
		<!-- Sidebar (left) -->
		<Sidebar bind:drawerHidden />

		<!-- Main Content -->
		<div
			class="main-content-area relative flex-1 overflow-y-auto overflow-x-hidden bg-white transition-[margin] duration-500 ease-in-out {!drawerHidden ? 'lg:ml-64' : ''}"
			class:ai-panel-open={aiPanelOpen && $aiAssistantEnabled}
			style="--ai-panel-width: {aiPanelWidth}px"
		>
			<DemoBanner />
			<DelegationBanner />

			<div class="{isFullBleedExtension ? 'px-0 lg:pl-0 lg:pr-0' : 'px-4 lg:pl-6 lg:pr-0'}">
				{#if !isFullBleedExtension}
					<PageBreadcrumb />
				{/if}
				
				<slot />
				{#if !isFullBleedExtension}
					<Footer />
				{/if}
			</div>
		</div>
	</div>

	<!-- AI Assistant Panel — sibling of overflow-hidden row so resize handle isn't clipped.
	     `ai_assistant_enabled` (#233) governs ONLY this in-realm, realm-context surface
	     (codex/proposal tools, realm status injection). It does NOT and must not disable
	     the user's global assistant, which lives on the registry (canonical II origin) and
	     never consults this realm flag. -->
	{#if $aiAssistantEnabled}
		<AiAssistantPanel
			bind:open={aiPanelOpen}
			bind:panelWidth={aiPanelWidth}
			onClose={() => (aiPanelOpen = false)}
		/>
	{/if}
</div>

<style>
	@media (min-width: 1024px) {
		.main-content-area.ai-panel-open {
			margin-right: var(--ai-panel-width);
		}
	}
</style>
