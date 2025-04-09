<script>
	import '../../app.pcss';
	import Navbar from './Navbar.svelte';
	import Sidebar from './Sidebar.svelte';
	import Footer from './Footer.svelte';
	let drawerHidden = false;

	console.log("Layout is rendering"); // Debugging line
</script>

<header
	class="fixed top-0 z-40 mx-auto w-full flex-none border-b border-gray-200 bg-white dark:border-gray-600 dark:bg-gray-800"
>
	<Navbar bind:drawerHidden />
</header>
<div class="overflow-hidden lg:flex">
	<!-- Sidebar -->
	<Sidebar bind:drawerHidden />

	<!-- Main Content -->
	<div class="relative h-full w-full overflow-y-auto pt-[70px] lg:ml-64 lg:pl-6">
		<slot />
		<Footer />
	</div>
</div>
