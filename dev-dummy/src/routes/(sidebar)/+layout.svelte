<script>
	import Sidebar from './Sidebar.svelte';
	import Navbar from './Navbar.svelte';
</script>

<div class="flex h-screen bg-gray-50 dark:bg-gray-900">
	<Sidebar />
	<div class="flex flex-col flex-1 w-full">
		<Navbar />
		<main class="h-full overflow-y-auto">
			<div class="container px-6 mx-auto grid">
				<slot />
			</div>
		</main>
	</div>
</div>
