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
	<div
		class="relative isolate z-10 flex items-center gap-3 bg-black px-4 py-2.5 text-sm text-white pointer-events-auto"
		role="status"
	>
		<p class="min-w-0 flex-1">
			<span class="font-semibold">{$_('demo_banner.title')}</span>
			{' '}{$_('demo_banner.description')}
		</p>
		<button
			type="button"
			onclick={dismissBanner}
			class="relative z-10 flex-shrink-0 rounded p-1.5 text-white hover:bg-white/15 pointer-events-auto"
			aria-label={$_('demo_banner.dismiss_label')}
		>
			<!-- SVG must not be the hit target: delegated click on <path> is
			     mouse-dead in some browsers while Tab+Enter still fires. -->
			<svg class="pointer-events-none h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
				<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
			</svg>
		</button>
	</div>
{/if}
