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
	import SafeText from '$lib/components/SafeText.svelte';

	// Import backend directly without using await in top-level
	import { backend } from '$lib/canisters';

	let greeting = '';

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
	<h1 class="text-3xl font-bold text-gray-900 mb-6">
		<SafeText key="extensions.test_bench.title" spinnerSize="sm" />
	</h1>

	<Card class="mb-6">
		<p class="text-lg text-gray-700 mb-8">
			<SafeText key="extensions.test_bench.extension_api_testing" spinnerSize="sm" />
		</p>
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
			<SafeText key="extensions.test_bench.call_testbench_api" spinnerSize="xs" />
		</Button>
	</Card>

	<Card class="mb-6">
		<h2 class="text-xl font-semibold mb-4">
			<SafeText key="extensions.test_bench.authentication" spinnerSize="sm" />
		</h2>
		<AuthButton />
	</Card>

	<Card class="mb-6">
		<h3 class="text-lg font-medium mb-2">
			<SafeText key="extensions.test_bench.greeting_test" spinnerSize="sm" />
		</h3>
		<section id="greeting" class="mb-2">{greeting}</section>
		<form action="#" on:submit|preventDefault={onSubmit} class="flex flex-col gap-2">
			<label for="name">
				<SafeText key="extensions.test_bench.enter_name" spinnerSize="xs" />
			</label>
			<input id="name" alt="Name" type="text" class="border p-2 rounded" />
			<Button type="submit" color="blue">
				<SafeText key="extensions.test_bench.submit_greeting" spinnerSize="xs" />
			</Button>
		</form>
	</Card>

	<Card class="mb-6">
		<h3 class="text-lg font-medium mb-2">
			<SafeText key="extensions.test_bench.universe_data" spinnerSize="sm" />
		</h3>
		<form action="#" on:submit|preventDefault={onSubmitGetUniverse} class="flex flex-col gap-2">
			<Button type="submit" color="green">
				<SafeText key="extensions.test_bench.get_universe_data" spinnerSize="xs" />
			</Button>
		</form>
		{#if $universe != ''}
			<section id="universe" class="mt-4 p-3 bg-gray-100 rounded">
				<h4 class="font-semibold">
					<strong>
						<SafeText key="extensions.test_bench.universe_data_label" spinnerSize="xs" />
					</strong>
				</h4>
				<pre class="whitespace-pre-wrap break-words">{JSON.stringify($universe, null, 2)}</pre>
			</section>
		{/if}
	</Card>

	<Card class="mb-6">
		<h3 class="text-lg font-medium mb-2">
			<SafeText key="extensions.test_bench.snapshot_data" spinnerSize="sm" />
		</h3>
		<form action="#" on:submit|preventDefault={get_snapshot_data} class="flex flex-col gap-2">
			<Button type="submit" color="purple">
				<SafeText key="extensions.test_bench.get_snapshots" spinnerSize="xs" />
			</Button>
		</form>
		{#if $snapshots != ''}
			<section id="snapshots" class="mt-4 p-3 bg-gray-100 rounded">
				<h4 class="font-semibold">
					<strong>
						<SafeText key="extensions.test_bench.snapshots_label" spinnerSize="xs" />
					</strong>
				</h4>
				<pre class="whitespace-pre-wrap break-words">{JSON.stringify($snapshots, null, 2)}</pre>
			</section>
		{/if}
	</Card>
</div>
