<script lang="ts">
	import Dashboard from '../../../utils/dashboard/Dashboard.svelte';
	import MetaTag from '../../../utils/MetaTag.svelte';
	import Footer from '../../Footer.svelte';
	import type { PageData } from './$types';
	import { SITE_NAME } from '$lib/globals';
	export let data: PageData;

	const path: string = '/layouts/sidebar';
	const description: string = 'Sidebar layout examaple - H';
	const title: string = SITE_NAME + ' - Sidebar Layout';
	const subtitle: string = 'Sidebar Layout';
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<Dashboard {data} />
</main>
<Footer />
