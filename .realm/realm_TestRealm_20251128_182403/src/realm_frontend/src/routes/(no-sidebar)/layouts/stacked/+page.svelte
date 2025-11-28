<script lang="ts">
	import type { PageData } from './$types';
	import Dashboard from '../../../utils/dashboard/Dashboard.svelte';
	import MetaTag from '../../../utils/MetaTag.svelte';
	import { SITE_NAME } from '$lib/globals';
	export let data: PageData;

	const path: string = '/layouts/stacked';
	const description: string = 'Stacked layout examaple - Smart Social Contracts';
	const title: string = SITE_NAME + ' - Stacked Layout';
	const subtitle: string = 'Stacked Layout';
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="py-4">
	<Dashboard {data} />
</main>
