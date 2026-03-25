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
				<div class="loading-bar">
					<div class="loading-bar-progress"></div>
				</div>
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
		position: relative;
		overflow: hidden;
	}
	
	.loading-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2rem;
	}
	
	.spinner {
		width: 40px;
		height: 40px;
		border: 3px solid #e5e5e5;
		border-top-color: #525252;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	
	.loading-bar {
		width: 200px;
		height: 2px;
		background: #e5e5e5;
		border-radius: 2px;
		overflow: hidden;
		position: relative;
	}
	
	.loading-bar-progress {
		position: absolute;
		top: 0;
		left: 0;
		height: 100%;
		width: 50%;
		background: linear-gradient(
			90deg,
			transparent 0%,
			#404040 50%,
			transparent 100%
		);
		animation: progress 1.5s ease-in-out infinite;
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
	
	@keyframes progress {
		0% {
			left: -50%;
		}
		100% {
			left: 100%;
		}
	}
</style>