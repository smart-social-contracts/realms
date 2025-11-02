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
			<div class="loading-content">
				<div class="spinner"></div>
				<p>Loading Realms GOS...</p>
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
		background: var(--color-bg-primary, #ffffff);
	}
	
	.loading-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.5rem;
	}
	
	.loading-content p {
		font-size: var(--font-size-lg, 18px);
		color: var(--color-text-secondary, #666);
		margin: 0;
	}
	
	.spinner {
		width: 40px;
		height: 40px;
		border: 4px solid var(--color-gray-200, #e5e5e5);
		border-top-color: var(--color-gray-700, #404040);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>