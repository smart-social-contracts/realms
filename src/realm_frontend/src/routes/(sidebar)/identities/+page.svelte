<script lang="ts">
	import MetaTag from '../../utils/MetaTag.svelte';
	import IdentityCard from '../../utils/settings/IdentityCard.svelte';
	import { imagesPath } from '../../utils/variables';
	import { Button, Card, Heading, P, Spinner } from 'flowbite-svelte';
	import { FingerprintOutline, CheckCircleSolid } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { onMount } from 'svelte';

	const path: string = '/identities';
	const description: string = 'Manage your digital identities';
	const metaTitle: string = 'My Identities';
	const subtitle: string = 'Identity Management';

	interface IdentityProvider {
		extensionName: string;
		name: string;
		providerUrl: string;
		logo: string;
		description: string;
		verified: boolean;
	}

	let loading = true;
	let identityProviders: IdentityProvider[] = [];

	onMount(async () => {
		try {
			const response = await backend.get_extensions();
			if (response.success && response.data.extensionsList) {
				const extensions = response.data.extensionsList.extensions.map((ext: string) => JSON.parse(ext));

				// Find extensions that declare an identity_provider capability
				const providerExtensions = extensions.filter(
					(ext: any) => ext.identity_provider && ext.enabled !== false
				);

				// Check verification status for each identity provider
				const providers: IdentityProvider[] = [];
				for (const ext of providerExtensions) {
					const ip = ext.identity_provider;
					let verified = false;

					try {
						const statusResponse = await backend.extension_sync_call({
							extension_name: ext.name,
							function_name: 'get_identity_status',
							args: ''
						});
						if (statusResponse.success) {
							const statusData = JSON.parse(statusResponse.response);
							verified = statusData.verified === true;
						}
					} catch (err) {
						console.error(`Error checking identity status for ${ext.name}:`, err);
					}

					providers.push({
						extensionName: ext.name,
						name: ip.name || ext.name,
						providerUrl: ip.provider_url || '',
						logo: ip.logo || '',
						description: ip.description || ext.description || '',
						verified
					});
				}

				identityProviders = providers;
			}
		} catch (error) {
			console.error('Error loading identity providers:', error);
		} finally {
			loading = false;
		}
	});
</script>

<MetaTag {path} {description} title={metaTitle} {subtitle} />

<div class="mt-4 space-y-6 px-4 md:px-6">
	<!-- Header Section -->
	<div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-2 mb-2">
			<FingerprintOutline class="w-6 h-6 text-blue-600 dark:text-blue-500" />
			<Heading tag="h1" class="text-2xl font-bold text-gray-900 dark:text-white">My Identities</Heading>
		</div>
		<p class="text-gray-600 dark:text-gray-400">
			Manage and connect your digital identities securely. Connected identities can be used for authentication and cross-platform verification.
		</p>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-16">
			<Spinner size="8" />
		</div>
	{:else if identityProviders.length > 0}
		<!-- Identity Provider Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
			{#each identityProviders as provider}
				<div class="transition-all duration-200 hover:shadow-md">
					{#if provider.verified}
						<IdentityCard
							src={imagesPath(provider.logo)}
							title={provider.name}
							description={provider.description}
							status="Verified"
						/>
					{:else}
						<a href="/extensions/{provider.extensionName}" class="block">
							<Card size="xl" class="flex flex-col items-center justify-center h-full p-8 border-2 border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 cursor-pointer transition-colors">
								<div class="flex flex-col items-center text-center">
									{#if provider.logo}
										<img src={imagesPath(provider.logo)} alt={provider.name} class="w-16 h-16 object-contain mb-4" />
									{:else}
										<div class="p-3 mb-4 rounded-full bg-blue-100 dark:bg-blue-900">
											<FingerprintOutline class="w-8 h-8 text-blue-600 dark:text-blue-400" />
										</div>
									{/if}
									<Heading tag="h3" class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">{provider.name}</Heading>
									<P class="mb-5 text-sm text-gray-500 dark:text-gray-400">
										{provider.description}
									</P>
									<Button size="sm" color="blue" class="px-4 py-2">Start Verification</Button>
								</div>
							</Card>
						</a>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<!-- No identity extensions installed -->
		<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-12 text-center">
			<div class="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
				<FingerprintOutline class="w-8 h-8 text-gray-400 dark:text-gray-500" />
			</div>
			<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">No Identity Providers Available</h2>
			<p class="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
				No identity verification extensions are currently installed. Contact your realm administrator to enable identity verification.
			</p>
		</div>
	{/if}
</div>
