<script>
	import modeobserver from './utils/modeobserver';
	import { onMount } from 'svelte';
	import { afterNavigate, goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import '$lib/i18n';
	import { locale } from 'svelte-i18n';
	import '../app.pcss';
	import { initializeTheme } from '$lib/theme/init';
	import { restoreAuthSession, resetAuthSessionRestore, getPortalRedirectUrl } from '$lib/auth';
	import { isEmbeddedInPortal, portalNavPush } from '$lib/portal-bridge.ts';
	import { resolvePortalNavSyncHref } from '$lib/portal-redirect-path.ts';
	import SetupStageGate from '$lib/components/SetupStageGate.svelte';
	import BridgeModalHost from '$lib/components/BridgeModalHost.svelte';
	import BridgeToastHost from '$lib/components/BridgeToastHost.svelte';

	export const SITE_NAME = "Realms GOS";

	// Debug locale changes
	if (browser) {
		locale.subscribe(value => {
			console.log('Layout: locale changed to', value);
			// Update HTML lang attribute directly
			document.documentElement.lang = value || 'en';
		});
	}

	// Mirror every in-realm navigation onto the portal address bar so shared
	// links and hard-refresh keep the current extension/path
	// (`/r/<slug>/extensions/justice_litigation`, …).
	afterNavigate((navigation) => {
		if (!browser || !isEmbeddedInPortal()) return;
		const url = navigation.to?.url;
		if (!url) return;
		// Drop iframe-only query params (portal=1, slug=…) — those belong on
		// the iframe src, not the shareable portal URL. Keep other search
		// params (e.g. invite codes) and the hash.
		const params = new URLSearchParams(url.search);
		params.delete('portal');
		params.delete('slug');
		const qs = params.toString();
		const path = `${url.pathname}${qs ? `?${qs}` : ''}${url.hash}`;
		// Real link clicks push a history entry; programmatic goto / initial
		// enter replace so auth redirects don't trap the back button on /join.
		const replace = navigation.type !== 'link';
		portalNavPush(path, { replace });
	});

	onMount(async () => {
		document.getElementById('app-splash')?.remove();

		// Standalone visit to the raw canister origin → bounce to the federation
		// portal (https://…/r/<slug>/<same-path>), where the single II login is
		// bridged into the embedded realm. Bookmarks and shared raw-URL links
		// transparently become portal links. ?standalone=1 opts out (tests/ops);
		// test-mode II bypass keeps working because the bypass URL carries it.
		if (browser) {
			const portalRedirect = getPortalRedirectUrl();
			if (portalRedirect) {
				console.log(`[portal] standalone visit — redirecting to ${portalRedirect}`);
				window.location.replace(portalRedirect);
				return;
			}
		}

		modeobserver();
		initializeTheme();

		let bridgeDispose = () => {};
		if (browser) {
			const { initPortalBridge } = await import('$lib/portal-bridge.ts');
			bridgeDispose = initPortalBridge();
			const onPortalAuth = async () => {
				// A fresh delegation just arrived; the memoized restore may have
				// resolved as "not authenticated" before it, so force a re-check.
				resetAuthSessionRestore();
				await restoreAuthSession();
			};
			// Host asked us to navigate (e.g. after a hard-load deep link sync).
			const onPortalNavSync = (event) => {
				const path = event?.detail?.path;
				if (!path || typeof path !== 'string') return;
				const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
				const next = resolvePortalNavSyncHref(current, path);
				if (!next) return;
				void goto(next, { replaceState: true, noScroll: true });
			};
			window.addEventListener('portal:auth', onPortalAuth);
			window.addEventListener('portal:nav-sync', onPortalNavSync);
			void restoreAuthSession();
			const prevDispose = bridgeDispose;
			bridgeDispose = () => {
				prevDispose?.();
				window.removeEventListener('portal:auth', onPortalAuth);
				window.removeEventListener('portal:nav-sync', onPortalNavSync);
			};
		}

		return () => {
			bridgeDispose?.();
		};
	});
</script>

<div class="app">
	<SetupStageGate>
		<slot />
	</SetupStageGate>
	<BridgeModalHost />
	<BridgeToastHost />
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}
</style>
