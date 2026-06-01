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
	<div class="mb-4 ml-4 flex items-start gap-3 border-l border-gray-300 pl-3 text-sm text-gray-600">
		<p class="min-w-0 flex-1">
			<span class="font-medium text-gray-800">{$_('demo_banner.title')}</span>
			{' '}{$_('demo_banner.description')}
		</p>
		<button
			onclick={dismissBanner}
			class="flex-shrink-0 text-gray-400 hover:text-gray-600"
			aria-label={$_('demo_banner.dismiss_label')}
		>
			<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
			</svg>
		</button>
	</div>
{/if}
