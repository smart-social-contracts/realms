<script>
	import { Card, Button, Toggle, Select } from 'flowbite-svelte';
	import { CogOutline, UserCircleOutline, BellSolid, PaletteSolid } from 'flowbite-svelte-icons';
	import { locale } from 'svelte-i18n';

	let darkMode = false;
	let notifications = true;
	let emailNotifications = false;
	let language = 'en';

	const languages = [
		{ value: 'en', name: 'English' },
		{ value: 'es', name: 'Español' }
	];

	function handleLanguageChange() {
		locale.set(language);
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('preferredLocale', language);
		}
	}
</script>

<div class="py-6">
	<div class="mb-8">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Settings</h1>
		<p class="text-gray-600 dark:text-gray-400">Manage your account and application preferences</p>
	</div>

	<div class="grid gap-6">
		<Card>
			<div class="flex items-center mb-4">
				<UserCircleOutline class="w-5 h-5 mr-2 text-gray-500" />
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Profile Settings</h3>
			</div>
			
			<div class="space-y-4">
				<div class="grid gap-4 md:grid-cols-2">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Display Name</label>
						<input type="text" value="John Doe" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700">
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Email</label>
						<input type="email" value="john.doe@example.com" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700">
					</div>
				</div>
				
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Bio</label>
					<textarea rows="3" class="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-700" placeholder="Tell us about yourself..."></textarea>
				</div>
				
				<div class="flex justify-end">
					<Button>Save Profile</Button>
				</div>
			</div>
		</Card>

		<Card>
			<div class="flex items-center mb-4">
				<PaletteSolid class="w-5 h-5 mr-2 text-gray-500" />
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Appearance</h3>
			</div>
			
			<div class="space-y-4">
				<div class="flex items-center justify-between">
					<div>
						<label class="text-sm font-medium text-gray-700 dark:text-gray-300">Dark Mode</label>
						<p class="text-sm text-gray-600 dark:text-gray-400">Toggle dark mode theme</p>
					</div>
					<Toggle bind:checked={darkMode} />
				</div>
				
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Language</label>
					<Select bind:value={language} on:change={handleLanguageChange}>
						{#each languages as lang}
							<option value={lang.value}>{lang.name}</option>
						{/each}
					</Select>
				</div>
			</div>
		</Card>

		<Card>
			<div class="flex items-center mb-4">
				<BellSolid class="w-5 h-5 mr-2 text-gray-500" />
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Notifications</h3>
			</div>
			
			<div class="space-y-4">
				<div class="flex items-center justify-between">
					<div>
						<label class="text-sm font-medium text-gray-700 dark:text-gray-300">Push Notifications</label>
						<p class="text-sm text-gray-600 dark:text-gray-400">Receive notifications in the app</p>
					</div>
					<Toggle bind:checked={notifications} />
				</div>
				
				<div class="flex items-center justify-between">
					<div>
						<label class="text-sm font-medium text-gray-700 dark:text-gray-300">Email Notifications</label>
						<p class="text-sm text-gray-600 dark:text-gray-400">Receive notifications via email</p>
					</div>
					<Toggle bind:checked={emailNotifications} />
				</div>
			</div>
		</Card>

		<Card>
			<div class="flex items-center mb-4">
				<CogOutline class="w-5 h-5 mr-2 text-gray-500" />
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">System</h3>
			</div>
			
			<div class="space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Principal ID</label>
					<div class="p-2 bg-gray-100 rounded-md dark:bg-gray-700">
						<code class="text-sm font-mono">dummy-principal-123456789abcdef</code>
					</div>
				</div>
				
				<div class="flex space-x-2">
					<Button color="red">Clear Cache</Button>
					<Button color="light">Export Data</Button>
					<Button color="light">Reset Settings</Button>
				</div>
			</div>
		</Card>
	</div>
</div>
