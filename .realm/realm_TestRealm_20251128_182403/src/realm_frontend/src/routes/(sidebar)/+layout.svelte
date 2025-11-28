<script>
	import '../../app.pcss';
	import Navbar from './Navbar.svelte';
	import Sidebar from './Sidebar.svelte';
	import Footer from './Footer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	
	// Set drawerHidden to true by default for desktop screens
	let drawerHidden = true;

	onMount(() => {
		if (browser) {
			// Ensure light mode is applied by removing dark class
			document.documentElement.classList.remove('dark');
			// Force light mode
			document.documentElement.classList.add('light');
			
			// Set initial drawer state based on screen size
			const updateDrawerState = () => {
				drawerHidden = window.innerWidth < 1024; // true if mobile, false if desktop
			};
			
			// Initialize drawer state
			updateDrawerState();
			
			// Update drawer state on resize
			window.addEventListener('resize', updateDrawerState);
			
			return () => {
				window.removeEventListener('resize', updateDrawerState);
			};
		}
	});

	console.log("Layout is rendering"); // Debugging line
</script>

<header
	class="sticky top-0 z-30 mx-auto w-full flex-none border-b border-gray-200 bg-white dark:border-gray-600 dark:bg-gray-800"
>
	<Navbar bind:drawerHidden />
</header>
<div class="overflow-hidden lg:flex">
	<!-- Sidebar -->
	<Sidebar bind:drawerHidden />

	<!-- Main Content -->
	<div class="relative h-full w-full overflow-y-auto bg-white lg:ml-64 lg:pl-6">
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
