<script>
	import { onMount } from 'svelte';
	import { initI18n, waitLocale } from '$lib/i18n';
	import { browser } from '$app/environment';
	import { locale, _ } from 'svelte-i18n';
	import '../app.pcss';

	export const SITE_NAME = "Realms gOS (Dev Mode)";
	
	initI18n();

	let i18nReady = false;

	if (browser) {
		locale.subscribe(value => {
			console.log('Layout: locale changed to', value);
			document.documentElement.lang = value || 'en';
		});
	}

	onMount(async () => {
		await waitLocale();
		i18nReady = true;
		
		if (browser) {
			const storedLocale = localStorage.getItem('preferredLocale');
			if (storedLocale) {
				console.log('Setting locale from localStorage:', storedLocale);
				locale.set(storedLocale);
				return;
			}
			
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
		<div class="loading">Loading...</div>
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
		font-size: 1.5rem;
	}
</style>
