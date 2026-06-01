<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	// @ts-ignore
	import { backend } from '$lib/canisters';
	import { canisterId as backendCanisterId } from '$lib/declarations/realm_backend';
	// @ts-ignore
	import { principal, isAuthenticated } from '$lib/stores/auth';
	import { userProfiles } from '$lib/stores/profiles';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { notifications, unreadCount, loadNotifications, markAsRead } from '$lib/stores/notifications';
	// @ts-ignore
	import { _, locale } from 'svelte-i18n';
	import { get } from 'svelte/store';
	// @ts-ignore
	import { CONFIG } from '$lib/config.js';
	import { cn } from '$lib/theme/utilities';
	import { mountExtension, resolveExtensionVersion, type MountResult } from '$lib/extension-loader';
	import { loadExtensionTranslation } from '$lib/i18n';
	import { IconSettings, IconX } from '@tabler/icons-svelte';
	import { writable } from 'svelte/store';

	export let open = false;
	export let onClose: () => void = () => {};

	const EXTENSION_ID = 'llm_chat';
	const SETTINGS_PATH = '/extensions/llm_chat';
	const modelLabel = CONFIG?.llmModelLabel ?? 'Default';

	function openSettings() {
		goto(SETTINGS_PATH);
	}

	let mountPoint: HTMLDivElement | undefined;
	let status: 'idle' | 'loading' | 'ready' | 'error' = 'idle';
	let errorMsg = '';
	let mounted: MountResult | void;
	let infraConfig: { fileRegistryCanisterId?: string; marketplaceCanisterId?: string } = {};

	type PageContext = { pathname: string; extensionId: string; title: string };

	// Reactive store so the mounted assistant stays aware of what the user is viewing
	// as they navigate, without needing to be remounted.
	const pageContext = writable<PageContext>(computePageContext($page.url.pathname));
	$: pageContext.set(computePageContext($page.url.pathname));
	$: activeExtensionId = extractActiveExtension($page.url.pathname);

	function extractActiveExtension(pathname: string): string {
		const match = pathname.match(/\/extensions\/([^/]+)/);
		return match?.[1] ?? '';
	}

	function prettifySegment(segment: string): string {
		if (!segment) return '';
		return segment
			.replace(/[-_]/g, ' ')
			.replace(/\b\w/g, (c) => c.toUpperCase());
	}

	function computePageContext(pathname: string): PageContext {
		const extensionId = extractActiveExtension(pathname);
		let title = '';
		if (extensionId) {
			title = prettifySegment(extensionId);
		} else {
			const segments = pathname.split('/').filter(Boolean);
			title = segments.length ? prettifySegment(segments[segments.length - 1]) : 'Home';
		}
		return { pathname, extensionId, title };
	}

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

	function buildContext(id: string, version: string): any {
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
			pageContext,
			context: {
				activeExtensionId,
			},
			sidebarPanel: true,
			settingsPath: SETTINGS_PATH,
			hideModelBar: true,
		};
	}

	function cleanupMounted() {
		if (mounted && typeof (mounted as MountResult)?.unmount === 'function') {
			try { (mounted as MountResult).unmount!(); } catch (e) { /* ignore */ }
		}
		mounted = undefined;
		if (mountPoint) mountPoint.innerHTML = '';
	}

	async function loadAssistant() {
		if (!browser || !mountPoint) return;
		cleanupMounted();
		status = 'loading';
		errorMsg = '';

		try {
			const [version] = await Promise.all([
				resolveExtensionVersion(backend as any, EXTENSION_ID),
				resolveInfraConfig(),
			]);
			if (!version) {
				status = 'error';
				errorMsg = 'AI Assistant extension is not installed.';
				return;
			}
			await loadExtensionTranslation(EXTENSION_ID, version, get(locale as any) || 'en');
			const ctx = buildContext(EXTENSION_ID, version);
			mounted = await mountExtension(EXTENSION_ID, version, mountPoint, ctx);
			status = 'ready';
		} catch (e: any) {
			console.error('[AI Panel] Load failed:', e);
			status = 'error';
			errorMsg = String(e?.message ?? e);
		}
	}

	$: if (open && browser && mountPoint && status === 'idle') {
		loadAssistant();
	}

	onDestroy(() => {
		cleanupMounted();
	});
</script>

<div
	class="fixed top-16 right-0 z-30 h-[calc(100vh-4rem)] w-80 border-l border-gray-200 bg-white transition-transform duration-300 ease-in-out flex flex-col {open ? 'translate-x-0' : 'translate-x-full'}"
>
	<!-- Panel header -->
	<div class="flex items-center gap-2 px-4 py-3 border-b border-gray-200">
		<h3 class="text-sm font-semibold text-gray-700 flex-1 min-w-0 truncate">AI Assistant</h3>
		<span class="text-[11px] text-gray-400 font-medium shrink-0">{modelLabel}</span>
		<button
			on:click={openSettings}
			class="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors shrink-0"
			title="Open AI Assistant settings"
			aria-label="Open AI Assistant settings"
		>
			<IconSettings size={16} />
		</button>
		<button
			on:click={onClose}
			class="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors shrink-0"
			aria-label="Close AI Assistant"
		>
			<IconX size={18} />
		</button>
	</div>

	<!-- Extension mount point -->
	<div class="flex-1 min-h-0 overflow-hidden flex flex-col">
		{#if status === 'loading'}
			<div class="flex items-center justify-center h-32 text-gray-500">
				<div class="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-700"></div>
				<span class="ml-2 text-sm">Loading...</span>
			</div>
		{:else if status === 'error'}
			<div class="p-4 text-sm text-red-600">{errorMsg}</div>
		{/if}
		<div bind:this={mountPoint} class="flex-1 min-h-0 h-full"></div>
	</div>
</div>
