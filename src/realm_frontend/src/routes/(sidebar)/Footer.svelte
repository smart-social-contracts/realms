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
	
	// Get commit hash from meta tag
	let commitHash = '';
	
	// This runs on the client side only
	if (typeof document !== 'undefined') {
		const metaTag = document.querySelector('meta[name="commit-hash"]');
		if (metaTag) {
			commitHash = metaTag.getAttribute('content') || '';
			// Format to show only first 7 characters if it's a full hash
			if (commitHash && commitHash !== 'COMMIT_HASH_PLACEHOLDER' && commitHash.length > 7) {
				commitHash = commitHash.substring(0, 7);
			}
		}
	}

	const links: LinkType[] = [
		{ name: 'Terms and conditions', href: '#' },
		{ name: 'Privacy Policy', href: '#' },
		{ name: 'Licensing', href: '#' },
		{ name: 'Cookie Policy', href: '#' },
		{ name: 'Contact', href: '#' }
	];

	const brands: [ComponentType, string][] = [
		// [XSolid, 'https://twitter.com/realms_protocol'], # TODO: update when we have it
		[GithubSolid, 'https://github.com/smart-social-contracts/realms'],
		// [DiscordSolid, 'https://discord.gg/realms-community'],  # TODO: replace by OpenChat link when we have it
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
	
	<!-- Commit hash display -->
	{#if commitHash && commitHash !== 'COMMIT_HASH_PLACEHOLDER'}
		<div class="mt-3 text-center">
			<span class="text-xs text-gray-400 dark:text-gray-500">Build: {commitHash}</span>
		</div>
	{/if}
</Frame>
