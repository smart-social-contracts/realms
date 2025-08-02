<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Tabs, TabItem, Spinner, Button, Input, Alert } from 'flowbite-svelte';
	import { ChartPieSolid, ClockSolid, WalletSolid,
		ChartOutline, PaperPlaneSolid, DollarOutline } from 'flowbite-svelte-icons';
	import { principal, universe, snapshots } from '$lib/stores/auth';
	import { formatNumber } from '$lib/utils';
	import { writable } from 'svelte/store';
	import AuthButton from '$lib/components/AuthButton.svelte';
	import { _ } from 'svelte-i18n';
	import { safeTranslate } from '$lib/i18n/safe-translate.js';

	// Import backend directly without using await in top-level
	import { backend } from '$lib/canisters';
	import { isDevelopmentMode } from '$lib/dev-mode.js';

	let Some;
	if (!isDevelopmentMode()) {
		import('@dfinity/candid').then(module => { Some = module.Some; });
	} else {
		Some = (value) => ({ Some: value });
	}

	let greeting = '';
	
	// Safe translations for visible UI elements
	$: safeTitle = $safeTranslate('extensions.test_bench.title');
	$: safeExtensionApiTesting = $safeTranslate('extensions.test_bench.extension_api_testing');
	$: safeCallTestbenchApi = $safeTranslate('extensions.test_bench.call_testbench_api');
	$: safeAuthentication = $safeTranslate('extensions.test_bench.authentication');
	$: safeGreetingTest = $safeTranslate('extensions.test_bench.greeting_test');
	$: safeEnterName = $safeTranslate('extensions.test_bench.enter_name');
	$: safeSubmitGreeting = $safeTranslate('extensions.test_bench.submit_greeting');
	$: safeUniverseData = $safeTranslate('extensions.test_bench.universe_data');
	$: safeGetUniverseData = $safeTranslate('extensions.test_bench.get_universe_data');
	$: safeUniverseDataLabel = $safeTranslate('extensions.test_bench.universe_data_label');
	$: safeSnapshotData = $safeTranslate('extensions.test_bench.snapshot_data');
	$: safeGetSnapshots = $safeTranslate('extensions.test_bench.get_snapshots');
	$: safeSnapshotsLabel = $safeTranslate('extensions.test_bench.snapshots_label');

	function onSubmit(event) {
		const name = event.target.name.value;
		backend.greet(name).then((response) => {
			greeting = response;
		});
	}

	function onSubmitGetUniverse(event) {
		backend.get_universe().then((response) => {
			universe.set(response);
		});
	}

	function get_snapshot_data(event) {
		backend.get_snapshots().then((response) => {
			snapshots.set(response);
		});
	}
</script>	


<div class="p-4">
	<h2 class="text-2xl font-bold mb-6">{safeTitle}</h2>

	<Card class="mb-6">
		<h3 class="text-lg font-semibold mb-4">{safeExtensionApiTesting}</h3>
		<Button
			color="primary"
			variant="filled"
			size="lg"
			class="w-full my-4 p-4 text-xl font-bold shadow-lg rounded-lg"
			onclick={() => {
				// Use the simplest approach possible
				backend.extension_async_call({
					extension_name: "test_bench",
					function_name: "get_data",
					args: "from frontend"
				}).then(response => {
					alert("Response from extension: " + JSON.stringify(response));
				}).catch(error => {
					console.error("Extension call failed:", error);
					alert("Error calling extension: " + error.message);
				});
			}}
		>
			{safeCallTestbenchApi}
		</Button>
	</Card>

	<Card class="mb-6">
		<h3 class="text-lg font-semibold mb-4">{safeAuthentication}</h3>
		<AuthButton />
	</Card>

	<Card class="mb-6">
		<h3 class="text-lg font-semibold mb-4">{safeGreetingTest}</h3>
		<section id="greeting" class="mb-2">{greeting}</section>
		<form action="#" on:submit|preventDefault={onSubmit} class="flex flex-col gap-2">
			<label for="name">{safeEnterName}</label>
			<input id="name" alt="Name" type="text" class="border p-2 rounded" />
			<Button type="submit" color="blue">{safeSubmitGreeting}</Button>
		</form>
	</Card>

	<Card class="mb-6">
		<h3 class="text-lg font-semibold mb-4">{safeUniverseData}</h3>
		<form action="#" on:submit|preventDefault={onSubmitGetUniverse} class="flex flex-col gap-2">
			<Button type="submit" color="green">{safeGetUniverseData}</Button>
		</form>
		{#if $universe != ''}
			<section id="universe" class="mt-4 p-3 bg-gray-100 rounded">
				<h4 class="font-semibold">{safeUniverseDataLabel}</h4>
				<pre class="whitespace-pre-wrap break-words">{JSON.stringify($universe, null, 2)}</pre>
			</section>
		{/if}
	</Card>

	<Card class="mb-6">
		<h3 class="text-lg font-semibold mb-4">{safeSnapshotData}</h3>
		<form action="#" on:submit|preventDefault={get_snapshot_data} class="flex flex-col gap-2">
			<Button type="submit" color="purple">{safeGetSnapshots}</Button>
		</form>
		{#if $snapshots != ''}
			<section id="snapshots" class="mt-4 p-3 bg-gray-100 rounded">
				<h4 class="font-semibold">{safeSnapshotsLabel}</h4>
				<pre class="whitespace-pre-wrap break-words">{JSON.stringify($snapshots, null, 2)}</pre>
			</section>
		{/if}
	</Card>
</div>
