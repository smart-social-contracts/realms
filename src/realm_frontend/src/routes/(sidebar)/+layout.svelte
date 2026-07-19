<script>
	import '../../app.pcss';
	import Navbar from './Navbar.svelte';
	import Sidebar from './Sidebar.svelte';
	import Footer from './Footer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import DelegationBanner from '$lib/components/DelegationBanner.svelte';
	import PageBreadcrumb from '$lib/components/PageBreadcrumb.svelte';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { hostActionEvents, documentFocus } from '$lib/host-bridge';
	import { portalFocusPush, portalAssistantOpen, isEmbeddedInPortal } from '$lib/portal-bridge.ts';
	import { realmInfo } from '$lib/stores/realmInfo';
	
	const SIDEBAR_STATE_KEY = 'realm_sidebar_state';
	
	let drawerHidden = true;
	let initialized = false;
	let embeddedInPortal = false;
	
	function saveSidebarState(hidden) {
		if (browser && initialized) {
			try {
				localStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(hidden));
			} catch {
				// sandbox / private mode
			}
		}
	}
	
	$: if (browser && initialized) {
		saveSidebarState(drawerHidden);
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
			embeddedInPortal = isEmbeddedInPortal();
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
				}
				wasDesktop = isDesktop;
			};
			
			window.addEventListener('resize', handleResize);

			// Chat UI lives on the mundus RegistryAssistant. When embedded in the
			// portal, forward assistant.open to the parent; otherwise ignore.
			const unsubHostActions = hostActionEvents.subscribe((event) => {
				if (event?.action.type !== 'assistant.open') return;
				if (embeddedInPortal) {
					portalAssistantOpen();
				}
			});

			const unsubFocus = documentFocus.subscribe((focus) => {
				portalFocusPush(focus);
			});
			
			return () => {
				window.removeEventListener('resize', handleResize);
				unsubHostActions();
				unsubFocus();
			};
		}
	});

	$: isFullBleedExtension =
		$page.url.pathname.includes('/extensions/codex_viewer') ||
		$page.url.pathname.includes('/extensions/zone_selector');
</script>

<div class="flex h-screen flex-col overflow-hidden">
	<header
		class="flex-none z-50 mx-auto w-full border-b border-gray-200 bg-white"
	>
		<Navbar bind:drawerHidden />
	</header>
	<div class="flex flex-1 overflow-hidden">
		<!-- Sidebar (left) -->
		<Sidebar bind:drawerHidden />

		<!-- Main Content -->
		<div
			class="main-content-area relative flex-1 overflow-x-hidden bg-white transition-[margin] duration-500 ease-in-out {isFullBleedExtension ? 'flex min-h-0 flex-col overflow-hidden' : 'overflow-y-auto'} {!drawerHidden ? 'lg:ml-64' : ''}"
		>
			<DemoBanner />
			<DelegationBanner />

			<div
				class="{isFullBleedExtension
					? 'flex min-h-0 flex-1 flex-col overflow-hidden px-0 lg:pl-0 lg:pr-0'
					: 'px-4 lg:pl-6 lg:pr-0'}"
			>
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
</div>
