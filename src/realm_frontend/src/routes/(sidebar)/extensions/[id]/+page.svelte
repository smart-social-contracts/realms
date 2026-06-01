<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { Alert } from 'flowbite-svelte';
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
	import { createMarketplaceExtensionBackend } from '$lib/marketplace-extension-backend';
	import type { RealmExtensionContext } from '$lib/realm-extension-sdk';
	import {
		deriveMySharingVetKey,
		unwrapDek,
		aesGcmDecryptWithDek,
		buildSharePlan,
		grantScopeData,
		decryptScopeData
	} from '$lib/crypto/sharing';
	import AccessDenied from '$lib/components/AccessDenied.svelte';
	import { parseAccessError, AccessDeniedError } from '$lib/utils/errors';
	import { sidebarConfig } from '$lib/stores/sidebar';
	import { extensionLoadingMessage } from '$lib/utils/breadcrumb';

	let mountPoint: HTMLDivElement | undefined;
	let status: 'loading' | 'ready' | 'error' | 'access_denied' = 'loading';
	let errorMsg = '';
	let accessDeniedOperation = '';
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

	async function buildContext(id: string, version: string): Promise<RealmExtensionContext> {
		let extensionBackend: typeof backend = backend;
		if (id === 'market_place' && infraConfig.marketplaceCanisterId) {
			extensionBackend = (await createMarketplaceExtensionBackend(
				infraConfig.marketplaceCanisterId,
				infraConfig.fileRegistryCanisterId ?? '',
			)) as typeof backend;
		}

		async function callSync(fn: string, args: Record<string, unknown> = {}): Promise<unknown> {
			const raw = await backend.extension_sync_call(id, fn, JSON.stringify(args));
			const res = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (res?.success === false) {
				const denied = parseAccessError(res);
				if (denied) throw new AccessDeniedError(denied);
				throw new Error(res.response ?? 'extension_sync_call failed');
			}
			if (!res?.response) return res;
			try { return JSON.parse(res.response); } catch { return res.response; }
		}
		async function callAsync(fn: string, args: Record<string, unknown> = {}): Promise<unknown> {
			const raw = await backend.extension_async_call(id, fn, JSON.stringify(args));
			const res = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (res?.success === false) {
				const denied = parseAccessError(res);
				if (denied) throw new AccessDeniedError(denied);
				throw new Error(res.response ?? 'extension_async_call failed');
			}
			if (!res?.response) return res;
			try { return JSON.parse(res.response); } catch { return res.response; }
		}

		return {
			extensionId: id,
			version,
			backend: extensionBackend,
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
			crypto: {
				async decryptWithEnvelope(
					wrappedDekHex: string,
					ciphertext: string,
				): Promise<Record<string, string> | null> {
					if (!wrappedDekHex || !ciphertext) return null;
					try {
						const me = get(principal) as string;
						const { vetKey } = await deriveMySharingVetKey(backend, me);
						const dek = unwrapDek(vetKey, wrappedDekHex);
						const plaintext = await aesGcmDecryptWithDek(dek, ciphertext);
						return JSON.parse(plaintext);
					} catch (e) {
						console.warn('[ctx.crypto] decryptWithEnvelope failed:', e);
						return null;
					}
				},
				async encryptForRecipients(recipients: string[], data: unknown) {
					return buildSharePlan(backend, recipients, data);
				},
				async grantScope(
					scope: string,
					wrappedDeks: Record<string, string>,
					opts?: { previousRecipients?: string[]; keep?: string[] },
				) {
					return grantScopeData(backend, scope, wrappedDeks, opts);
				},
				async decryptScope(scope: string, ciphertext: string) {
					const me = get(principal) as string;
					return decryptScopeData(backend, scope, me, ciphertext);
				},
			},
			ui: {
				AccessDenied,
				accessDeniedOperation: (error: unknown) => {
					if (error instanceof AccessDeniedError) return error.operation;
					const e = error as { name?: string; operation?: string };
					return e?.name === 'AccessDeniedError' ? (e.operation ?? null) : null;
				},
			},
		};
	}

	function cleanupMounted() {
		if (mounted && typeof (mounted as MountResult)?.unmount === 'function') {
			try {
				(mounted as MountResult).unmount!();
			} catch (e) {
				console.warn('unmount error', e);
			}
		}
		mounted = undefined;
		if (mountPoint) {
			mountPoint.innerHTML = '';
		}
	}

	async function loadRuntimeExtension(id: string) {
		cleanupMounted();
		status = 'loading';
		errorMsg = '';

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

			if (!mountPoint) {
				throw new Error('mount point not ready');
			}

			console.debug(`[extension] Loading ${id}@${version}...`);

			await loadExtensionTranslation(id, version, get(locale) || 'en');

			const ctx = await buildContext(id, version);
			mounted = await mountExtension(id, version, mountPoint, ctx);
			console.debug(`[extension] Mounted ${id}@${version}`);
			status = 'ready';
		} catch (e: any) {
			if (e instanceof AccessDeniedError) {
				status = 'access_denied';
				accessDeniedOperation = e.operation;
			} else {
				console.error('Extension load failed:', e);
				status = 'error';
				errorMsg = String(e?.message ?? e);
			}
		}
	}

	$: id = $page.params.id;
	$: loadingMessage = id ? extensionLoadingMessage(id, $sidebarConfig) : 'Loading...';

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
		cleanupMounted();
	});
</script>

<div class="p-4">
	{#if status === 'loading'}
		<div class="flex items-center gap-2 text-gray-500">
			<svg class="animate-spin h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
			</svg>
			<span class="text-sm">{loadingMessage}</span>
		</div>
	{:else if status === 'access_denied'}
		<AccessDenied operation={accessDeniedOperation} />
	{:else if status === 'error'}
		<Alert color="red" class="mb-4">
			<div class="font-semibold">Failed to load extension '{id}'</div>
			<div class="text-sm mt-1">{errorMsg}</div>
		</Alert>
	{/if}

	<div bind:this={mountPoint} data-extension-id={id} class="extension-mount-point"></div>
</div>

<style>
	:global(.extension-mount-point svg[role="status"]),
	:global(.extension-mount-point svg.animate-spin),
	:global(.extension-mount-point svg[class*="animate-spin"]) {
		max-width: 3rem !important;
		max-height: 3rem !important;
		width: auto !important;
		height: auto !important;
	}
</style>
