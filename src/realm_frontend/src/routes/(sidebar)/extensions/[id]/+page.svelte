<script lang="ts">
	import { SITE_NAME } from '$lib/config';
	import MetaTag from '../../../utils/MetaTag.svelte';
	
	export let data;
	const { extension } = data;
	
	const path = `/extensions/${extension.id}`;
	const description = extension.description;
	const title = `${SITE_NAME} - ${extension.name}`;
	const subtitle = extension.name;
	
	// Get the component from the extension data
	const ExtensionComponent = extension.component;
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="max-w-7xl mx-auto">
		<!-- Adding the extension.id as a key forces re-rendering when ID changes -->
		<svelte:component this={ExtensionComponent} key={extension.id} />
	</div>
</main>
