<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { isAuthenticated } from '$lib/stores/auth';
	import { hasJoined } from '$lib/stores/profiles';
	import { sidebarConfig } from '$lib/stores/sidebar';
	import { isEmbeddedInPortal } from '$lib/portal-bridge.ts';
	import { restoreAuthSession } from '$lib/auth';
	import { get } from 'svelte/store';

	onMount(async () => {
		if (isEmbeddedInPortal()) {
			await restoreAuthSession();
			if (get(isAuthenticated) && hasJoined()) {
				const config = get(sidebarConfig);
				const defaultPath = config?.defaultPath || '/extensions/public_dashboard';
				goto(defaultPath);
			} else {
				goto('/join');
			}
			return;
		}
		if (get(isAuthenticated) && hasJoined()) {
			const config = get(sidebarConfig);
			const defaultPath = config?.defaultPath || '/extensions/member_dashboard';
			goto(defaultPath);
		} else {
			goto('/extensions/public_dashboard');
		}
	});
</script>
