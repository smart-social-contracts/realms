<script lang="ts">
	import MetaTag from '../../../utils/MetaTag.svelte';
	import Playground from './Playground.svelte';
	import { SITE_NAME } from '$lib/globals';

	const path: string = '/playground/stacked';
	const description: string = 'Playground stacked example - Smart Social Contracts';
	const metaTitle: string = SITE_NAME + ' - Playground stacked';
	const subtitle: string = 'Playground stacked';
</script>

<MetaTag {path} {description} title={metaTitle} {subtitle} />

<div
	id="main-content"
	class="relative mx-auto h-full w-full max-w-screen-2xl p-4 overflow-y-auto bg-gray-50 dark:bg-gray-900"
>
	<Playground />
</div>
