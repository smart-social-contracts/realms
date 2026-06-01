<script lang="ts">
	import MetaTag from '../../utils/MetaTag.svelte';
	import IdentityCard from '../../utils/settings/IdentityCard.svelte';
	import { imagesPath } from '../../utils/variables';
	import { Avatar, Button, Card, Heading, Input, Label, P, Spinner, Toggle } from 'flowbite-svelte';
	import { FingerprintOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { principal } from '$lib/stores/auth';
	import { decryptPrivateData } from '$lib/crypto/vetkeys';
	import {
		buildSharePlan,
		decryptScopeData,
		deriveMySharingVetKey,
		grantScopeData,
		userScope
	} from '$lib/crypto/sharing';

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

	// Per-section loading states
	let publicDataLoaded = false;
	let privateDataLoaded = false;
	let identitiesLoading = true;
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

	// Data sharing (consent-based, via vetKey crypto groups — issue #215)
	interface ShareAudience {
		id: string;
		label: string;
		type: string;
		principals: string[];
	}
	let sharingLoaded = false;
	let sharingSaving = false;
	let sharingMessage = '';
	let audiences: ShareAudience[] = [];
	let selectedAudiences: Record<string, boolean> = {};
	let currentlySharedWith: string[] = [];

	const privateDataFields = [
		{ key: 'first_name', label: 'First Name', type: 'text' },
		{ key: 'last_name', label: 'Last Name', type: 'text' },
		{ key: 'photo', label: 'Photo URL', type: 'url' },
		{ key: 'birth_date', label: 'Date of Birth', type: 'date' },
		{ key: 'address', label: 'Address', type: 'text' },
		{ key: 'email', label: 'Email', type: 'email' },
		{ key: 'phone', label: 'Phone Number', type: 'tel' }
	];

	$: displayAvatar = avatarUrl?.trim() || `https://api.dicebear.com/9.x/glass/svg?seed=${$principal}`;

	onMount(() => {
		loadPublicData();
		loadPrivateData();
		loadIdentityProviders();
		loadSharingStatus();
	});

	async function probeEncryption(): Promise<boolean> {
		try {
			await deriveMySharingVetKey(backend, get(principal) as string);
			return true;
		} catch (e) {
			console.warn('Encryption probe failed:', e);
			encryptionError = 'Encryption not available on this subnet';
			return false;
		}
	}

	async function loadPublicData() {
		try {
			const statusResponse = await backend.get_my_user_status();
			if (statusResponse?.success && statusResponse.data?.userGet) {
				const u = statusResponse.data.userGet;
				nickname = u.nickname || '';
				avatarUrl = u.avatar || '';
			}
		} catch (err) {
			console.error('Error loading public data:', err);
		} finally {
			publicDataLoaded = true;
		}
	}

	async function loadPrivateData() {
		try {
			const statusResponse = await backend.get_my_user_status();
			if (statusResponse?.success && statusResponse.data?.userGet) {
				const u = statusResponse.data.userGet;
				const owner = get(principal) as string;
				if (u.private_data) {
					// 1. Preferred: DEK + envelope model (supports sharing).
					const decrypted = await decryptScopeData<Record<string, string>>(
						backend,
						userScope(owner),
						owner,
						u.private_data
					);
					if (decrypted) {
						privateData = decrypted;
						encryptionAvailable = true;
					} else {
						// 2. Legacy: data encrypted directly with the user's vetKey.
						let legacy: Record<string, string> | null = null;
						try {
							legacy = await decryptPrivateData(backend, u.private_data);
						} catch (decErr) {
							console.warn('Legacy vetKeys decryption failed:', decErr);
						}
						if (legacy) {
							privateData = legacy;
							encryptionAvailable = true;
						} else {
							// 3. Plaintext / unknown — surface raw JSON if parseable.
							try {
								privateData = JSON.parse(u.private_data);
							} catch {
								privateData = {};
							}
							encryptionAvailable = await probeEncryption();
						}
					}
				} else {
					encryptionAvailable = await probeEncryption();
				}
			}
		} catch (err) {
			console.error('Error loading private data:', err);
		} finally {
			privateDataLoaded = true;
		}
	}

	async function loadSharingStatus() {
		try {
			const owner = get(principal) as string;
			const scope = userScope(owner);

			const envResp = await backend.crypto_list_scope_envelopes(scope);
			const envs = envResp?.data?.envelopeList?.envelopes ?? [];
			currentlySharedWith = envs
				.map((e: any) => e.principal_id)
				.filter((p: string) => p && p !== owner);

			const audResp = await backend.list_share_audiences();
			if (audResp?.success && audResp.data?.message) {
				const parsed = JSON.parse(audResp.data.message);
				audiences = (parsed.audiences ?? []).filter(
					(a: ShareAudience) => (a.principals?.length ?? 0) > 0
				);
			}

			// An audience is shown as selected if at least one of its members
			// (other than the owner) currently holds an envelope for this scope.
			const sharedSet = new Set(currentlySharedWith);
			const sel: Record<string, boolean> = {};
			for (const a of audiences) {
				sel[a.id] = a.principals.some((p) => p !== owner && sharedSet.has(p));
			}
			selectedAudiences = sel;
		} catch (e) {
			console.warn('loadSharingStatus failed:', e);
		} finally {
			sharingLoaded = true;
		}
	}

	function selectedRecipients(owner: string): string[] {
		const set = new Set<string>();
		for (const a of audiences) {
			if (selectedAudiences[a.id]) {
				for (const p of a.principals) if (p && p !== owner) set.add(p);
			}
		}
		return Array.from(set);
	}

	async function loadIdentityProviders() {
		try {
			const response = await backend.get_extensions();
			if (response.success && response.data.extensionsList) {
				const extensions = response.data.extensionsList.extensions.map((ext: string) => JSON.parse(ext));

				const providerExtensions = extensions.filter(
					(ext: any) => ext.identity_provider && ext.enabled !== false
				);

				identityProviders = providerExtensions.map((ext: any) => ({
					extensionName: ext.name,
					name: ext.identity_provider.name || ext.name,
					providerUrl: ext.identity_provider.provider_url || '',
					logo: ext.identity_provider.logo || '',
					description: ext.identity_provider.description || ext.description || '',
					verified: false
				}));

				Promise.all(
					providerExtensions.map(async (ext: any, i: number) => {
						try {
							const statusResponse = await backend.extension_sync_call({
								extension_name: ext.name,
								function_name: 'get_identity_status',
								args: ''
							});
							if (statusResponse.success) {
								const statusData = JSON.parse(statusResponse.response);
								if (statusData.verified) {
									identityProviders[i] = { ...identityProviders[i], verified: true };
									identityProviders = identityProviders;
								}
							}
						} catch (err) {
							console.error(`Error checking identity status for ${ext.name}:`, err);
						}
					})
				);
			}
		} catch (error) {
			console.error('Error loading identity providers:', error);
		} finally {
			identitiesLoading = false;
		}
	}

	async function savePublicProfile() {
		publicSaving = true;
		publicMessage = '';
		try {
			const response = await backend.update_my_public_profile(nickname.trim(), avatarUrl.trim());
			if (response?.success) {
				publicMessage = 'Public profile updated successfully!';
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
			if (!encryptionAvailable) {
				const response = await backend.update_my_private_data(JSON.stringify(privateData));
				privateMessage = response?.success
					? 'Private data saved (unencrypted).'
					: 'Failed to update private data';
				return;
			}

			const owner = get(principal) as string;
			const scope = userScope(owner);
			const recipients = selectedRecipients(owner);

			// Encrypt with a fresh DEK and wrap it for the owner + each recipient.
			// The owner is always included so the new ciphertext stays self-readable.
			const plan = await buildSharePlan(backend, [owner, ...recipients], privateData);

			const response = await backend.update_my_private_data(plan.ciphertext);
			if (!response?.success) {
				privateMessage = 'Failed to update private data';
				return;
			}

			// Persist grants (and revoke anyone deselected) in batch calls; never
			// revoke the owner.
			const granted = await grantScopeData(backend, scope, plan.wrappedDeks, {
				previousRecipients: currentlySharedWith,
				keep: [owner]
			});
			currentlySharedWith = granted.filter((p) => p !== owner);

			privateMessage =
				recipients.length > 0
					? `Private data encrypted, saved, and shared with ${recipients.length} recipient${recipients.length === 1 ? '' : 's'}.`
					: 'Private data encrypted and saved successfully!';
		} catch (err) {
			console.error('Error updating private data:', err);
			privateMessage = 'Error updating private data';
		} finally {
			privateSaving = false;
		}
	}

	async function saveSharingSettings() {
		if (!encryptionAvailable) return;
		sharingSaving = true;
		sharingMessage = '';
		try {
			await savePrivateData();
			sharingMessage = 'Sharing settings updated.';
		} catch {
			sharingMessage = 'Failed to update sharing settings.';
		} finally {
			sharingSaving = false;
		}
	}
</script>

<MetaTag {path} {description} title={metaTitle} {subtitle} />

<div class="mt-4 space-y-6 px-4 md:px-6">
	<!-- Public Data -->
	<Card size="xl">
		<Heading tag="h3" class="mb-2 text-xl font-bold dark:text-white">Public Data</Heading>
		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			This information is visible to all community members.
		</p>
		{#if !publicDataLoaded}
			<div class="flex justify-center items-center py-8">
				<Spinner size="6" />
			</div>
		{:else}
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
		{/if}
	</Card>

	<!-- Private Data -->
	<Card size="xl">
		<Heading tag="h3" class="mb-2 text-xl font-bold dark:text-white">Private Data</Heading>
		{#if !privateDataLoaded}
			<div class="flex justify-center items-center py-8">
				<Spinner size="6" />
				<span class="ml-3 text-sm text-gray-500">Decrypting private data...</span>
			</div>
		{:else}
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
				{#each privateDataFields as field}
					<div>
						<Label for="private-{field.key}" class="mb-2">
							{field.label}
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
		{/if}
	</Card>

	<!-- Connected Identities -->
	<Card size="xl">
		<Heading tag="h3" class="mb-2 text-xl font-bold dark:text-white">Connected Identities</Heading>
		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			Verify your identity through external providers for enhanced trust and access.
		</p>
		{#if identitiesLoading}
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

	<!-- Data Sharing -->
	<Card size="xl">
		<Heading tag="h3" class="mb-2 text-xl font-bold dark:text-white">Data Sharing</Heading>
		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			Choose who may read your private data — realm administrators and/or specific
			departments. Sharing is consent-based: your data stays encrypted, and access is
			granted by wrapping your encryption key for each recipient. You can revoke at any time.
		</p>
		{#if !sharingLoaded}
			<div class="flex justify-center items-center py-6">
				<Spinner size="6" />
			</div>
		{:else if !encryptionAvailable}
			<div class="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
				<p class="text-sm text-yellow-800 dark:text-yellow-200">
					Sharing requires encryption, which is not available on this subnet.
				</p>
			</div>
		{:else if audiences.length === 0}
			<div class="p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
				<p class="text-sm text-gray-600 dark:text-gray-300">
					There are no administrators or departments available to share with yet.
				</p>
			</div>
		{:else}
			<ul class="space-y-2">
				{#each audiences as audience (audience.id)}
					<li class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
						<div>
							<p class="text-sm font-medium text-gray-900 dark:text-white">
								{audience.label}
								{#if audience.type === 'department'}
									<span class="ml-1 text-xs font-normal text-gray-400">(department)</span>
								{/if}
							</p>
							<p class="text-xs text-gray-500 dark:text-gray-400">
								{audience.principals.length} member{audience.principals.length === 1 ? '' : 's'} would gain read access.
							</p>
						</div>
						<Toggle bind:checked={selectedAudiences[audience.id]} disabled={sharingSaving || privateSaving} />
					</li>
				{/each}
			</ul>

			<div class="mt-4 flex items-center gap-3">
				<Button size="sm" color="blue" on:click={saveSharingSettings} disabled={sharingSaving || privateSaving}>
					{sharingSaving ? 'Updating…' : 'Save sharing settings'}
				</Button>
				{#if sharingMessage}
					<span class="text-sm {sharingMessage.includes('updated') ? 'text-green-600' : 'text-red-600'}">{sharingMessage}</span>
				{/if}
			</div>

			{#if currentlySharedWith.length > 0}
				<div class="mt-3">
					<p class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
						Currently shared with ({currentlySharedWith.length})
					</p>
					<ul class="space-y-1 max-h-32 overflow-y-auto">
						{#each currentlySharedWith as p}
							<li class="text-xs font-mono text-gray-600 dark:text-gray-300 break-all">{p}</li>
						{/each}
					</ul>
				</div>
			{/if}
		{/if}
	</Card>

</div>
