<script lang="ts">
	import { onMount } from 'svelte';
	import { _ } from 'svelte-i18n';
	import { Card, Button, Badge, Spinner, Toggle } from 'flowbite-svelte';
	import { ArrowUpRightFromSquareOutline, LayersOutline, UserOutline, RectangleListSolid, WalletSolid, BellOutline, ChartPieOutline, BookOpenOutline, ShieldCheckOutline, HomeOutline, CogOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';

	interface Extension {
		name: string;
		version: string;
		description: string;
		author: string;
		icon?: string;
		categories?: string[];
		profiles?: string[];
		doc_url?: string;
		url_path?: string;
		show_in_sidebar?: boolean;
		installed?: boolean;
		enabled?: boolean;
	}

	let extensions: Extension[] = [];
	let loading = true;
	let error: string | null = null;

	onMount(async () => {
		try {
			console.log('Loading extensions from backend...');
			const response = await backend.get_extensions();
			console.log('Backend response:', response);
			
			if (response && response.success && response.data && response.data.ExtensionsList) {
				const extensionData = response.data.ExtensionsList.extensions.map(ext => JSON.parse(ext));
				console.log('Parsed extension data:', extensionData);
				
				extensions = extensionData.map(ext => ({
					name: ext.name,
					version: ext.version,
					description: ext.description,
					author: ext.author,
					icon: ext.icon,
					categories: ext.categories,
					profiles: ext.profiles,
					doc_url: ext.doc_url,
					url_path: ext.url_path,
					show_in_sidebar: ext.show_in_sidebar,
					installed: true, // All extensions returned by backend are installed
					enabled: ext.show_in_sidebar !== false // Default to enabled unless explicitly disabled
				}));
				
				console.log('Extensions loaded successfully:', extensions.length);
			} else {
				console.error('Invalid response format from backend:', response);
			}
		} catch (err) {
			console.error('Error loading extensions:', err);
		} finally {
			loading = false;
		}
	});

	function getCategoryName(category: string): string {
		const categoryMap: Record<string, string> = {
			public_services: 'Public Services',
			finances: 'Finances',
			other: 'Other'
		};
		return categoryMap[category] || category;
	}

	function getStatusColor(installed: boolean): string {
		return installed ? 'green' : 'blue';
	}

	function getStatusText(installed: boolean): string {
		return installed ? 'Installed' : 'Available';
	}

	function getExtensionIcon(iconName: string | undefined, extensionName: string) {
		const iconMap: Record<string, any> = {
			layers: LayersOutline,
			user: UserOutline,
			table: RectangleListSolid,
			wallet: WalletSolid,
			chat: UserOutline, // Fallback since ChatBubbleLeftRightOutline doesn't exist
			bell: BellOutline,
			chart: ChartPieOutline,
			book: BookOpenOutline,
			shield: ShieldCheckOutline,
			beaker: UserOutline, // Fallback since BeakerOutline doesn't exist
			home: HomeOutline,
			cog: CogOutline
		};
		return iconMap[iconName || ''] || UserOutline;
	}

	function handleToggleExtension(extension: Extension) {
		// Update the extension's enabled state
		extension.enabled = !extension.enabled;
		// Here you would typically call a backend API to enable/disable the extension
		console.log(`${extension.enabled ? 'Enabled' : 'Disabled'} extension:`, extension.name);
		// Force reactivity update
		extensions = [...extensions];
	}
</script>

<div class="space-y-6">
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
			{$_('extensions.market_place.title')}
		</h1>
		<p class="text-gray-600 dark:text-gray-400">
			{$_('extensions.market_place.description')}
		</p>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-12">
			<Spinner size="8" />
			<span class="ml-3 text-gray-600 dark:text-gray-400">Loading extensions...</span>
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each extensions as extension}
				<Card class="h-full">
					<div class="flex flex-col h-full">
						<div class="flex items-start justify-between mb-4">
							<div class="flex items-center">
								<div class="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center mr-3">
									<svelte:component this={getExtensionIcon(extension.icon, extension.name)} class="w-6 h-6 text-blue-600 dark:text-blue-400" />
								</div>
								<div>
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white capitalize">
										{extension.name.replace(/_/g, ' ')}
									</h3>
									<p class="text-sm text-gray-500 dark:text-gray-400">v{extension.version}</p>
								</div>
							</div>
							<Badge color={getStatusColor(extension.installed || false)}>
								{getStatusText(extension.installed || false)}
							</Badge>
						</div>

						<p class="text-gray-600 dark:text-gray-400 text-sm mb-4 flex-grow">
							{extension.description}
						</p>

						<div class="space-y-3">
							{#if extension.categories && extension.categories.length > 0}
								<div class="flex flex-wrap gap-1">
									{#each extension.categories as category}
										<Badge color="light" class="text-xs">
											{getCategoryName(category)}
										</Badge>
									{/each}
								</div>
							{/if}

							<div class="text-xs text-gray-500 dark:text-gray-400">
								<p><strong>Author:</strong> {extension.author}</p>
								{#if extension.profiles}
									<p><strong>Profiles:</strong> {extension.profiles.join(', ')}</p>
								{/if}
							</div>

							<div class="flex items-center justify-between pt-2">
								<div class="flex items-center space-x-2">
									<span class="text-sm text-gray-600 dark:text-gray-400">
										{extension.enabled ? 'Enabled' : 'Disabled'}
									</span>
									<Toggle 
										checked={extension.enabled || false} 
										on:change={() => handleToggleExtension(extension)}
										size="small"
									/>
								</div>
								
								{#if extension.doc_url}
									<Button color="light" size="sm" href={extension.doc_url} target="_blank">
										<ArrowUpRightFromSquareOutline class="w-4 h-4" />
									</Button>
								{/if}
							</div>
						</div>
					</div>
				</Card>
			{/each}
		</div>
	{/if}
</div>
