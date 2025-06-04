<script>
	import modeobserver from './utils/modeobserver';
	import { onMount } from 'svelte';
	import { initI18n } from '$lib/i18n';
	import { browser } from '$app/environment';
	import { locale, _ } from 'svelte-i18n';
	import '../app.pcss';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';

	export const SITE_NAME = "Realms gOS";
	
	// Initialize i18n right away
	initI18n();

	// Debug locale changes
	if (browser) {
		locale.subscribe(value => {
			console.log('Layout: locale changed to', value);
			// Update HTML lang attribute directly
			document.documentElement.lang = value || 'en';
		});
	}

	onMount(() => {
		modeobserver();
		
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
	<slot />
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}
</style>