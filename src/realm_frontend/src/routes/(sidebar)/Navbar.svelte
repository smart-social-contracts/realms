<script>
	import AuthButton from '$lib/components/AuthButton.svelte';
	import { realmInfo, realmName } from '$lib/stores/realmInfo';
	import { onMount } from 'svelte';
	import { NavHamburger, Navbar } from 'flowbite-svelte';
	import '../../app.pcss';

	export let fluid = true;
	export let drawerHidden = false;
	export let list = false;

	onMount(() => {
		realmInfo.fetch();
	});
</script>

<Navbar {fluid} class="text-black relative z-50" color="default" let:NavContainer style="pointer-events: auto;">
	<NavHamburger
		onClick={() => (drawerHidden = !drawerHidden)}
		class="m-0 md:block p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
	/>

	<div class="absolute left-1/2 transform -translate-x-1/2">
		<a href="/" class="flex items-center cursor-pointer">
			<img
				src="/images/logo.png"
				class="h-8 sm:h-10 pointer-events-none"
				alt={$realmName || 'Realms Logo'}
			/>
			<span
				class="ml-3 self-center whitespace-nowrap text-xl font-medium text-gray-700 dark:text-white sm:text-2xl pointer-events-none"
			>
				{$realmName || ''}
			</span>
		</a>
	</div>

	<div class="ms-auto flex items-center gap-2 text-gray-500 dark:text-gray-400">
		<AuthButton />
	</div>
</Navbar>
