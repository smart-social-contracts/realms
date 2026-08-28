<script>
	import { Button, Modal, Toggle, Alert } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	import { realmInfo, testMode } from '$lib/stores/realmInfo';
	import { NOTICE_LOCALE_SLOTS } from '$lib/config/hostTestFlags';
	import { localeLabel } from '$lib/i18n/realmLocales';

	export let open = false;

	const FLAGS = [
		{ key: 'test_mode', store: 'testMode', label: 'Test mode', hint: 'Master switch — turning this off hides this editor and locks flags to admins' },
		{ key: 'ii_bypass', store: 'testModeIIBypass', label: 'II bypass', hint: 'Skip Internet Identity and show the deterministic test identity picker' },
		{ key: 'user_self_registration', store: 'testModeUserSelfRegistration', label: 'User self-registration', hint: 'Allow users to join without an invitation code' },
		{ key: 'demo_data', store: 'testModeDemoData', label: 'Demo data', hint: 'Auto-activate the demo data simulator' },
		{ key: 'skip_terms', store: 'testModeSkipTerms', label: 'Skip terms', hint: 'Skip the demo notice step on join' },
		{ key: 'skip_passport_zkproof', store: 'testModeSkipPassportZkproof', label: 'Skip passport ZK-proof', hint: 'Bypass passport zero-knowledge verification' },
		{ key: 'disable_monetary_tokens', store: 'testModeDisableMonetaryTokens', label: 'Disable monetary tokens', hint: 'Gray out ckBTC, ckUSDC, ckEURC, and Custom. REALMS stays selectable. Does not strip an already-configured ledger.' },
		{ key: 'demo_notice', store: 'testModeDemoNotice', label: 'Demo notice', hint: 'Show the configurable demo notice on founder setup and join' }
	];

	let values = {};
	let noticeBodies = {};
	let saving = false;
	let error = '';
	let message = '';

	// Snapshot current flags each time the modal opens
	$: if (open) syncFromStore();

	function syncFromStore() {
		const info = $realmInfo;
		const next = {};
		for (const f of FLAGS) next[f.key] = !!info[f.store];
		values = next;
		const stored = info.demoNoticeBody || {};
		const bodies = {};
		for (const loc of NOTICE_LOCALE_SLOTS) bodies[loc] = stored[loc] || '';
		noticeBodies = bodies;
		error = '';
		message = '';
	}

	async function save() {
		saving = true;
		error = '';
		message = '';
		try {
			const raw = await backend.set_test_flags_json(
				JSON.stringify({
					test_flags: { ...values, demo_notice_body: noticeBodies }
				})
			);
			const result = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (!result?.success) {
				throw new Error(result?.error || 'Failed to update test flags');
			}
			await realmInfo.fetch();
			message = 'Test flags updated';
			if (!values.test_mode) open = false;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			saving = false;
		}
	}
</script>

{#if $testMode}
	<Modal bind:open title="Test flags" size="lg" autoclose={false} outsideclose>
		<p class="text-sm text-gray-500 dark:text-gray-400">
			This realm runs in test mode. Anyone can view and change these runtime flags while
			test mode is enabled.
		</p>
		<Alert color="red" class="border border-red-300">
			<span class="font-semibold">WARNING:</span> turning off "Test mode" hides this editor and
			locks further flag changes to canister admins.
		</Alert>
		<div class="space-y-4">
			{#each FLAGS as flag}
				<div class="flex items-start justify-between gap-4">
					<div>
						<p class="text-sm font-medium text-gray-900 dark:text-white">{flag.label}</p>
						<p class="text-xs text-gray-500 dark:text-gray-400">{flag.hint}</p>
					</div>
					<Toggle color="blue" bind:checked={values[flag.key]} disabled={saving} />
				</div>
			{/each}
			<div class="space-y-2 pt-2 border-t border-gray-200 dark:border-gray-700">
				<p class="text-sm font-medium text-gray-900 dark:text-white">Demo notice body</p>
				<p class="text-xs text-gray-500 dark:text-gray-400">
					English is seeded from Legal. Other locale slots stay empty until Legal/Story writes them.
				</p>
				{#each NOTICE_LOCALE_SLOTS as loc}
					<label class="block">
						<span class="text-xs font-medium text-gray-600 dark:text-gray-300">
							{localeLabel(loc)}{loc === 'en' ? ' (seeded default)' : ' (slot)'}
						</span>
						<textarea
							class="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs text-gray-900"
							rows={loc === 'en' ? 8 : 3}
							bind:value={noticeBodies[loc]}
							disabled={saving}
							placeholder={loc === 'en' ? '' : 'Leave empty until Legal writes this locale'}
						></textarea>
					</label>
				{/each}
			</div>
		</div>
		{#if error}
			<Alert color="red" class="mt-2">{error}</Alert>
		{/if}
		{#if message}
			<Alert color="green" class="mt-2">{message}</Alert>
		{/if}
		<svelte:fragment slot="footer">
			<!-- Explicit colors: the flowbite primary palette maps to --color-primary-*
			     CSS vars that are unset on realms without branding. -->
			<Button
				color="none"
				class="bg-gray-900 text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900"
				on:click={save}
				disabled={saving}
			>
				{saving ? 'Saving…' : 'Save'}
			</Button>
			<Button color="alternative" on:click={() => (open = false)} disabled={saving}>Close</Button>
		</svelte:fragment>
	</Modal>
{/if}
