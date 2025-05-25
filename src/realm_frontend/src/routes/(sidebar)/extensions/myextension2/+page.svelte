<script lang="ts">
	import { onMount } from 'svelte';
	import MyExtension2 from '$lib/extensions/my-extension-2';
	import { SITE_NAME } from '$lib/config';
	import MetaTag from '../../../utils/MetaTag.svelte';
	
	const path: string = '/extensions/myextension2';
	const description: string = 'MyExtension2';
	const title: string = SITE_NAME + ' - MyExtension2';
	const subtitle: string = 'MyExtension2';
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="max-w-7xl mx-auto">
		<MyExtension2/>
	</div>
</main>
