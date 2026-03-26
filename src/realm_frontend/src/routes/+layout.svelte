<script>
	import modeobserver from './utils/modeobserver';
	import { onMount } from 'svelte';
	import { initI18n } from '$lib/i18n';
	import { browser } from '$app/environment';
	import { locale, _ } from 'svelte-i18n';
	import '../app.pcss';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { initializeTheme } from '$lib/theme/init';

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

	onMount(async () => {
		modeobserver();
		
		// Initialize theme system
		initializeTheme();
		
		// Initialize i18n and wait for all translations to load
		// This includes both core and extension translations
		await initI18n();
		
		i18nReady = true;
		
		// Restore user's preferred language from localStorage or cookie
		if (browser) {
			// First try localStorage
			const storedLocale = localStorage.getItem('preferredLocale');
			if (storedLocale) {
				console.log('Setting locale from localStorage:', storedLocale);
				locale.set(storedLocale);
				return;
			}
			
			// Then try cookie
			const localeCookie = document.cookie
				.split('; ')
				.find(row => row.startsWith('locale='));
			
			if (localeCookie) {
				const cookieLocale = localeCookie.split('=')[1];
				console.log('Setting locale from cookie:', cookieLocale);
				locale.set(cookieLocale);
			}
		}
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