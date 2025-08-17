<script lang="ts">
	import { Avatar, Button, Card, Heading } from 'flowbite-svelte';
	import { UserOutline } from 'flowbite-svelte-icons';
	import { _ } from 'svelte-i18n';

	export let src: string | undefined;
</script>

<Card
	size="xl"
	class="block shadow-sm sm:flex sm:space-x-4 sm:py-6 xl:block xl:space-x-0 2xl:flex 2xl:space-x-4"
	horizontal
>
	{#if src}
		<Avatar {src} class="mb-4 h-28 w-28 rounded-lg sm:mb-0 xl:mb-4 2xl:mb-0" size="none" rounded />
	{:else}
		<div class="mb-4 flex h-28 w-28 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700 sm:mb-0 xl:mb-4 2xl:mb-0">
			<UserOutline class="h-16 w-16 text-gray-400 dark:text-gray-500" />
		</div>
	{/if}

	<div class="py-0.5">
		<Heading tag="h3" class="text-xl">{$_('settings.profile_picture')}</Heading>
		<p class="mb-4 mt-1 pt-px text-sm">JPG, GIF or PNG. Max size of 800K</p>
			<div class="flex items-center space-x-4">
				<Button size="sm" class="px-3" color="alternative">Upload picture</Button>
				<Button size="sm" class="px-3" color="alternative">Delete</Button>
			</div>
	</div>
</Card>

<!--
@component
[Go to docs](https://flowbite-svelte-admin-dashboard.vercel.app/)
## Props
@prop export let src: string;
-->
