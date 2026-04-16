<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { Spinner, Alert } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	import { principal, isAuthenticated } from '$lib/stores/auth';
	import { mountExtension, resolveExtensionVersion, type MountResult } from '$lib/extension-loader';

	let mountPoint: HTMLDivElement | undefined;
	let status: 'loading' | 'ready' | 'error' = 'loading';
	let errorMsg = '';
	let debugInfo = '';
	let mounted: MountResult | void;

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
			debugInfo = `Loading ${id}@${version} from file_registry...`;

			if (!mountPoint) {
				throw new Error('mount point not ready');
			}
			mounted = await mountExtension(id, version, mountPoint, {
				backend,
				extensionId: id,
				version,
				// Extensions that need to identify the current user (e.g.
				// member_dashboard) receive principal + auth state as props.
				// Bundle MUST read these as props, not reach into host stores.
				principal: $principal || '',
				isAuthenticated: $isAuthenticated,
			});
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
	<h1 class="text-2xl font-bold mb-4">Extension: {id}</h1>

	{#if status === 'loading'}
		<div class="flex items-center gap-2 text-gray-600">
			<Spinner size="5" />
			<span>{debugInfo || 'Resolving extension...'}</span>
		</div>
	{:else if status === 'error'}
		<Alert color="red" class="mb-4">
			<div class="font-semibold">Failed to load extension '{id}'</div>
			<div class="text-sm mt-1">{errorMsg}</div>
		</Alert>
	{/if}

	<div bind:this={mountPoint} data-extension-id={id} class="extension-mount-point"></div>
</div>
