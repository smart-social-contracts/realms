<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Button } from 'flowbite-svelte';
	import { getAllExtensions, toggleExtension, type ExtensionMetadata } from '$lib/extensions';
	import { getIcon } from '$lib/utils/iconMap';
	import { _ } from 'svelte-i18n';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../utils/MetaTag.svelte';
	
	const path: string = '/extensions';
	const description: string = 'Browse and install extensions for your Smart Social Contracts platform';
	const title: string = SITE_NAME + ' - Extensions';
	const subtitle: string = 'Extensions Marketplace';
	
	// Get all extensions
	$: extensions = getAllExtensions();
	
	// Extension toggle handler
	function handleToggleExtension(id: string, currentState: boolean) {
		toggleExtension(id, !currentState);
		// Force update of extensions list
		extensions = getAllExtensions();
	}
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="max-w-7xl mx-auto">
		<h1 class="text-3xl font-bold mb-6 text-gray-900 dark:text-white">{$_('extensions.market_place.title')}</h1>
		
		<p class="mb-8 text-gray-600 dark:text-gray-400">
			{$_('extensions.market_place.description')}
		</p>
		
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each extensions as extension (extension.id)}
				<Card padding="xl" class="h-full flex flex-col">
					<div class="flex items-start mb-4">
						<div class="p-3 bg-primary-100 dark:bg-primary-900 rounded-lg mr-3">
							<svelte:component 
								this={getIcon(extension.icon)} 
								class="w-6 h-6 text-primary-600 dark:text-primary-400"
							/>
						</div>
						<div>
							<h3 class="text-xl font-semibold text-gray-900 dark:text-white">{$_(`extensions.${extension.id}.name`)}</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400">v{extension.version} by {extension.author}</p>
						</div>
					</div>
					
					<p class="text-gray-700 dark:text-gray-300 mb-4 flex-grow">
						{$_(`extensions.${extension.id}.description`)}
					</p>
					
					{#if extension.permissions && extension.permissions.length > 0}
						<div class="mb-4">
							<p class="text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$_('extensions.market_place.required_permissions')}</p>
							<div class="flex flex-wrap gap-2">
								{#each extension.permissions as permission}
									<span class="bg-gray-100 text-gray-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-gray-700 dark:text-gray-300">
										{permission}
									</span>
								{/each}
							</div>
						</div>
					{/if}
					
					<div class="flex justify-between mt-auto">
						<Button href="/extensions/{extension.id}" color="primary" class="w-full">
							{$_('extensions.market_place.open_extension')}
						</Button>
					</div>
				</Card>
			{/each}
		</div>
	</div>
</main>
