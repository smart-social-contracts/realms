<script>
	import modeobserver from './utils/modeobserver';
	import { onMount } from 'svelte';

	export const SITE_NAME = "Realms gOS";
	
	onMount(modeobserver);
</script>

<slot />