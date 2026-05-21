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
	let nickname: string = '';
	let avatarUrl: string = '';
	let profiles: string[] = [];
	let loadingUserStatus = true;
	let userStatusError = '';
	let assignedQuarter: string = '';
	let selectedQuarter: string = '';
	let changingQuarter = false;
	let quarterChangeError = '';
	let quarterChangeSuccess = '';

	// Upgrade state
	let isAdmin = false;
	let upgradeAvailable = false;
	let currentVersion = '';
	let latestVersion = '';
	let creditBalance = 0;
	let upgradeLoading = false;
	let upgradeError = '';
	let upgradeSuccess = '';
	let upgradeJobId = '';
	let checkingUpgrade = false;

	$: displayAvatar = avatarUrl?.trim() || `https://api.dicebear.com/9.x/glass/svg?seed=${principal}`;

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

	async function checkUpgradeAvailability() {
		if (!isAdmin) return;
		checkingUpgrade = true;
		try {
			const raw = await backend.get_available_upgrade('');
			const result = JSON.parse(raw);
			if (result.success) {
				currentVersion = result.current_version || '';
				latestVersion = result.latest_version || '';
				upgradeAvailable = result.upgrade_available || false;
			}
		} catch (e: any) {
			console.warn('Could not check upgrade availability:', e.message);
		}

		try {
			const raw = await backend.get_realm_credits('');
			const result = JSON.parse(raw);
			if (result.success && result.credits) {
				creditBalance = result.credits.balance || 0;
			}
		} catch (e: any) {
			console.warn('Could not fetch realm credits:', e.message);
		}
		checkingUpgrade = false;
	}

	async function handleUpgrade() {
		upgradeLoading = true;
		upgradeError = '';
		upgradeSuccess = '';
		try {
			const raw = await backend.request_upgrade('');
			const result = JSON.parse(raw);
			if (result.success) {
				upgradeJobId = result.job_id || '';
				upgradeSuccess = `Upgrade to ${result.target_version || 'latest'} initiated (job: ${upgradeJobId})`;
				upgradeAvailable = false;
			} else {
				upgradeError = result.error || 'Upgrade request failed';
			}
		} catch (e: any) {
			upgradeError = e.message || 'Failed to request upgrade';
		} finally {
			upgradeLoading = false;
		}
	}

	onMount(async () => {
		try {
			if (!backend || typeof backend.get_my_user_status !== 'function') {
				throw new Error("Backend canister is not properly initialized");
			}
			
			const response = await backend.get_my_user_status();
			
			if (response && response.success && response.data && response.data.userGet) {
				const u = response.data.userGet;
				principal = u.principal;
				nickname = u.nickname || '';
				avatarUrl = u.avatar || '';
				profiles = u.profiles || [];
				assignedQuarter = u.assigned_quarter || '';
				selectedQuarter = assignedQuarter;
				isAdmin = profiles.includes('admin') || profiles.includes('operator');
			} else {
				throw new Error('Could not fetch user status: Invalid response format.');
			}
		} catch (e: any) {
			userStatusError = e.message || 'Failed to fetch user status.';
		} finally {
			loadingUserStatus = false;
		}

		if (isAdmin) {
			await checkUpgradeAvailability();
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

			<!-- User Info -->
			{#if loadingUserStatus}
				<div class="mt-4 text-gray-500">Loading user status...</div>
			{:else if userStatusError}
				<div class="mt-4 text-red-500">{userStatusError}</div>
			{:else}
				<div class="mt-4 p-5 bg-gray-50 rounded-lg border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
					<div class="flex items-center gap-4 mb-4">
						<img
							src={displayAvatar}
							alt="Avatar"
							class="w-16 h-16 rounded-full object-cover border-2 border-gray-200 dark:border-gray-600"
						/>
						<div>
							<div class="text-lg font-semibold text-gray-900 dark:text-white">
								{nickname || 'No nickname set'}
							</div>
							<div class="flex flex-wrap gap-1.5 mt-1">
								{#each profiles as profile}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 capitalize">
										{profile}
									</span>
								{/each}
								{#if profiles.length === 0}
									<span class="text-sm text-gray-500 dark:text-gray-400">No profiles</span>
								{/if}
							</div>
						</div>
					</div>
					<div class="pt-3 border-t border-gray-200 dark:border-gray-700">
						<span class="text-xs font-medium text-gray-500 dark:text-gray-400">Principal</span>
						<div class="font-mono text-sm text-gray-700 dark:text-gray-300 break-all mt-0.5">{principal}</div>
					</div>
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

		<!-- Registries (only shown when there are registries to display) -->
		{#if $realmInfo.registries.length > 0}
		<div class="col-span-full mt-6">
			<Heading tag="h2" class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
				{$_('settings.registries_title', { default: 'Registries' })}
			</Heading>
			<div class="space-y-2">
				{#each $realmInfo.registries as reg}
					<div class="p-3 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
						<span class="font-semibold">{reg.canister_type}:</span>
						<span class="font-mono text-sm break-all ml-1">{reg.canister_id}</span>
					</div>
				{/each}
			</div>
		</div>
		{/if}

		<!-- Realm Upgrade (admin/operator only) -->
		{#if isAdmin}
		<div class="col-span-full mt-6">
			<Heading tag="h2" class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
				Realm Upgrade
			</Heading>
			<div class="p-4 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
				{#if checkingUpgrade}
					<div class="text-gray-500">Checking for updates...</div>
				{:else}
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
						<div>
							<span class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Current Version</span>
							<div class="text-sm font-semibold text-gray-900 dark:text-white mt-0.5">
								{currentVersion || 'Unknown'}
							</div>
						</div>
						<div>
							<span class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Latest Available</span>
							<div class="text-sm font-semibold mt-0.5" class:text-green-600={upgradeAvailable} class:dark:text-green-400={upgradeAvailable} class:text-gray-900={!upgradeAvailable} class:dark:text-white={!upgradeAvailable}>
								{latestVersion || 'None published'}
								{#if upgradeAvailable}
									<span class="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
										Update available
									</span>
								{/if}
							</div>
						</div>
						<div>
							<span class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Realm Credits</span>
							<div class="text-sm font-semibold text-gray-900 dark:text-white mt-0.5">
								{creditBalance} credits
								{#if creditBalance < 5}
									<span class="ml-1 text-xs text-red-500">(need 5 for upgrade)</span>
								{/if}
							</div>
						</div>
					</div>

					{#if upgradeAvailable && creditBalance >= 5}
						<button
							on:click={handleUpgrade}
							disabled={upgradeLoading}
							class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{upgradeLoading ? 'Upgrading...' : `Upgrade to ${latestVersion}`}
						</button>
						<p class="mt-1 text-xs text-gray-500">Cost: 5 credits. Both backend and frontend will be upgraded.</p>
					{:else if upgradeAvailable && creditBalance < 5}
						<p class="text-sm text-amber-600 dark:text-amber-400">
							Insufficient credits to upgrade. Transfer tokens to the registry to purchase credits.
						</p>
					{:else if !upgradeAvailable && latestVersion}
						<p class="text-sm text-gray-500">Your realm is up to date.</p>
					{/if}

					{#if upgradeError}
						<div class="mt-2 text-sm text-red-600 dark:text-red-400">{upgradeError}</div>
					{/if}
					{#if upgradeSuccess}
						<div class="mt-2 text-sm text-green-600 dark:text-green-400">{upgradeSuccess}</div>
					{/if}
				{/if}
			</div>
		</div>
		{/if}
	</div>
</main>
