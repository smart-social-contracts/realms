<script>
	import modeobserver from './utils/modeobserver';
	import { onMount } from 'svelte';
	import { afterNavigate, goto } from '$app/navigation';
	import { initI18n } from '$lib/i18n';
	import { browser } from '$app/environment';
	import { locale, _ } from 'svelte-i18n';
	import '../app.pcss';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { initializeTheme } from '$lib/theme/init';
	import { restoreAuthSession, resetAuthSessionRestore, getPortalRedirectUrl } from '$lib/auth';
	import { isEmbeddedInPortal, portalNavPush } from '$lib/portal-bridge.ts';

	export const SITE_NAME = "Realms GOS";

	// Flag to track if i18n is ready
	let i18nReady = false;

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
				const current = `${window.location.pathname}${window.location.search}`;
				if (current === path) return;
				void goto(path, { replaceState: true, noScroll: true });
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

		await initI18n();
		i18nReady = true;

		if (browser) {
			const storedLocale = localStorage.getItem('preferredLocale');
			if (storedLocale) {
				locale.set(storedLocale);
			} else {
				const localeCookie = document.cookie
					.split('; ')
					.find(row => row.startsWith('locale='));
				if (localeCookie) {
					locale.set(localeCookie.split('=')[1]);
				}
			}
		}

		return () => {
			bridgeDispose?.();
		};
	});
</script>

<div class="app">
	{#if browser && i18nReady}
		<slot />
	{:else}
		<div class="loading">
			<div class="loading-dots">
				<span></span>
				<span></span>
				<span></span>
			</div>
		</div>
	{/if}
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}
	
	.loading {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 100vh;
		height: 100dvh;
		background: #ffffff;
	}
	
	.loading-dots {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}
	
	.loading-dots span {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #a3a3a3;
		animation: dot-pulse 1.4s ease-in-out infinite;
	}
	
	.loading-dots span:nth-child(2) {
		animation-delay: 0.2s;
	}
	
	.loading-dots span:nth-child(3) {
		animation-delay: 0.4s;
	}
	
	@keyframes dot-pulse {
		0%, 80%, 100% {
			opacity: 0.3;
			transform: scale(0.8);
		}
		40% {
			opacity: 1;
			transform: scale(1);
		}
	}
</style>