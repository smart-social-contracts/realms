<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { Alert } from 'flowbite-svelte';
	import { backend, quarterBackend } from '$lib/canisters';
	import { canisterId as backendCanisterId } from '$lib/declarations/realm_backend';
	import { principal, isAuthenticated } from '$lib/stores/auth';
	import { userProfiles } from '$lib/stores/profiles';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { notifications, unreadCount, loadNotifications, markAsRead } from '$lib/stores/notifications';
	import { _, locale } from 'svelte-i18n';
	import { get } from 'svelte/store';
	import { CONFIG } from '$lib/config.js';
	import { cn } from '$lib/theme/utilities';
	import {
		mountExtension,
		mountSandboxedExtension,
		resolveExtensionVersion,
		type MountResult,
		type SandboxMountResult
	} from '$lib/extension-loader';
	import { isPrivilegedExtension } from '$lib/extension-privileged';
	import { loadExtensionTranslation } from '$lib/i18n';
	import { createMarketplaceExtensionBackend } from '$lib/marketplace-extension-backend';
	import type { RealmExtensionContext } from '$lib/realm-extension-sdk';
	import { getExtensionManifestWithRetry } from '$lib/utils/extension-manifest';
	import { resolveExtensionMountMode } from '$lib/utils/extension-runtime-mode';
	import BridgeModalHost from '$lib/components/BridgeModalHost.svelte';
	import type { HostRealmInfo, HostState } from '@realmsgos/extension-bridge';
	import BridgeToastHost from '$lib/components/BridgeToastHost.svelte';
	import {
		deriveMySharingVetKey,
		unwrapDek,
		aesGcmDecryptWithDek,
		buildSharePlan,
		grantScopeData,
		decryptScopeData
	} from '$lib/crypto/sharing';
	import AccessDenied from '$lib/components/AccessDenied.svelte';
	import MonacoEditor from '$lib/components/MonacoEditor.svelte';
	import MonacoDiffEditor from '$lib/components/MonacoDiffEditor.svelte';
	import { parseAccessError, AccessDeniedError, formatDelegationExpiredError } from '$lib/utils/errors';
	import { sidebarConfig } from '$lib/stores/sidebar';
	import { extensionLoadingMessage } from '$lib/utils/breadcrumb';
	import { createHostContext } from '$lib/host-bridge';

	export let extensionId: string;

	const FULL_BLEED_EXTENSIONS = new Set(['codex_viewer', 'zone_selector', 'land_registry']);
	const PANE_BLEED_EXTENSIONS = new Set(['public_dashboard']);

	let mountPoint: HTMLDivElement | undefined;
	let status: 'loading' | 'ready' | 'error' | 'access_denied' | 'sdk_mismatch' = 'loading';
	let errorMsg = '';
	let errorRetryable = false;
	let accessDeniedOperation = '';
	let mounted: MountResult | SandboxMountResult | void;
	let sandboxed = false;
	let runtimeDenied: { operation: string; message: string } | null = null;

	function readHostTheme(): 'light' | 'dark' {
		if (!browser) return 'light';
		return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
	}

	function realmInfoSnapshot(): HostRealmInfo {
		const info = get(realmInfo);
		return {
			name: info.name,
			welcomeMessage: info.welcomeMessage,
			manifesto: info.manifesto,
			isQuarter: info.isQuarter,
			parentRealmCanisterId: info.parentRealmCanisterId,
			logoUrl: info.logoUrl || undefined
		};
	}

	function buildSandboxHostState(): HostState {
		return {
			principal: get(principal) as string,
			locale: get(locale) || 'en',
			theme: readHostTheme(),
			realmInfo: realmInfoSnapshot()
		};
	}

	function subscribeSandboxHostState(onChange: (state: HostState) => void): () => void {
		const unsubs = [
			principal.subscribe(() => onChange(buildSandboxHostState())),
			realmInfo.subscribe(() => onChange(buildSandboxHostState())),
			locale.subscribe(() => onChange(buildSandboxHostState()))
		];

		if (browser) {
			const onDark = (event: Event) => {
				const detail = (event as CustomEvent<boolean>).detail;
				onChange({ ...buildSandboxHostState(), theme: detail ? 'dark' : 'light' });
			};
			document.addEventListener('dark', onDark);
			unsubs.push(() => document.removeEventListener('dark', onDark));

			const observer = new MutationObserver(() => onChange(buildSandboxHostState()));
			observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
			unsubs.push(() => observer.disconnect());
		}

		onChange(buildSandboxHostState());
		return () => unsubs.forEach((u) => u());
	}

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
				marketplaceCanisterId: mp?.canister_id ?? ''
			};
		} catch {
			infraConfig = {};
		}
	}

	async function buildContext(id: string, version: string): Promise<RealmExtensionContext> {
		let extensionBackend: typeof backend = quarterBackend;
		let marketplaceAdapter: Awaited<ReturnType<typeof createMarketplaceExtensionBackend>> | null =
			null;
		if (
			(id === 'market_place' || id === 'package_manager') &&
			infraConfig.marketplaceCanisterId
		) {
			marketplaceAdapter = await createMarketplaceExtensionBackend(
				infraConfig.marketplaceCanisterId,
				infraConfig.fileRegistryCanisterId ?? ''
			).catch(() => null);
		}
		if (id === 'market_place' && marketplaceAdapter) {
			extensionBackend = marketplaceAdapter as unknown as typeof backend;
		}

		function unwrapCallResult(raw: unknown, label: string): unknown {
			const res = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (res?.success === false) {
				const denied = parseAccessError(res);
				if (denied) {
					runtimeDenied = denied;
					throw new AccessDeniedError(denied);
				}
				throw new Error(res.response ?? `${label} failed`);
			}
			if (!res?.response) return res;
			let inner: unknown;
			try {
				inner = JSON.parse(res.response);
			} catch {
				return res.response;
			}
			const denied = parseAccessError(inner);
			if (denied) {
				runtimeDenied = denied;
			}
			return inner;
		}
		async function callSync(fn: string, args: Record<string, unknown> = {}): Promise<unknown> {
			let raw: string;
			try {
				raw = await extensionBackend.extension_sync_call(id, fn, JSON.stringify(args));
			} catch (e) {
				const friendly = formatDelegationExpiredError(e);
				if (friendly) throw new Error(friendly);
				throw e;
			}
			return unwrapCallResult(raw, 'extension_sync_call');
		}
		async function callAsync(fn: string, args: Record<string, unknown> = {}): Promise<unknown> {
			let raw: string;
			try {
				raw = await extensionBackend.extension_async_call(id, fn, JSON.stringify(args));
			} catch (e) {
				const friendly = formatDelegationExpiredError(e);
				if (friendly) throw new Error(friendly);
				throw e;
			}
			return unwrapCallResult(raw, 'extension_async_call');
		}

		return {
			...createHostContext(),
			extensionId: id,
			version,
			backend: extensionBackend,
			marketplace: marketplaceAdapter,
			callSync,
			callAsync,
			principal,
			isAuthenticated,
			userProfiles,
			realmInfo,
			config: {
				...CONFIG,
				canisterId: backendCanisterId?.toString?.() ?? '',
				aiAssistantEnabled: get(realmInfo).aiAssistantEnabled !== false,
				...infraConfig
			},
			navigate: goto,
			t: _,
			locale,
			notifications: {
				items: notifications,
				unreadCount,
				load: loadNotifications,
				markAsRead
			},
			theme: { cn },
			crypto: {
				async decryptWithEnvelope(
					wrappedDekHex: string,
					ciphertext: string
				): Promise<Record<string, string> | null> {
					if (!wrappedDekHex || !ciphertext) return null;
					try {
						const me = get(principal) as string;
						const { vetKey } = await deriveMySharingVetKey(quarterBackend, me);
						const dek = unwrapDek(vetKey, wrappedDekHex);
						const plaintext = await aesGcmDecryptWithDek(dek, ciphertext);
						return JSON.parse(plaintext);
					} catch (e) {
						console.warn('[ctx.crypto] decryptWithEnvelope failed:', e);
						return null;
					}
				},
				async encryptForRecipients(recipients: string[], data: unknown) {
					return buildSharePlan(quarterBackend, recipients, data);
				},
				async grantScope(
					scope: string,
					wrappedDeks: Record<string, string>,
					opts?: { previousRecipients?: string[]; keep?: string[] }
				) {
					return grantScopeData(quarterBackend, scope, wrappedDeks, opts);
				},
				async decryptScope(scope: string, ciphertext: string) {
					const me = get(principal) as string;
					return decryptScopeData(quarterBackend, scope, me, ciphertext);
				}
			},
			ui: {
				AccessDenied,
				MonacoEditor,
				MonacoDiffEditor,
				accessDeniedOperation: (error: unknown) => {
					if (error instanceof AccessDeniedError) return error.operation;
					const e = error as { name?: string; operation?: string };
					return e?.name === 'AccessDeniedError' ? (e.operation ?? null) : null;
				}
			}
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
		sandboxed = false;
		if (mountPoint) {
			mountPoint.innerHTML = '';
		}
	}

	async function ensureMountPoint(): Promise<HTMLDivElement> {
		await tick();
		if (mountPoint) return mountPoint;
		await tick();
		if (mountPoint) return mountPoint;
		throw new Error('mount point not ready');
	}

	async function loadRuntimeExtension(id: string) {
		cleanupMounted();
		status = 'loading';
		errorMsg = '';
		errorRetryable = false;
		runtimeDenied = null;

		try {
			const [version, manifest] = await Promise.all([
				resolveExtensionVersion(backend as any, id),
				getExtensionManifestWithRetry(id),
				resolveInfraConfig()
			]);

			const mountMode = resolveExtensionMountMode(version, manifest, isPrivilegedExtension(id));
			if (mountMode.kind === 'not_installed') {
				status = 'error';
				errorMsg = `Extension '${id}' is not installed on this realm_backend.`;
				return;
			}
			if (mountMode.kind === 'manifest_unavailable') {
				status = 'error';
				errorMsg = `Extension manifest unavailable for '${id}'. Please retry.`;
				errorRetryable = true;
				return;
			}
			if (mountMode.kind === 'not_privileged') {
				status = 'error';
				errorMsg = `Extension '${id}' is not on the privileged allowlist and must declare runtime:"sandboxed".`;
				return;
			}

			const mountEl = await ensureMountPoint();

			console.debug(`[extension] Loading ${id}@${version}...`);

			await loadExtensionTranslation(id, version, get(locale) || 'en');

			if (mountMode.kind === 'sandboxed') {
				sandboxed = true;
				const ctx = await buildContext(id, version);
				mounted = await mountSandboxedExtension(id, version, mountEl, {
					manifest: {
						sdk_version: manifest?.sdk_version as string | undefined,
						capabilities: manifest?.capabilities as string[] | undefined,
						entry_access: manifest?.entry_access as
							| { functions?: Record<string, string> }
							| undefined
					},
					callSync: ctx.callSync,
					callAsync: ctx.callAsync,
					navigate: ctx.navigate,
					getHostState: buildSandboxHostState,
					subscribeHostState: subscribeSandboxHostState,
					onHandshakeFailed: (reason) => {
						cleanupMounted();
						if (String(reason).includes('SDK version mismatch')) {
							status = 'sdk_mismatch';
							errorMsg = reason;
						} else {
							status = 'error';
							errorMsg = reason;
						}
					}
				});
				await (mounted as SandboxMountResult).ready;
				console.debug(`[extension] Sandboxed bridge ready ${id}@${version}`);
			} else {
				const ctx = await buildContext(id, version);
				mounted = await mountExtension(id, version, mountEl, ctx);
				console.debug(`[extension] Mounted ${id}@${version}`);
			}
			status = 'ready';
		} catch (e: any) {
			cleanupMounted();
			const denied =
				e instanceof AccessDeniedError ? { operation: e.operation } : parseAccessError(e);
			if (denied) {
				status = 'access_denied';
				accessDeniedOperation = denied.operation;
			} else if (String(e?.message ?? e).includes('SDK version mismatch')) {
				status = 'sdk_mismatch';
				errorMsg = String(e?.message ?? e);
			} else {
				console.error('Extension load failed:', e);
				status = 'error';
				errorMsg = String(e?.message ?? e);
			}
		}
	}

	$: loadingMessage = extensionId
		? extensionLoadingMessage(extensionId, $sidebarConfig)
		: 'Loading...';

	$: extensionHostClass = FULL_BLEED_EXTENSIONS.has(extensionId)
		? 'extension-host-fullbleed'
		: PANE_BLEED_EXTENSIONS.has(extensionId)
			? 'w-full min-w-0'
			: 'p-4';

	let lastLoadedId: string | undefined;
	$: if (browser && extensionId && extensionId !== lastLoadedId && mountPoint) {
		lastLoadedId = extensionId;
		loadRuntimeExtension(extensionId);
	}

	onMount(() => {
		if (extensionId && mountPoint) {
			lastLoadedId = extensionId;
			loadRuntimeExtension(extensionId);
		}
	});

	onDestroy(() => {
		cleanupMounted();
	});
</script>

<div class={extensionHostClass}>
	{#if status === 'loading'}
		<div class="flex items-center gap-2 text-gray-500">
			<svg
				class="animate-spin h-5 w-5 text-gray-400"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
			>
				<circle
					class="opacity-25"
					cx="12"
					cy="12"
					r="10"
					stroke="currentColor"
					stroke-width="4"
				></circle>
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				></path>
			</svg>
			<span class="text-sm">{loadingMessage}</span>
		</div>
	{:else if status === 'access_denied'}
		<AccessDenied operation={accessDeniedOperation} onRetry={() => loadRuntimeExtension(extensionId)} />
	{:else if status === 'ready' && runtimeDenied}
		<AccessDenied
			operation={runtimeDenied.operation}
			message={runtimeDenied.message}
			onRetry={() => loadRuntimeExtension(extensionId)}
		/>
	{:else if status === 'sdk_mismatch'}
		<Alert color="red" class="mb-4">
			<div class="font-semibold">Extension SDK version mismatch</div>
			<div class="text-sm mt-1">{errorMsg}</div>
			<div class="text-sm mt-2 text-gray-600 dark:text-gray-400">
				This sandboxed extension requires a bridge protocol version incompatible with the host.
				Update the extension or contact the publisher.
			</div>
		</Alert>
	{:else if status === 'error'}
		<Alert color="red" class="mb-4">
			<div class="font-semibold">Failed to load extension '{extensionId}'</div>
			<div class="text-sm mt-1">{errorMsg}</div>
			{#if errorRetryable}
				<button
					type="button"
					class="mt-3 text-sm font-medium text-red-800 underline dark:text-red-200"
					onclick={() => loadRuntimeExtension(extensionId)}
				>
					Retry
				</button>
			{/if}
		</Alert>
	{/if}

	<div
		bind:this={mountPoint}
		data-extension-id={extensionId}
		class="extension-mount-point"
		class:hidden={!!runtimeDenied}
	></div>
</div>

{#if sandboxed && status === 'ready'}
	<BridgeModalHost />
	<BridgeToastHost />
{/if}

<style>
	.extension-host-fullbleed {
		flex: 1;
		height: 100%;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.extension-host-fullbleed :global(.extension-mount-point) {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.extension-mount-point.hidden,
	.extension-host-fullbleed :global(.extension-mount-point.hidden) {
		display: none !important;
	}

	:global(.extension-mount-point svg[role='status']),
	:global(.extension-mount-point svg.animate-spin),
	:global(.extension-mount-point svg[class*='animate-spin']) {
		max-width: 3rem !important;
		max-height: 3rem !important;
		width: auto !important;
		height: auto !important;
	}
</style>
