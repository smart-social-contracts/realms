<script lang="ts">
	import { Card, Frame, type LinkType } from 'flowbite-svelte';
	import {
		DiscordSolid,
		DribbbleSolid,
		FacebookSolid,
		GithubSolid,
		TwitterSolid,
		XSolid,
	} from 'flowbite-svelte-icons';
	import type { ComponentType } from 'svelte';

	const links: LinkType[] = [
		{ name: 'Terms and conditions', href: '#' },
		{ name: 'Privacy Policy', href: '#' },
		{ name: 'Licensing', href: '#' },
		{ name: 'Cookie Policy', href: '#' },
		{ name: 'Contact', href: '#' }
	];

	const brands: [ComponentType, string][] = [
		[XSolid, ''],
		[GithubSolid, ''],
	];
</script>

<Frame
	tag="footer"
	rounded
	shadow
	class="mx-auto mt-6 w-full max-w-screen-xl rounded-lg bg-white p-6 shadow dark:bg-gray-800 pl-2"
>
	<!-- <ul class="flex flex-wrap items-center justify-center space-x-4 space-y-1 md:space-x-6 xl:space-x-8">
		{#each links as { name, href }}
			<li>
				<a
					{href}
					class="text-sm font-normal text-gray-500 hover:underline dark:text-gray-400"
				>
					{name}
				</a>
			</li>
		{/each}
	</ul> -->
	<div class="mt-4 flex justify-center space-x-6 md:mt-0">
		{#each brands as [component, href]}
			<a {href} class="text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white">
				<svelte:component this={component} size="md" />
			</a>
		{/each}
	</div>
</Frame>
