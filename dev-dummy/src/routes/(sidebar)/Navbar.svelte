<script>
	import { Button, Dropdown, DropdownItem, Avatar } from 'flowbite-svelte';
	import { ChevronDownOutline, UserCircleOutline, CogOutline, LockSolid } from 'flowbite-svelte-icons';
	import { isAuthenticated, principal } from '$lib/dummy-data/auth';
</script>

<header class="z-10 py-4 bg-white shadow-md dark:bg-gray-800">
	<div class="container flex items-center justify-between h-full px-6 mx-auto text-purple-600 dark:text-purple-300">
		<div class="flex justify-center flex-1 lg:mr-32">
			<div class="relative w-full max-w-xl mr-6 focus-within:text-purple-500">
				<div class="absolute inset-y-0 flex items-center pl-2">
					<svg class="w-4 h-4" aria-hidden="true" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"></path>
					</svg>
				</div>
				<input
					class="w-full pl-8 pr-2 text-sm text-gray-700 placeholder-gray-600 bg-gray-100 border-0 rounded-md dark:placeholder-gray-500 dark:focus:shadow-outline-gray dark:focus:placeholder-gray-600 dark:bg-gray-700 dark:text-gray-200 focus:placeholder-gray-500 focus:bg-white focus:border-purple-300 focus:outline-none focus:shadow-outline-purple form-input"
					type="text"
					placeholder="Search for projects"
					aria-label="Search"
				/>
			</div>
		</div>
		
		<ul class="flex items-center flex-shrink-0 space-x-6">
			<li class="relative">
				<Button class="relative align-middle rounded-md focus:outline-none focus:shadow-outline-purple" size="sm" pill={true}>
					<svg class="w-5 h-5" aria-hidden="true" fill="currentColor" viewBox="0 0 20 20">
						<path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"></path>
					</svg>
					<span class="absolute top-0 right-0 inline-block w-3 h-3 transform translate-x-1 -translate-y-1 bg-red-600 border-2 border-white rounded-full dark:border-gray-800"></span>
				</Button>
			</li>
			
			<li class="relative">
				<Button class="align-middle rounded-full focus:shadow-outline-purple focus:outline-none" size="sm" pill={true}>
					<Avatar src="" alt="User avatar" class="object-cover w-8 h-8 rounded-full" />
				</Button>
				<Dropdown class="w-56 p-2 mt-2 space-y-2 text-gray-600 bg-white border border-gray-100 rounded-md shadow-md dark:border-gray-700 dark:text-gray-300 dark:bg-gray-700">
					<DropdownItem class="flex items-center p-2 text-sm font-medium text-gray-600 transition-colors duration-150 rounded-md hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200">
						<UserCircleOutline class="w-4 h-4 mr-3" />
						<span>Profile</span>
					</DropdownItem>
					<DropdownItem class="flex items-center p-2 text-sm font-medium text-gray-600 transition-colors duration-150 rounded-md hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200">
						<CogOutline class="w-4 h-4 mr-3" />
						<span>Settings</span>
					</DropdownItem>
					<DropdownItem class="flex items-center p-2 text-sm font-medium text-gray-600 transition-colors duration-150 rounded-md hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200">
						<LockSolid class="w-4 h-4 mr-3" />
						<span>Log out</span>
					</DropdownItem>
				</Dropdown>
			</li>
		</ul>
	</div>
</header>
