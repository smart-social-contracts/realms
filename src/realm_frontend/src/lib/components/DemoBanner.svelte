<script>
	import { browser } from '$app/environment';
	import { testMode } from '$lib/stores/realmInfo';
	import { _ } from 'svelte-i18n';
	
	let dismissed = false;
	
	const DEMO_BANNER_DISMISSED_KEY = 'demo_banner_dismissed';
	
	function dismissBanner() {
		dismissed = true;
		localStorage.setItem(DEMO_BANNER_DISMISSED_KEY, 'true');
	}
	
	if (browser) {
		dismissed = localStorage.getItem(DEMO_BANNER_DISMISSED_KEY) === 'true';
	}
	
	$: showBanner = browser && $testMode && !dismissed;
</script>

{#if showBanner}
	<div class="flex items-center gap-3 bg-black px-4 py-2.5 text-sm text-white">
		<p class="min-w-0 flex-1">
			<span class="font-semibold">{$_('demo_banner.title')}</span>
			{' '}{$_('demo_banner.description')}
		</p>
		<button
			onclick={dismissBanner}
			class="flex-shrink-0 rounded p-1.5 text-white hover:bg-white/15"
			aria-label={$_('demo_banner.dismiss_label')}
		>
			<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
			</svg>
		</button>
	</div>
{/if}
