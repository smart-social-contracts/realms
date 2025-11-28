<script lang="ts">
	console.log("Settings Svelte script loaded (top of file)");

	import ProfilePicture from '../../utils/settings/ProfilePicture.svelte';
	import MessagingHandles from '../../utils/settings/MessagingHandles.svelte';
	import { Breadcrumb, BreadcrumbItem, Heading } from 'flowbite-svelte';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../utils/MetaTag.svelte';
	import { _ } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import { backend } from '$lib/canisters.js';

	const path: string = '/settings';
	const description: string = 'Settings example - Smart Social Contracts';
	const title: string = SITE_NAME + ' - Settings';
	const subtitle: string = 'Settings';

	let principal: string = '';
	let profiles: string[] = [];
	let avatar: string | undefined = undefined;
	let loadingUserStatus = true;
	let userStatusError = '';

	onMount(async () => {
		console.log("Settings page mounted");
		// Fetch user status
		try {
			console.log("Backend:", backend);
			
			if (!backend || typeof backend.get_my_user_status !== 'function') {
				throw new Error("Backend canister is not properly initialized");
			}
			
			console.log("Calling backend.get_my_user_status...");
			const response = await backend.get_my_user_status();
			console.log("Backend response:", response);
			
			if (response && response.success && response.data && response.data.userGet) {
				principal = response.data.userGet.principal;
				profiles = response.data.userGet.profiles || [];
				avatar = response.data.userGet.avatar;
			} else {
				console.error("Invalid backend response format:", response);
				throw new Error('Could not fetch user status: Invalid response format.');
			}
		} catch (e: any) {
			userStatusError = e.message || 'Failed to fetch user status.';
		} finally {
			loadingUserStatus = false;
		}
	});
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="grid grid-cols-1 space-y-2 dark:bg-gray-900">
		<div class="col-span-full mb-6">
			<Breadcrumb class="mb-6">
				<BreadcrumbItem home>Home</BreadcrumbItem>
				<BreadcrumbItem>Settings</BreadcrumbItem>
			</Breadcrumb>

			<Heading tag="h1" class="text-xl font-semibold text-gray-900 sm:text-2xl dark:text-white">
				{$_('settings.title', { default: 'User Settings' })}
			</Heading>

			<!-- User Principal and Profiles -->
			{#if loadingUserStatus}
				<div class="mt-4 text-gray-500">Loading user status...</div>
			{:else if userStatusError}
				<div class="mt-4 text-red-500">{userStatusError}</div>
			{:else}
				<div class="mt-4 p-4 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
					<div class="mb-2"><span class="font-semibold">Principal:</span> <span class="font-mono break-all">{principal}</span></div>
					<div><span class="font-semibold">Profiles:</span> {profiles.length > 0 ? profiles.join(', ') : 'None'}</div>
				</div>
			{/if}
		</div>
		
		<!-- Simplified settings with profile and messaging handles -->
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
			<div class="space-y-6">
				<ProfilePicture src={avatar} />
			</div>
			<div class="space-y-6">
				<MessagingHandles />
			</div>
		</div>
	</div>
</main>
