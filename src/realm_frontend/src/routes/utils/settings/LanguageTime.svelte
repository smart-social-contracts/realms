<script>
	import { Button, Heading, Label, Select } from 'flowbite-svelte';
	import Card from '../widgets/Card.svelte';
	import { locale } from 'svelte-i18n';
	import { supportedLocales } from '$lib/i18n';
	import { _ } from 'svelte-i18n';
	
	// Transform supported locales to format required by Select component
	const languages = supportedLocales.map(loc => ({
		name: loc.name,
		value: loc.id
	}));
	
	// Get the current locale
	let selectedLocale = $locale;
	
	// Function to save the selected locale
	function saveLanguagePreference() {
		locale.set(selectedLocale);
		if (typeof localStorage !== "undefined") {
			localStorage.setItem("preferredLocale", selectedLocale);
		}
	}

	const timezones = [
		{ name: 'GMT+0 Greenwich Mean Time (GMT)', value: '0' },
		{ name: 'GMT+1 Central European Time (CET)', value: '1' },
		{ name: 'GMT+2 Eastern European Time (EET)', value: '2' },
		{ name: 'GMT+3 Moscow Time (MSK)', value: '3' },
		{ name: 'GMT+5 Pakistan Standard Time (PKT)', value: '4' },
		{ name: 'GMT+8 China Standard Time (CST)', value: '5' },
		{ name: 'GMT+10 Eastern Australia Standard Time (AEST)', value: '6' }
	];
</script>

<Card title="Language &amp; Time">
	<div class="space-y-4">
		<Label class="space-y-2">
			<span>{$_('settings.select_language')}</span>
			<Select bind:value={selectedLocale} items={languages} class="font-normal"></Select>
			<p class="mt-1 text-sm text-gray-500">{$_('settings.language_description', { fallback: 'Choose your preferred display language for the interface' })}</p>
		</Label>
		<Label class="space-y-2">
			<span>{$_('settings.time_zone', { fallback: 'Time Zone' })}</span>
			<Select items={timezones} class="font-normal"></Select>
		</Label>
	</div>
	<Button class="mt-6 w-fit" on:click={saveLanguagePreference}>{$_('settings.save_all', { fallback: 'Save all' })}</Button>
</Card>
