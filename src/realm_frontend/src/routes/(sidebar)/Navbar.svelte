<script>
	import Notifications from '../utils/dashboard/NotificationList.svelte';
	import NotificationsIcon from '$lib/components/NotificationsIcon.svelte';
	import AppsMenu from '../utils/widgets/AppsMenu.svelte';
	import UserMenu from '../utils/widgets/UserMenu.svelte';
	import T from '$lib/components/T.svelte';
	import { _ } from 'svelte-i18n';
	import { isAuthenticated } from '$lib/stores/auth';
	import { hasJoined, profilesLoading } from '$lib/stores/profiles';
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
		Button
	} from 'flowbite-svelte';
	import { ChevronDownOutline } from 'flowbite-svelte-icons';
	import '../../app.pcss';
	import Users from '../data/users.json';

	export let fluid = true;
	export let drawerHidden = false;
	export let list = false;
</script>

<Navbar {fluid} class="text-black" color="default" let:NavContainer>
	<NavHamburger
		onClick={() => (drawerHidden = !drawerHidden)}
		class="m-0 me-3 md:block lg:hidden"
	/>
	<NavBrand href="/" class={list ? 'w-40' : 'lg:w-60'}>
		<img
			src="/images/logo_white_horizontal.png"
			class="h-8 sm:h-10"
			alt="Smart Social Contracts Logo"
		/>
		<span
			class="ml-px self-center whitespace-nowrap text-xl font-semibold dark:text-white sm:text-2xl"
		>
			<!-- Flowbite -->
		</span>
	</NavBrand>
	<div class="hidden lg:block lg:ps-3">
		{#if list}
			<NavUl class="ml-2" activeUrl="/" activeClass="text-primary-600 dark:text-primary-500">
				<NavLi href="/">Home</NavLi>
				<NavLi href="#top">Messages</NavLi>
				<NavLi href="#top">Profile</NavLi>
				<NavLi href="#top">Settings</NavLi>
				<NavLi class="cursor-pointer">
					Dropdown
					<ChevronDownOutline  class="ms-0 inline" />
				</NavLi>
				<Dropdown class="z-20 w-44">
					<DropdownItem href="#top">Item 1</DropdownItem>
					<DropdownItem href="#top">Item 2</DropdownItem>
					<DropdownItem href="#top">Item 3</DropdownItem>
				</Dropdown>
			</NavUl>
		{:else}
			<!-- <form>
				<Search size="md" class="mt-1 w-96 border focus:outline-none" />
			</form> -->
		{/if}
	</div>
	<div class="ms-auto flex items-center text-gray-500 dark:text-gray-400 sm:order-2">
		<NotificationsIcon />
		<!-- <AppsMenu /> -->
		<!-- <DarkMode /> -->
		{#if $isAuthenticated && $profilesLoading}
			<!-- Show a loading spinner while profile data is loading -->
			<div class="flex items-center me-2" role="status">
				<div class="animate-spin h-4 w-4 border-2 border-gray-300 rounded-full border-t-blue-600 mr-2"></div>
				<span class="sr-only">Loading...</span>
			</div>
		{:else if !hasJoined()}
			<Button class="me-2" color="alternative" href="/join" pill={true}>
				<T key="buttons.join" default_text="Join" />
			</Button>
		{/if}
		<UserMenu {...Users[4]} />
	</div>
</Navbar>
