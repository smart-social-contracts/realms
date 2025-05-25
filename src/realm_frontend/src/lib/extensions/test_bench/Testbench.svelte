<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Tabs, TabItem, Spinner, Button, Input, Alert } from 'flowbite-svelte';
	import { ChartPieSolid, ClockSolid, WalletSolid,
		ChartOutline, PaperPlaneSolid, DollarOutline } from 'flowbite-svelte-icons';
	import { principal } from '$lib/stores/auth';
	import { formatNumber } from '$lib/utils';

	
	// Import backend directly without using await in top-level
	import { backend } from '$lib/canisters';
</script>	


<p>Testbenchs</p>

<Button
	color="primary"
	variant="filled"
	size="lg"
	class="w-full my-4 p-4 text-xl font-bold shadow-lg rounded-lg"
	onclick={() => {
		backend.extension_call({
			extension_name: "test_bench",
			function_name: "get_data",
			args: null,
			kwargs: null,
		});
	}}
>
	Call Testbench
</Button>
