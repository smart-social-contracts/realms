<script lang="ts">
	import { onMount } from 'svelte';
	import { MyExtension1 } from '$lib/extensions/my-extension-1';
	import { SITE_NAME } from '$lib/config';
	import MetaTag from '../../../utils/MetaTag.svelte';
	
	const path: string = '/extensions/myextension1';
	const description: string = 'MyExtension1';
	const title: string = SITE_NAME + ' - MyExtension1';
	const subtitle: string = 'MyExtension1';
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="max-w-7xl mx-auto">
		<MyExtension1 />
	</div>
</main>
