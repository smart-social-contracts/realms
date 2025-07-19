<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../utils/MetaTag.svelte';
	import { _ } from 'svelte-i18n';

	export let data;

	const path: string = '/dashboard';
	const description: string = 'Public Dashboard - redirecting to extension';
	const title: string = SITE_NAME + ' - ' + $_('extensions.public_dashboard.title');
	const subtitle: string = $_('extensions.public_dashboard.title');

	onMount(() => {
		goto('/extensions/public_dashboard');
	});
</script>

<MetaTag {path} {description} {title} {subtitle} />
