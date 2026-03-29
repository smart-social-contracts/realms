<script lang="ts">
	console.log("Settings Svelte script loaded (top of file)");

	import { Breadcrumb, BreadcrumbItem, Heading } from 'flowbite-svelte';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../utils/MetaTag.svelte';
	import { _ } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import { backend } from '$lib/canisters.js';
	import { realmInfo } from '$lib/stores/realmInfo';

	const path: string = '/settings';
	const description: string = 'Settings example - Smart Social Contracts';
	const title: string = SITE_NAME + ' - Settings';
	const subtitle: string = 'Settings';

	let principal: string = '';
	let profiles: string[] = [];
	let loadingUserStatus = true;
	let userStatusError = '';
	let assignedQuarter: string = '';
	let selectedQuarter: string = '';
	let changingQuarter = false;
	let quarterChangeError = '';
	let quarterChangeSuccess = '';

	function getQuarterName(canisterId: string): string {
		const q = $realmInfo.quarters.find(q => q.canister_id === canisterId);
		return q ? `${q.name} (${canisterId})` : canisterId || 'Not assigned';
	}

	async function handleChangeQuarter() {
		if (!selectedQuarter || selectedQuarter === assignedQuarter) return;
		changingQuarter = true;
		quarterChangeError = '';
		quarterChangeSuccess = '';
		try {
			const response = await backend.change_quarter(selectedQuarter);
			if (response.success) {
				assignedQuarter = selectedQuarter;
				quarterChangeSuccess = `Switched to ${getQuarterName(selectedQuarter)}`;
			} else {
				quarterChangeError = response.data?.error || 'Failed to change quarter';
			}
		} catch (e: any) {
			quarterChangeError = e.message || 'Failed to change quarter';
		} finally {
			changingQuarter = false;
		}
	}

	onMount(async () => {
		console.log("Settings page mounted");
		// Fetch user status
		try {
			console.log("Backend:", backend);
			
			if (!backend || typeof backend.get_my_user_status !== 'function') {
				throw new Error("Backend canister is not properly initialized");
			}
			
			console.log("Calling backend.get_my_user_status...");
			const response = await backend.get_my_user_status();
			console.log("Backend response:", response);
			
			if (response && response.success && response.data && response.data.userGet) {
				principal = response.data.userGet.principal;
				profiles = response.data.userGet.profiles || [];
				assignedQuarter = response.data.userGet.assigned_quarter || '';
				selectedQuarter = assignedQuarter;
			} else {
				console.error("Invalid backend response format:", response);
				throw new Error('Could not fetch user status: Invalid response format.');
			}
		} catch (e: any) {
			userStatusError = e.message || 'Failed to fetch user status.';
		} finally {
			loadingUserStatus = false;
		}
	});
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="grid grid-cols-1 space-y-2 dark:bg-gray-900">
		<div class="col-span-full mb-6">
			<Breadcrumb class="mb-6">
				<BreadcrumbItem home>Home</BreadcrumbItem>
				<BreadcrumbItem>Settings</BreadcrumbItem>
			</Breadcrumb>

			<Heading tag="h1" class="text-xl font-semibold text-gray-900 sm:text-2xl dark:text-white">
				{$_('settings.title', { default: 'User Settings' })}
			</Heading>

			<!-- User Principal and Profiles -->
			{#if loadingUserStatus}
				<div class="mt-4 text-gray-500">Loading user status...</div>
			{:else if userStatusError}
				<div class="mt-4 text-red-500">{userStatusError}</div>
			{:else}
				<div class="mt-4 p-4 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
					<div class="mb-2"><span class="font-semibold">Principal:</span> <span class="font-mono break-all">{principal}</span></div>
					<div><span class="font-semibold">Profiles:</span> {profiles.length > 0 ? profiles.join(', ') : 'None'}</div>
				</div>
			{/if}
		</div>

		<!-- Quarter Assignment -->
		{#if $realmInfo.quarters.length > 0}
		<div class="col-span-full mt-6">
			<Heading tag="h2" class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
				{$_('settings.quarter_title', { default: 'Quarter' })}
			</Heading>
			<div class="p-4 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
				<div class="mb-3">
					<span class="font-semibold">Current Quarter:</span>
					<span class="ml-1">{getQuarterName(assignedQuarter)}</span>
				</div>
				<div class="flex items-end gap-3">
					<div class="flex-1">
						<label for="quarter-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							Switch Quarter
						</label>
						<select
							id="quarter-select"
							bind:value={selectedQuarter}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						>
							{#each $realmInfo.quarters.filter(q => q.status === 'active') as quarter}
								<option value={quarter.canister_id}>
									{quarter.name} — {quarter.population} users ({quarter.canister_id})
								</option>
							{/each}
						</select>
					</div>
					<button
						on:click={handleChangeQuarter}
						disabled={changingQuarter || selectedQuarter === assignedQuarter || !selectedQuarter}
						class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
					>
						{changingQuarter ? 'Switching...' : 'Switch'}
					</button>
				</div>
				{#if quarterChangeError}
					<div class="mt-2 text-sm text-red-600 dark:text-red-400">{quarterChangeError}</div>
				{/if}
				{#if quarterChangeSuccess}
					<div class="mt-2 text-sm text-green-600 dark:text-green-400">{quarterChangeSuccess}</div>
				{/if}
			</div>
		</div>
		{/if}

		<!-- Registries -->
		<div class="col-span-full mt-6">
			<Heading tag="h2" class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
				{$_('settings.registries_title', { default: 'Registries' })}
			</Heading>
			{#if $realmInfo.loading}
				<div class="text-gray-500">Loading...</div>
			{:else if $realmInfo.registries.length > 0}
				<div class="space-y-2">
					{#each $realmInfo.registries as reg}
						<div class="p-3 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
							<span class="font-semibold">{reg.canister_type}:</span>
							<span class="font-mono text-sm break-all ml-1">{reg.canister_id}</span>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-gray-500 dark:text-gray-400">
					{$_('settings.no_registries', { default: 'This realm is not registered with any registry.' })}
				</div>
			{/if}
		</div>
	</div>
</main>
