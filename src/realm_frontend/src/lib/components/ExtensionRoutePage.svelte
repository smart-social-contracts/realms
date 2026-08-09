<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import ExtensionRuntimeHost from '$lib/components/ExtensionRuntimeHost.svelte';
	import { sidebarConfig } from '$lib/stores/sidebar';

	const id = $derived($page.params.id);
	const subpath = $derived($page.params.subpath ?? '');

	// Codex extension overrides (issue #242): navigating to a base system
	// extension (e.g. /extensions/member_dashboard) redirects to its
	// codex-specific replacement when one is installed.
	$effect(() => {
		const override = id ? $sidebarConfig?.extensionOverrides?.[id] : undefined;
		if (browser && override && override !== id) {
			goto(`/extensions/${override}${subpath ? `/${subpath}` : ''}`, { replaceState: true });
		}
	});
</script>

{#if id}
	<ExtensionRuntimeHost extensionId={id} />
{/if}
