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
				<div class="logo-container">
					<img
						src="/images/logo_sphere_only.svg"
						alt="Realms GOS"
						class="logo"
					/>
					<div class="shimmer"></div>
				</div>
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
		background: #ffffff;
		position: relative;
		overflow: hidden;
	}
	
	.loading-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2.5rem;
		position: relative;
		z-index: 10;
	}
	
	.logo-container {
		position: relative;
		width: 120px;
		height: 120px;
		display: flex;
		align-items: center;
		justify-content: center;
		animation: pulse 2s ease-in-out infinite;
	}
	
	.logo {
		width: 100%;
		height: auto;
		position: relative;
		z-index: 2;
	}
	
	.shimmer {
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(
			90deg,
			transparent 0%,
			rgba(255, 255, 255, 0.4) 50%,
			transparent 100%
		);
		animation: shimmer 2.5s infinite;
		z-index: 3;
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
	
	@keyframes pulse {
		0%, 100% {
			opacity: 1;
			transform: scale(1);
		}
		50% {
			opacity: 0.85;
			transform: scale(0.98);
		}
	}
	
	@keyframes shimmer {
		0% {
			left: -100%;
		}
		100% {
			left: 100%;
		}
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