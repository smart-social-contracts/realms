<script>
	import { onMount } from 'svelte';
	import { testMode } from '$lib/stores/realmInfo';
	import { _ } from 'svelte-i18n';
	
	let showBanner = false;
	
	const DEMO_BANNER_DISMISSED_KEY = 'demo_banner_dismissed';
	
	function dismissBanner() {
		showBanner = false;
		localStorage.setItem(DEMO_BANNER_DISMISSED_KEY, 'true');
	}
	
	onMount(() => {
		if ($testMode) {
			const wasDismissed = localStorage.getItem(DEMO_BANNER_DISMISSED_KEY) === 'true';
			showBanner = !wasDismissed;
		}
	});
</script>

{#if showBanner}
	<div class="relative flex items-center gap-2 mb-4 px-4 py-3 rounded-lg border-l-4 border-blue-500 bg-blue-50 text-sm text-blue-800">
		<svg class="w-4 h-4 flex-shrink-0 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
			<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
		</svg>
		<span>
			<span class="font-medium">{$_('demo_banner.title')}</span>
			{$_('demo_banner.description')}
		</span>
		<button
			onclick={dismissBanner}
			class="ml-auto p-1 rounded hover:bg-blue-100 text-blue-500 hover:text-blue-700 transition-colors"
			aria-label={$_('demo_banner.dismiss_label')}
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
			</svg>
		</button>
	</div>
{/if}
