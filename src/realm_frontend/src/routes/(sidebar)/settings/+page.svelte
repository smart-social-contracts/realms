<script lang="ts">
	import GeneralInfo from '../../utils/settings/GeneralInfo.svelte';
	import LanguageTime from '../../utils/settings/LanguageTime.svelte';
	import ProfilePicture from '../../utils/settings/ProfilePicture.svelte';
	import { Breadcrumb, BreadcrumbItem, Heading } from 'flowbite-svelte';
	import Footer from '../Footer.svelte';
	import { SITE_NAME } from '$lib/config';
	import { imagesPath } from '../../utils/variables';
	import Users from '../../data/users.json';
	import MetaTag from '../../utils/MetaTag.svelte';
	import { _ } from 'svelte-i18n';
	import { onMount } from 'svelte';

	const path: string = '/settings';
	const description: string = 'Settings example - Smart Social Contracts';
	const title: string = SITE_NAME + ' - Settings';
	const subtitle: string = 'Settings';

	// For translation text
	let settingsTitle = 'User Settings';
	onMount(() => {
		settingsTitle = _('settings.title', { fallback: 'User Settings' });
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
				{settingsTitle}
			</Heading>
		</div>
		
		<!-- Simplified settings with just profile and language sections -->
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
			<div class="space-y-6">
				<ProfilePicture src={imagesPath(Users[4].avatar, 'users')} />
			</div>
			<div class="space-y-6">
				<LanguageTime />
				<GeneralInfo />
			</div>
		</div>
	</div>
</main>
<Footer />
