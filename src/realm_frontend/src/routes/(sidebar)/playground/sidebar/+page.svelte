<script lang="ts">
	import Playground from '../../../(no-sidebar)/playground/stacked/Playground.svelte';
	import MetaTag from '../../../utils/MetaTag.svelte';
	import Footer from '../../Footer.svelte';
	import { SITE_NAME } from '$lib/globals';

	const path: string = '/playground/sidebar';
	const description: string = 'Playground Sidebar example - Smart Social Contracts';
	const metaTitle: string = SITE_NAME + ' - Playground Sidebar';
	const subtitle: string = 'Playground Sidebar';
</script>

<MetaTag {path} {description} title={metaTitle} {subtitle} />

<div
	id="main-content"
	class="relative mx-auto h-full w-full overflow-y-auto bg-gray-50 p-4 dark:bg-gray-900"
>
	<Playground />
</div>
<Footer />
