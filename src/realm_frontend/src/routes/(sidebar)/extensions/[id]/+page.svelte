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
	import { get } from 'svelte/store';
	import { CONFIG } from '$lib/config.js';
	import { cn } from '$lib/theme/utilities';
	import { mountExtension, resolveExtensionVersion, type MountResult } from '$lib/extension-loader';
	import { loadExtensionTranslation } from '$lib/i18n';
	import type { RealmExtensionContext } from '$lib/realm-extension-sdk';

	let mountPoint: HTMLDivElement | undefined;
	let status: 'loading' | 'ready' | 'error' = 'loading';
	let errorMsg = '';
	let debugInfo = '';
	let mounted: MountResult | void;

	let infraConfig: { fileRegistryCanisterId?: string; marketplaceCanisterId?: string } = {};

	async function resolveInfraConfig() {
		try {
			const raw = await backend.status();
			const resp = typeof raw === 'string' ? JSON.parse(raw) : raw;
			const canisters: { canister_id: string; canister_type: string }[] =
				resp?.data?.status?.canisters ?? [];
			const fr = canisters.find((c) => c.canister_type === 'file_registry');
			const mp = canisters.find((c) => c.canister_type === 'marketplace');
			infraConfig = {
				fileRegistryCanisterId: fr?.canister_id ?? '',
				marketplaceCanisterId: mp?.canister_id ?? '',
			};
		} catch {
			infraConfig = {};
		}
	}

	function buildContext(id: string, version: string): RealmExtensionContext {
		async function callSync(fn: string, args: Record<string, unknown> = {}): Promise<unknown> {
			const raw = await backend.extension_sync_call(id, fn, JSON.stringify(args));
			const res = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (res?.success === false) throw new Error(res.response ?? 'extension_sync_call failed');
			if (!res?.response) return res;
			try { return JSON.parse(res.response); } catch { return res.response; }
		}
		async function callAsync(fn: string, args: Record<string, unknown> = {}): Promise<unknown> {
			const raw = await backend.extension_async_call(id, fn, JSON.stringify(args));
			const res = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (res?.success === false) throw new Error(res.response ?? 'extension_async_call failed');
			if (!res?.response) return res;
			try { return JSON.parse(res.response); } catch { return res.response; }
		}

		return {
			extensionId: id,
			version,
			backend,
			callSync,
			callAsync,
			principal,
			isAuthenticated,
			userProfiles,
			realmInfo,
			config: {
				...CONFIG,
				canisterId: backendCanisterId?.toString?.() ?? '',
				...infraConfig,
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
			const [version] = await Promise.all([
				resolveExtensionVersion(backend as any, id),
				resolveInfraConfig(),
			]);
			if (!version) {
				status = 'error';
				errorMsg = `Extension '${id}' is not installed on this realm_backend.`;
				return;
			}
			debugInfo = `Loading ${id}@${version}...`;

			if (!mountPoint) {
				throw new Error('mount point not ready');
			}

			await loadExtensionTranslation(id, version, get(locale) || 'en');

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
