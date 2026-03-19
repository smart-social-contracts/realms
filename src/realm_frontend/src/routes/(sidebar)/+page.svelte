<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { isAuthenticated } from '$lib/stores/auth';
	import { hasJoined } from '$lib/stores/profiles';
	import { DEMO_MODE } from '$lib/config.js';
	import { get } from 'svelte/store';

	onMount(() => {
		if (DEMO_MODE || (get(isAuthenticated) && hasJoined())) {
			goto('/extensions/member_dashboard');
		} else {
			goto('/extensions/public_dashboard');
		}
	});
</script>
