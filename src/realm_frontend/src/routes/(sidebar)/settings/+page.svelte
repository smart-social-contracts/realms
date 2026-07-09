<script lang="ts">
	console.log("Settings Svelte script loaded (top of file)");

	import { Heading } from 'flowbite-svelte';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../utils/MetaTag.svelte';
	import { _ } from 'svelte-i18n';
	import { onMount } from 'svelte';
	// @ts-ignore
	import { quarterBackend, createQuarterActor } from '$lib/canisters.js';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { activeQuarterId } from '$lib/stores/quarters';
	import {
		probeFederatedMembership,
		activateMembership,
		type MembershipHit
	} from '$lib/utils/federatedMembership';
	import { formatQuarterLabel } from '$lib/utils/quarterLabels';

	const path: string = '/settings';
	const description: string = 'Settings example - Smart Social Contracts';
	const title: string = SITE_NAME + ' - Settings';
	const subtitle: string = 'Settings';

	let principal = $state('');
	let nickname = $state('');
	let avatarUrl = $state('');
	let profiles = $state<string[]>([]);
	let loadingUserStatus = $state(true);
	let userStatusError = $state('');

	/** Federated membership probe (issue #156). */
	let membershipHits = $state<MembershipHit[]>([]);
	let capitalId = $state('');
	let loadingMembership = $state(true);
	let membershipError = $state('');
	let activatingCanisterId = $state('');
	let activateError = $state('');
	let activateSuccess = $state('');
	let registeringCanisterId = $state('');
	let registerError = $state('');
	let registerSuccess = $state('');

	const displayAvatar = $derived(
		avatarUrl?.trim() || `https://api.dicebear.com/9.x/glass/svg?seed=${principal}`
	);

	const sessionQuarterId = $derived(($activeQuarterId as string | null) || capitalId || '');

	const showFederationUi = $derived(
		$realmInfo.quarters.length > 1 || membershipHits.length > 1
	);

	const membershipIds = $derived(new Set(membershipHits.map((h) => h.canisterId)));

	const registerTargets = $derived(
		($realmInfo.quarters || []).filter(
			(q) =>
				q.status === 'active' &&
				q.canister_id &&
				!membershipIds.has(q.canister_id)
		)
	);

	function quarterMeta(canisterId: string) {
		return ($realmInfo.quarters || []).find((q) => q.canister_id === canisterId) || null;
	}

	function labelForCanister(canisterId: string): string {
		const q = quarterMeta(canisterId);
		if (q) return formatQuarterLabel(q as any);
		if (capitalId && canisterId === capitalId) return 'Quarter 0 (Capital)';
		return canisterId || 'Unknown quarter';
	}

	function isSessionActive(hit: MembershipHit): boolean {
		const cid = hit.canisterId || '';
		if (hit.isCapital || (capitalId && cid === capitalId)) {
			return !$activeQuarterId || $activeQuarterId === capitalId;
		}
		return $activeQuarterId === cid;
	}

	/** Primary profile for deliberate multi-registration: prefer admin, else member. */
	function primaryJoinProfile(): string {
		if (profiles.includes('admin')) return 'admin';
		if (profiles.includes('member')) return 'member';
		if (profiles.includes('developer')) return 'developer';
		return profiles[0] || 'member';
	}

	function isInviteRequiredError(message: string): boolean {
		const m = (message || '').toLowerCase();
		return (
			m.includes('invite') ||
			m.includes('invitation') ||
			m.includes('registration code') ||
			m.includes('registration is closed') ||
			m.includes('open_registration') ||
			m.includes('not open')
		);
	}

	async function loadUserStatus() {
		const response = await quarterBackend.get_my_user_status();
		if (response && response.success && response.data && response.data.userGet) {
			const u = response.data.userGet;
			principal = u.principal;
			nickname = u.nickname || '';
			avatarUrl = u.avatar || '';
			profiles = u.profiles || [];
		} else {
			throw new Error(
				(response && !response.success && response.data?.error) ||
					'Could not fetch user status: Invalid response format.'
			);
		}
	}

	async function refreshMembershipProbe() {
		const result = await probeFederatedMembership({ activate: false, cache: false });
		membershipHits = result.hits;
		capitalId = result.capitalId || '';
		return result;
	}

	async function handleActivate(hit: MembershipHit) {
		if (isSessionActive(hit) || activatingCanisterId) return;
		activatingCanisterId = hit.canisterId;
		activateError = '';
		activateSuccess = '';
		registerError = '';
		registerSuccess = '';
		try {
			await activateMembership(hit, capitalId, { cache: true });
			activateSuccess = `Now using ${labelForCanister(hit.canisterId)} for this session.`;
			try {
				await loadUserStatus();
			} catch (e: any) {
				// Session switched; status refresh is best-effort.
				console.warn('User status refresh after activate failed:', e);
			}
		} catch (e: any) {
			activateError = e.message || 'Failed to switch active quarter.';
		} finally {
			activatingCanisterId = '';
		}
	}

	async function handleRegister(canisterId: string) {
		if (!canisterId || registeringCanisterId) return;
		registeringCanisterId = canisterId;
		registerError = '';
		registerSuccess = '';
		activateError = '';
		activateSuccess = '';
		try {
			const profile = primaryJoinProfile();
			const actor = await createQuarterActor(canisterId);
			const response = await actor.join_realm(profile, '', '');
			if (!response?.success) {
				const err = response?.data?.error || 'Failed to register in this quarter.';
				if (isInviteRequiredError(err)) {
					registerError =
						'This quarter requires an invitation code. Use an invite link to register there, then return here to activate it.';
				} else {
					registerError = err;
				}
				return;
			}

			const result = await refreshMembershipProbe();
			const hit =
				result.hits.find((h) => h.canisterId === canisterId) ||
				({
					canisterId,
					isCapital: !!(capitalId && canisterId === capitalId),
					response,
					profiles: [profile]
				} as MembershipHit);

			await activateMembership(hit, result.capitalId || capitalId, { cache: true });
			registerSuccess = `Registered in ${labelForCanister(canisterId)} and set it as the active quarter.`;
			try {
				await loadUserStatus();
			} catch (e: any) {
				console.warn('User status refresh after register failed:', e);
			}
		} catch (e: any) {
			const msg = e.message || 'Failed to register in this quarter.';
			if (isInviteRequiredError(msg)) {
				registerError =
					'This quarter requires an invitation code. Use an invite link to register there, then return here to activate it.';
			} else {
				registerError = msg;
			}
		} finally {
			registeringCanisterId = '';
		}
	}

	onMount(async () => {
		await Promise.all([
			(async () => {
				try {
					await refreshMembershipProbe();
				} catch (e: any) {
					membershipError = e.message || 'Failed to probe quarter memberships.';
				} finally {
					loadingMembership = false;
				}
			})(),
			(async () => {
				try {
					await loadUserStatus();
				} catch (e: any) {
					userStatusError = e.message || 'Failed to fetch user status.';
				} finally {
					loadingUserStatus = false;
				}
			})()
		]);
	});
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="grid grid-cols-1 space-y-2 dark:bg-gray-900">
		<div class="col-span-full mb-6">
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
								{#each profiles as profile (profile)}
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
					{#if sessionQuarterId}
						<div class="pt-3 mt-3 border-t border-gray-200 dark:border-gray-700">
							<span class="text-xs font-medium text-gray-500 dark:text-gray-400">Active quarter (this session)</span>
							<div class="text-sm text-gray-700 dark:text-gray-300 mt-0.5">
								{labelForCanister(sessionQuarterId)}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Multi-quarter membership (issue #156) -->
		{#if showFederationUi}
		<div class="col-span-full mt-6">
			<Heading tag="h2" class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
				{$_('settings.quarter_title', { default: 'Quarters' })}
			</Heading>

			<!-- 1. Activate / switch session among existing memberships -->
			<div class="p-4 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700 mb-4">
				<h3 class="text-sm font-semibold text-gray-900 dark:text-white">
					Active quarter (this session)
				</h3>
				<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
					Switch among quarters you already belong to. This updates session routing and your local home cache — it does not create a new membership.
				</p>

				{#if loadingMembership}
					<div class="mt-3 text-sm text-gray-500">Checking memberships…</div>
				{:else if membershipError}
					<div class="mt-3 text-sm text-red-600 dark:text-red-400">{membershipError}</div>
				{:else if membershipHits.length === 0}
					<div class="mt-3 text-sm text-gray-500">No quarter memberships found for this principal.</div>
				{:else}
					<ul class="mt-3 space-y-2">
						{#each membershipHits as hit (hit.canisterId)}
							<li class="flex flex-wrap items-center justify-between gap-2 rounded border border-gray-200 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700">
								<div class="min-w-0">
									<div class="text-sm font-medium text-gray-900 dark:text-white">
										{labelForCanister(hit.canisterId)}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400 font-mono break-all">
										{hit.canisterId}
									</div>
									{#if hit.profiles?.length}
										<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 capitalize">
											{hit.profiles.join(', ')}
										</div>
									{/if}
								</div>
								{#if isSessionActive(hit)}
									<span class="text-xs font-medium text-green-700 dark:text-green-400">In use</span>
								{:else}
									<button
										type="button"
										onclick={() => handleActivate(hit)}
										disabled={!!activatingCanisterId}
										class="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
									>
										{activatingCanisterId === hit.canisterId ? 'Switching…' : 'Use this quarter'}
									</button>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}

				{#if activateError}
					<div class="mt-2 text-sm text-red-600 dark:text-red-400">{activateError}</div>
				{/if}
				{#if activateSuccess}
					<div class="mt-2 text-sm text-green-600 dark:text-green-400">{activateSuccess}</div>
				{/if}
			</div>

			<!-- 2. Deliberate register in another quarter -->
			<div class="p-4 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
				<h3 class="text-sm font-semibold text-gray-900 dark:text-white">
					Register in another quarter
				</h3>
				<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
					Create a membership on a quarter you are not yet part of, then make it active. This is intentional multi-registration — not the open join picker.
				</p>

				{#if loadingMembership}
					<div class="mt-3 text-sm text-gray-500">Loading available quarters…</div>
				{:else if registerTargets.length === 0}
					<div class="mt-3 text-sm text-gray-500">
						You are already a member of every active quarter, or none are available to join.
					</div>
				{:else}
					<ul class="mt-3 space-y-2">
						{#each registerTargets as quarter (quarter.canister_id)}
							<li class="flex flex-wrap items-center justify-between gap-2 rounded border border-gray-200 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700">
								<div class="min-w-0">
									<div class="text-sm font-medium text-gray-900 dark:text-white">
										{formatQuarterLabel(quarter as any)}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400 font-mono break-all">
										{quarter.canister_id}
									</div>
									<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
										{quarter.population} users
									</div>
								</div>
								<button
									type="button"
									onclick={() => handleRegister(quarter.canister_id)}
									disabled={!!registeringCanisterId || loadingUserStatus || !profiles.length}
									class="px-3 py-1.5 text-sm font-medium text-gray-800 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-600 dark:text-white dark:border-gray-500 dark:hover:bg-gray-500"
								>
									{registeringCanisterId === quarter.canister_id ? 'Registering…' : 'Register here'}
								</button>
							</li>
						{/each}
					</ul>
				{/if}

				{#if registerError}
					<div class="mt-2 text-sm text-red-600 dark:text-red-400">{registerError}</div>
				{/if}
				{#if registerSuccess}
					<div class="mt-2 text-sm text-green-600 dark:text-green-400">{registerSuccess}</div>
				{/if}
			</div>
		</div>
		{:else if $realmInfo.quarters.length === 1}
		<div class="col-span-full mt-6">
			<Heading tag="h2" class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
				{$_('settings.quarter_title', { default: 'Quarter' })}
			</Heading>
			<div class="p-4 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
				<span class="font-semibold">Current quarter:</span>
				<span class="ml-1">{labelForCanister($realmInfo.quarters[0]?.canister_id || sessionQuarterId)}</span>
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
				{#each $realmInfo.registries as reg (reg.canister_id)}
					<div class="p-3 bg-gray-50 rounded border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
						<span class="font-semibold">{reg.canister_type}:</span>
						<span class="font-mono text-sm break-all ml-1">{reg.canister_id}</span>
					</div>
				{/each}
			</div>
		</div>
		{/if}

	</div>
</main>
