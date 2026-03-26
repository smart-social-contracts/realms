<script lang="ts">
	import MetaTag from '../../utils/MetaTag.svelte';
	import IdentityCard from '../../utils/settings/IdentityCard.svelte';
	import { imagesPath } from '../../utils/variables';
	import { Avatar, Button, Card, Heading, Input, Label, P, Spinner } from 'flowbite-svelte';
	import { FingerprintOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { onMount } from 'svelte';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { principal } from '$lib/stores/auth';
	import { encryptPrivateData, decryptPrivateData } from '$lib/crypto/vetkeys';

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

	// Public data
	let nickname = '';
	let avatarUrl = '';
	let publicSaving = false;
	let publicMessage = '';

	// Private data
	let privateData: Record<string, string> = {};
	let privateSaving = false;
	let privateMessage = '';
	let encryptionAvailable = false;
	let encryptionError = '';

	$: displayAvatar = avatarUrl?.trim() || `https://api.dicebear.com/9.x/glass/svg?seed=${$principal}`;

	onMount(async () => {
		// Load user status
		try {
			const statusResponse = await backend.get_my_user_status();
			if (statusResponse?.success && statusResponse.data?.userGet) {
				const u = statusResponse.data.userGet;
				nickname = u.nickname || '';
				avatarUrl = u.avatar || '';
				if (u.private_data) {
					// Try decrypting with vetKeys first (encrypted hex blob)
					try {
						const decrypted = await decryptPrivateData(backend, u.private_data);
						if (decrypted) {
							privateData = decrypted;
							encryptionAvailable = true;
						} else {
							// Fallback: try parsing as legacy unencrypted JSON
							try {
								privateData = JSON.parse(u.private_data);
							} catch {
								privateData = {};
							}
							// Probe encryption availability
							try {
								await encryptPrivateData(backend, {});
								encryptionAvailable = true;
							} catch {
								encryptionAvailable = false;
							}
						}
					} catch (decErr) {
						console.warn('vetKeys decryption failed, falling back to plaintext:', decErr);
						try {
							privateData = JSON.parse(u.private_data);
						} catch {
							privateData = {};
						}
						encryptionAvailable = false;
						encryptionError = 'Encryption not available on this subnet';
					}
				} else {
					// No private data yet — probe encryption
					try {
						await encryptPrivateData(backend, {});
						encryptionAvailable = true;
					} catch {
						encryptionAvailable = false;
					}
				}
			}
		} catch (err) {
			console.error('Error loading user status:', err);
		}

		try {
			const response = await backend.get_extensions();
			if (response.success && response.data.extensionsList) {
				const extensions = response.data.extensionsList.extensions.map((ext: string) => JSON.parse(ext));

				const providerExtensions = extensions.filter(
					(ext: any) => ext.identity_provider && ext.enabled !== false
				);

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

	async function savePublicProfile() {
		publicSaving = true;
		publicMessage = '';
		try {
			const response = await backend.update_my_public_profile(nickname.trim(), avatarUrl.trim());
			if (response?.success) {
				publicMessage = 'Public profile updated successfully!';
				// Update avatar in header
				window.dispatchEvent(new CustomEvent('profilePictureUpdated', {
					detail: { profilePictureUrl: avatarUrl.trim() }
				}));
			} else {
				publicMessage = 'Failed to update public profile';
			}
		} catch (err) {
			console.error('Error updating public profile:', err);
			publicMessage = 'Error updating public profile';
		} finally {
			publicSaving = false;
		}
	}

	async function savePrivateData() {
		privateSaving = true;
		privateMessage = '';
		try {
			let payload: string;
			if (encryptionAvailable) {
				payload = await encryptPrivateData(backend, privateData);
			} else {
				// Fallback to plaintext if encryption is not available
				payload = JSON.stringify(privateData);
			}
			const response = await backend.update_my_private_data(payload);
			if (response?.success) {
				privateMessage = encryptionAvailable
					? 'Private data encrypted and saved successfully!'
					: 'Private data saved (unencrypted).';
			} else {
				privateMessage = 'Failed to update private data';
			}
		} catch (err) {
			console.error('Error updating private data:', err);
			privateMessage = 'Error updating private data';
		} finally {
			privateSaving = false;
		}
	}
</script>

<MetaTag {path} {description} title={metaTitle} {subtitle} />

<div class="mt-4 space-y-6 px-4 md:px-6">
	<!-- Connected Identities -->
	<Card size="xl">
		<Heading tag="h3" class="mb-2 text-xl font-bold dark:text-white">Connected Identities</Heading>
		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			Verify your identity through external providers for enhanced trust and access.
		</p>
		{#if loading}
			<div class="flex justify-center items-center py-8">
				<Spinner size="8" />
			</div>
		{:else if identityProviders.length > 0}
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				{#each identityProviders as provider}
					{#if provider.verified}
						<IdentityCard
							src={imagesPath(provider.logo)}
							title={provider.name}
							description={provider.description}
							status="Verified"
						/>
					{:else}
						<a href="/extensions/{provider.extensionName}" class="block">
							<div class="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 cursor-pointer transition-colors rounded-lg">
								{#if provider.logo}
									<img src={imagesPath(provider.logo)} alt={provider.name} class="w-24 h-24 object-contain mb-3" />
								{:else}
									<div class="p-3 mb-3 rounded-full bg-blue-100 dark:bg-blue-900">
										<FingerprintOutline class="w-8 h-8 text-blue-600 dark:text-blue-400" />
									</div>
								{/if}
								<Heading tag="h4" class="mb-1 text-lg font-semibold text-gray-900 dark:text-white">{provider.name}</Heading>
								<P class="mb-3 text-sm text-gray-500 dark:text-gray-400 text-center">
									{provider.description}
								</P>
								<Button size="sm" color="blue" class="px-4 py-2">Start Verification</Button>
							</div>
						</a>
					{/if}
				{/each}
			</div>
		{:else}
			<div class="text-center py-6">
				<div class="w-12 h-12 mx-auto mb-3 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
					<FingerprintOutline class="w-6 h-6 text-gray-400 dark:text-gray-500" />
				</div>
				<p class="text-gray-500 dark:text-gray-400">
					No identity verification extensions are currently installed.
				</p>
			</div>
		{/if}
	</Card>

	<!-- Public Data -->
	<Card size="xl">
		<Heading tag="h3" class="mb-2 text-xl font-bold dark:text-white">Public Data</Heading>
		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			This information is visible to all community members.
		</p>
		<div class="flex flex-col sm:flex-row gap-6">
			<div class="flex-shrink-0">
				<Avatar src={displayAvatar} class="h-24 w-24 rounded-lg" size="none" rounded />
			</div>
			<div class="flex-1 space-y-4">
				<div>
					<Label for="nickname" class="mb-2">Nickname</Label>
					<Input id="nickname" bind:value={nickname} placeholder="Enter your nickname" />
				</div>
				<div>
					<Label for="avatar-url" class="mb-2">Avatar URL</Label>
					<Input id="avatar-url" bind:value={avatarUrl} placeholder="https://example.com/your-avatar.jpg" />
				</div>
			</div>
		</div>
		{#if publicMessage}
			<p class="mt-3 text-sm {publicMessage.includes('success') ? 'text-green-600' : 'text-red-600'}">{publicMessage}</p>
		{/if}
		<div class="mt-4">
			<Button size="sm" color="alternative" on:click={savePublicProfile} disabled={publicSaving}>
				{publicSaving ? 'Saving...' : 'Save'}
			</Button>
		</div>
	</Card>

	<!-- Private Data -->
	{#if $realmInfo.privateDataFields.length > 0}
		<Card size="xl">
			<Heading tag="h3" class="mb-2 text-xl font-bold dark:text-white">Private Data</Heading>
				{#if encryptionAvailable}
				<div class="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
					<p class="text-sm text-green-800 dark:text-green-200">
						&#x1f512; Your private data is <strong>end-to-end encrypted</strong> using IC vetKeys. Only you can decrypt it.
					</p>
				</div>
			{:else}
				<div class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
					<p class="text-sm text-yellow-800 dark:text-yellow-200">
						Encryption is not available{encryptionError ? `: ${encryptionError}` : ''}. Data will be stored unencrypted.
					</p>
				</div>
			{/if}
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				{#each $realmInfo.privateDataFields as field}
					<div>
						<Label for="private-{field.key}" class="mb-2">
							{field.label}{#if field.required}<span class="text-red-500 ml-1">*</span>{/if}
						</Label>
						{#if field.type === 'date'}
							<Input id="private-{field.key}" type="date" value={privateData[field.key] || ''} on:input={(e) => { privateData[field.key] = e.currentTarget.value; }} />
						{:else if field.type === 'email'}
							<Input id="private-{field.key}" type="email" value={privateData[field.key] || ''} on:input={(e) => { privateData[field.key] = e.currentTarget.value; }} placeholder="email@example.com" />
						{:else if field.type === 'tel'}
							<Input id="private-{field.key}" type="tel" value={privateData[field.key] || ''} on:input={(e) => { privateData[field.key] = e.currentTarget.value; }} placeholder="+1 234 567 890" />
						{:else if field.type === 'url'}
							<Input id="private-{field.key}" type="url" value={privateData[field.key] || ''} on:input={(e) => { privateData[field.key] = e.currentTarget.value; }} placeholder="https://..." />
						{:else}
							<Input id="private-{field.key}" type="text" value={privateData[field.key] || ''} on:input={(e) => { privateData[field.key] = e.currentTarget.value; }} />
						{/if}
					</div>
				{/each}
			</div>
			{#if privateMessage}
				<p class="mt-3 text-sm {privateMessage.includes('success') ? 'text-green-600' : 'text-red-600'}">{privateMessage}</p>
			{/if}
			<div class="mt-4">
				<Button size="sm" color="alternative" on:click={savePrivateData} disabled={privateSaving}>
					{privateSaving ? 'Saving...' : 'Save'}
				</Button>
			</div>
		</Card>
	{/if}

</div>
