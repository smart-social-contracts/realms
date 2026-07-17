<script>
	import { Button, Modal, Toggle, Alert } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	import { realmInfo, testMode } from '$lib/stores/realmInfo';

	export let open = false;

	const FLAGS = [
		{ key: 'test_mode', store: 'testMode', label: 'Test mode', hint: 'Master switch — turning this off hides this editor and locks flags to admins' },
		{ key: 'ii_bypass', store: 'testModeIIBypass', label: 'II bypass', hint: 'Skip Internet Identity and show the deterministic test identity picker' },
		{ key: 'user_self_registration', store: 'testModeUserSelfRegistration', label: 'User self-registration', hint: 'Allow users to join without an invitation code' },
		{ key: 'demo_data', store: 'testModeDemoData', label: 'Demo data', hint: 'Auto-activate the demo data simulator' },
		{ key: 'skip_terms', store: 'testModeSkipTerms', label: 'Skip terms', hint: 'Skip the terms & conditions step on join' },
		{ key: 'skip_passport_zkproof', store: 'testModeSkipPassportZkproof', label: 'Skip passport ZK-proof', hint: 'Bypass passport zero-knowledge verification' }
	];

	let values = {};
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
		error = '';
		message = '';
	}

	async function save() {
		saving = true;
		error = '';
		message = '';
		try {
			const raw = await backend.set_test_flags_json(JSON.stringify({ test_flags: values }));
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
	<Modal bind:open title="Test flags" size="sm" autoclose={false} outsideclose>
		<p class="text-sm text-gray-500 dark:text-gray-400">
			This realm runs in test mode. Anyone can view and change these runtime flags while
			test mode is enabled.
		</p>
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
