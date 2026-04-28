<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { Spinner, Alert } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	import { canisterId as backendCanisterId } from '$lib/declarations/realm_backend';
	import { principal, isAuthenticated } from '$lib/stores/auth';
	import { userProfiles } from '$lib/stores/profiles';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { notifications, unreadCount, loadNotifications, markAsRead } from '$lib/stores/notifications';
	import { _, locale } from 'svelte-i18n';
	import { CONFIG } from '$lib/config.js';
	import { cn } from '$lib/theme/utilities';
	import { mountExtension, resolveExtensionVersion, type MountResult } from '$lib/extension-loader';
	import type { RealmExtensionContext } from '$lib/realm-extension-sdk';

	let mountPoint: HTMLDivElement | undefined;
	let status: 'loading' | 'ready' | 'error' = 'loading';
	let errorMsg = '';
	let debugInfo = '';
	let mounted: MountResult | void;

	function buildContext(id: string, version: string): RealmExtensionContext {
		return {
			extensionId: id,
			version,
			backend,
			principal,
			isAuthenticated,
			userProfiles,
			realmInfo,
			config: {
				...CONFIG,
				canisterId: backendCanisterId?.toString?.() ?? '',
			},
			navigate: goto,
			t: _,
			locale,
			notifications: {
				items: notifications,
				unreadCount,
				load: loadNotifications,
				markAsRead,
			},
			theme: { cn },
		};
	}

	async function loadRuntimeExtension(id: string) {
		status = 'loading';
		errorMsg = '';
		debugInfo = '';

		try {
			const version = await resolveExtensionVersion(backend as any, id);
			if (!version) {
				status = 'error';
				errorMsg = `Extension '${id}' is not installed on this realm_backend.`;
				return;
			}
			debugInfo = `Loading ${id}@${version}...`;

			if (!mountPoint) {
				throw new Error('mount point not ready');
			}

			const ctx = buildContext(id, version);
			mounted = await mountExtension(id, version, mountPoint, ctx);
			debugInfo = `Mounted ${id}@${version}`;
			status = 'ready';
		} catch (e: any) {
			console.error('Extension load failed:', e);
			status = 'error';
			errorMsg = String(e?.message ?? e);
		}
	}

	$: id = $page.params.id;

	let lastLoadedId: string | undefined;
	$: if (browser && id && id !== lastLoadedId && mountPoint) {
		lastLoadedId = id;
		loadRuntimeExtension(id);
	}

	onMount(() => {
		if (id && mountPoint) {
			lastLoadedId = id;
			loadRuntimeExtension(id);
		}
	});

	onDestroy(() => {
		if (mounted && typeof (mounted as MountResult)?.unmount === 'function') {
			try {
				(mounted as MountResult).unmount!();
			} catch (e) {
				console.warn('unmount error', e);
			}
		}
	});
</script>

<div class="p-4">
	{#if status === 'loading'}
		<div class="flex items-center gap-2 text-gray-600">
			<Spinner size="5" />
			<span>{debugInfo || 'Loading extension...'}</span>
		</div>
	{:else if status === 'error'}
		<Alert color="red" class="mb-4">
			<div class="font-semibold">Failed to load extension '{id}'</div>
			<div class="text-sm mt-1">{errorMsg}</div>
		</Alert>
	{/if}

	<div bind:this={mountPoint} data-extension-id={id} class="extension-mount-point"></div>
</div>
