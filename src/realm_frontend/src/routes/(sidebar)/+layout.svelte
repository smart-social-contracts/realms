<script>
	import '../../app.pcss';
	import Navbar from './Navbar.svelte';
	import Sidebar from './Sidebar.svelte';
	import Footer from './Footer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import AiAssistantPanel from '$lib/components/AiAssistantPanel.svelte';
	import PageBreadcrumb from '$lib/components/PageBreadcrumb.svelte';
	import { isAuthenticated } from '$lib/stores/auth';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	
	const SIDEBAR_STATE_KEY = 'realm_sidebar_state';
	const AI_PANEL_STATE_KEY = 'realm_ai_panel_state';
	
	let drawerHidden = true;
	let aiPanelOpen = false;
	let initialized = false;
	
	function saveSidebarState(hidden) {
		if (browser && initialized) {
			localStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(hidden));
		}
	}

	function saveAiPanelState(open) {
		if (browser && initialized) {
			localStorage.setItem(AI_PANEL_STATE_KEY, JSON.stringify(open));
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
			document.documentElement.classList.remove('dark');
			document.documentElement.classList.add('light');
			
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
			
			initialized = true;
			
			const handleResize = () => {
				if (window.innerWidth < 1024) {
					drawerHidden = true;
					aiPanelOpen = false;
				}
			};
			
			window.addEventListener('resize', handleResize);
			
			return () => {
				window.removeEventListener('resize', handleResize);
			};
		}
	});
</script>

<div class="flex h-screen flex-col overflow-hidden">
	<header
		class="flex-none z-50 mx-auto w-full border-b border-gray-200 bg-white"
	>
		<Navbar bind:drawerHidden bind:aiPanelOpen />
	</header>
	<div class="flex flex-1 overflow-hidden">
		{#if $isAuthenticated}
			<!-- Sidebar (left) -->
			<Sidebar bind:drawerHidden />
		{/if}

		<!-- Main Content -->
		<div class="relative flex-1 overflow-y-auto overflow-x-hidden bg-white transition-[margin] duration-500 ease-in-out {$isAuthenticated && !drawerHidden ? 'lg:ml-64' : ''} {aiPanelOpen ? 'lg:mr-80' : ''}">
			<DemoBanner />

			<div class="px-4 lg:pl-6 lg:pr-0">
				<PageBreadcrumb />
				
				<slot />
				{#if !($page.url.pathname.includes('/extensions/') && $page.url.pathname.includes('/llm_chat'))}
					<Footer />
				{/if}
			</div>
		</div>

		<!-- AI Assistant Panel (right) -->
		<AiAssistantPanel bind:open={aiPanelOpen} onClose={() => (aiPanelOpen = false)} />
	</div>
</div>
