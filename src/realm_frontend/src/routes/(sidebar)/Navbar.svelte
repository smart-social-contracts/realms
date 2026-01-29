<script>
	import Notifications from '../utils/dashboard/NotificationList.svelte';
	import AppsMenu from '../utils/widgets/AppsMenu.svelte';
	import UserMenu from '../utils/widgets/UserMenu.svelte';
		import { _ } from 'svelte-i18n';
	import { isAuthenticated } from '$lib/stores/auth';
		import { realmInfo, realmLogo, realmName } from '$lib/stores/realmInfo';
	import { onMount } from 'svelte';
	import {
		DarkMode,
		Dropdown,
		DropdownItem,
		NavBrand,
		NavHamburger,
		NavLi,
		NavUl,
		Navbar,
		Search,
	} from 'flowbite-svelte';
	import { ChevronDownOutline } from 'flowbite-svelte-icons';
	import '../../app.pcss';
	import Users from '../data/users.json';

	export let fluid = true;
	export let drawerHidden = false;
	export let list = false;
	
	// Fetch realm info on mount
	onMount(() => {
		realmInfo.fetch();
	});
</script>

<Navbar {fluid} class="text-black relative z-50" color="default" let:NavContainer style="pointer-events: auto;">
	<!-- Left: Hamburger -->
	<NavHamburger
		onClick={() => (drawerHidden = !drawerHidden)}
		class="m-0 md:block p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
	/>
	
	<!-- Center: Logo and Name (absolutely positioned) -->
	<div class="absolute left-1/2 transform -translate-x-1/2">
		<a href="/" class="flex items-center cursor-pointer">
			<img
				src={$realmLogo || "/images/logo_horizontal.svg"}
				class="h-8 sm:h-10 pointer-events-none"
				alt={$realmName || "Realms Logo"}
			/>
			<span
				class="ml-3 self-center whitespace-nowrap text-xl font-medium text-gray-700 dark:text-white sm:text-2xl pointer-events-none"
			>
				{$realmName || ''}
			</span>
		</a>
	</div>
	
	<!-- Right: User Menu -->
	<div class="ms-auto flex items-center text-gray-500 dark:text-gray-400">
		<UserMenu {...Users[4]} />
	</div>
</Navbar>
