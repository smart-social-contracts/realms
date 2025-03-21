<script>
	import modeobserver from './utils/modeobserver';
	import { onMount } from 'svelte';

	export const SITE_NAME = "Smart Social Contracts";
	
	onMount(modeobserver);
</script>

<slot />