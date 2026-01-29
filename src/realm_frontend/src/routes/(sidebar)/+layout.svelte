<script>
	import '../../app.pcss';
	import Navbar from './Navbar.svelte';
	import Sidebar from './Sidebar.svelte';
	import Footer from './Footer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	
	const SIDEBAR_STATE_KEY = 'realm_sidebar_state';
	
	// Set drawerHidden to true by default
	let drawerHidden = true;
	let initialized = false;
	
	// Save sidebar state to localStorage
	function saveSidebarState(hidden) {
		if (browser && initialized) {
			localStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(hidden));
		}
	}
	
	// Watch for changes to drawerHidden and save (only after initialization)
	$: if (browser && initialized) {
		saveSidebarState(drawerHidden);
	}

	onMount(() => {
		if (browser) {
			// Ensure light mode is applied by removing dark class
			document.documentElement.classList.remove('dark');
			// Force light mode
			document.documentElement.classList.add('light');
			
			// Load saved state or use screen size default
			const saved = localStorage.getItem(SIDEBAR_STATE_KEY);
			if (saved !== null) {
				drawerHidden = JSON.parse(saved);
			} else {
				// Default: visible on desktop, hidden on mobile
				drawerHidden = window.innerWidth < 1024;
			}
			
			// Mark as initialized so we start saving changes
			initialized = true;
			
			// Only update on resize for mobile breakpoint changes
			const handleResize = () => {
				// On mobile, always hide sidebar
				if (window.innerWidth < 1024) {
					drawerHidden = true;
				}
			};
			
			window.addEventListener('resize', handleResize);
			
			return () => {
				window.removeEventListener('resize', handleResize);
			};
		}
	});

	console.log("Layout is rendering"); // Debugging line
</script>

<header
	class="sticky top-0 z-50 mx-auto w-full flex-none border-b border-gray-200 bg-white dark:border-gray-600 dark:bg-gray-800"
>
	<Navbar bind:drawerHidden />
</header>
<div class="min-h-screen lg:flex">
	<!-- Sidebar -->
	<Sidebar bind:drawerHidden />

	<!-- Main Content -->
	<div class="relative h-full w-full overflow-x-hidden bg-white transition-[margin] duration-500 ease-in-out {drawerHidden ? '' : 'lg:ml-64'} lg:pl-6">
		<!-- Demo Banner -->
		<div class="px-4 lg:px-0">
			<DemoBanner />
		</div>
		
		<slot />
		{#if !($page.url.pathname.includes('/extensions/') && $page.url.pathname.includes('/llm_chat'))}
			<Footer />
		{/if}
	</div>
</div>
