<script>
	import { onMount } from 'svelte';
	import { Alert, Button } from 'flowbite-svelte';
	import { CloseOutline, InfoCircleSolid } from 'flowbite-svelte-icons';
	import { TEST_MODE } from '$lib/config.js';
	import { _ } from 'svelte-i18n';
	
	let showBanner = false;
	
	const DEMO_BANNER_DISMISSED_KEY = 'demo_banner_dismissed';
	
	function dismissBanner() {
		showBanner = false;
		localStorage.setItem(DEMO_BANNER_DISMISSED_KEY, 'true');
	}
	
	onMount(() => {
		if (TEST_MODE) {
			const wasDismissed = localStorage.getItem(DEMO_BANNER_DISMISSED_KEY) === 'true';
			showBanner = !wasDismissed;
		}
	});
</script>

{#if showBanner}
	<div class="relative">
		<Alert color="blue" class="mb-4 border-l-4 border-blue-500">
			<InfoCircleSolid slot="icon" class="w-4 h-4" />
			<span class="font-medium">{$_('demo_banner.title')}</span>
			{$_('demo_banner.description')}
			<Button
				color="alternative"
				size="xs"
				class="absolute top-2 right-2 p-1"
				on:click={dismissBanner}
				aria-label={$_('demo_banner.dismiss_label')}
			>
				<CloseOutline class="w-3 h-3" />
			</Button>
		</Alert>
	</div>
{/if}
