<script>
	import { onMount } from 'svelte';
	import { Alert, Button } from 'flowbite-svelte';
	import { CloseOutline, InfoCircleSolid } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	
	let showBanner = false;
	let isLoading = true;
	
	const DEMO_BANNER_DISMISSED_KEY = 'demo_banner_dismissed';
	
	async function checkDemoMode() {
		try {
			const response = await backend.status();
			if (response && response.success && response.data && response.data.Status) {
				const isDemoMode = response.data.Status.demo_mode;
				const wasDismissed = localStorage.getItem(DEMO_BANNER_DISMISSED_KEY) === 'true';
				
				showBanner = isDemoMode && !wasDismissed;
			}
		} catch (error) {
			console.error('Error checking demo mode:', error);
		} finally {
			isLoading = false;
		}
	}
	
	function dismissBanner() {
		showBanner = false;
		localStorage.setItem(DEMO_BANNER_DISMISSED_KEY, 'true');
	}
	
	onMount(() => {
		checkDemoMode();
	});
</script>

{#if !isLoading && showBanner}
	<div class="relative">
		<Alert color="blue" class="mb-4 border-l-4 border-blue-500">
			<InfoCircleSolid slot="icon" class="w-4 h-4" />
			<span class="font-medium">Demo Mode Active</span>
			This application is running in demonstration mode with sample data. Features and data shown are for demonstration purposes only.
			<Button
				color="alternative"
				size="xs"
				class="absolute top-2 right-2 p-1"
				on:click={dismissBanner}
				aria-label="Dismiss demo mode notice"
			>
				<CloseOutline class="w-3 h-3" />
			</Button>
		</Alert>
	</div>
{/if}
