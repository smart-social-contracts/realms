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
	// Get commit datetime from meta tag
	let commitDatetime = '';
	// Get version from meta tag
	let version = '';
	
	// This runs on the client side only
	if (typeof document !== 'undefined') {
		const commitHashMeta = document.querySelector('meta[name="commit-hash"]');
		if (commitHashMeta) {
			commitHash = commitHashMeta.getAttribute('content') || '';
			// Format to show only first 7 characters if it's a full hash
			if (commitHash && commitHash !== 'COMMIT_HASH_PLACEHOLDER' && commitHash.length > 7) {
				commitHash = commitHash.substring(0, 7);
			}
		}
		
		const commitDatetimeMeta = document.querySelector('meta[name="commit-datetime"]');
		if (commitDatetimeMeta) {
			commitDatetime = commitDatetimeMeta.getAttribute('content') || '';
		}
		
		const versionMeta = document.querySelector('meta[name="version"]');
		if (versionMeta) {
			version = versionMeta.getAttribute('content') || '';
		}
		
		// Use build-time values as fallback for local development
		// These are injected by Vite at build time via define config
		if (!version || version === 'VERSION_PLACEHOLDER') {
			// @ts-ignore - Vite injects this at build time
			version = typeof __BUILD_VERSION__ !== 'undefined' ? __BUILD_VERSION__ : 'dev';
		}
		if (!commitHash || commitHash === 'COMMIT_HASH_PLACEHOLDER') {
			// @ts-ignore - Vite injects this at build time
			commitHash = typeof __BUILD_COMMIT__ !== 'undefined' ? __BUILD_COMMIT__ : 'local';
		}
		if (!commitDatetime || commitDatetime === 'COMMIT_DATETIME_PLACEHOLDER') {
			// @ts-ignore - Vite injects this at build time
			commitDatetime = typeof __BUILD_TIME__ !== 'undefined' ? __BUILD_TIME__ : new Date().toISOString().replace('T', ' ').substring(0, 19);
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
	
	<!-- Social links -->
	<div class="flex justify-center space-x-6">
		{#each brands as [component, href]}
			<a {href} class="text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white">
				<svelte:component this={component} size="md" />
			</a>
		{/each}
	</div>
	
	<!-- App name, version and commit hash display -->
	<div class="mt-3 text-center">
		<span class="text-xs text-gray-400 dark:text-gray-500">
			Realms GOS {version} ({commitHash}) - {commitDatetime}{typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname.endsWith('.localhost')) ? ' - Local deployment' : ''}
		</span>
	</div>
	
	<!-- Built on Internet Computer section -->
	<div class="flex justify-center mt-3">
		<a href="https://internetcomputer.org" target="_blank" rel="noopener noreferrer" class="flex items-center text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white">
			<img src="/images/internet-computer-icp-logo.svg" alt="Internet Computer Logo" width="24" height="24" class="mr-2" />
			<span class="text-sm">Built on the Internet Computer</span>
		</a>
	</div>
</Frame>
