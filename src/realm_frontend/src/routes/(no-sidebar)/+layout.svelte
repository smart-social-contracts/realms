<script>
	import Footer from '../(no-sidebar)/Footer.svelte';
	import Navbar from '../(sidebar)/Navbar.svelte';

	import '../../app.pcss';
</script>

<header
	class="sticky top-0 z-30 mx-auto w-full flex-none border-b border-gray-200 bg-white dark:border-gray-600 dark:bg-gray-800"
>
	<Navbar />
</header>
	<div class="w-full pt-[70px]">
	<slot />
	<Footer />
</div>
