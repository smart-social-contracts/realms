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
			// Profiles may still be loading after restore — wait briefly so we
			// don't bounce a real member to /join on a race (refresh loop).
			const { profilesLoading } = await import('$lib/stores/profiles');
			for (let i = 0; i < 40 && get(profilesLoading); i++) {
				await new Promise((r) => setTimeout(r, 50));
			}
			if (get(isAuthenticated) && hasJoined()) {
				const config = get(sidebarConfig);
				const defaultPath = config?.defaultPath || '/extensions/member_dashboard';
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
