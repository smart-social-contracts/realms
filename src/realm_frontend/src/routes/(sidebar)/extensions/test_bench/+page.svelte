<script lang="ts">
	import { onMount } from 'svelte';
	import Testbench from '$lib/extensions/test_bench';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../../utils/MetaTag.svelte';
	
	const path: string = '/extensions/test_bench';
	const description: string = 'Testbench';
	const title: string = SITE_NAME + ' - Testbench';
	const subtitle: string = 'Testbench';
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="max-w-7xl mx-auto">
		<Testbench/>
	</div>
</main>
