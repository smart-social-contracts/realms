<script lang="ts">
	import ChartWidget from '../../../routes/utils/widgets/ChartWidget.svelte';
	import { onMount } from 'svelte';
	import ActivityList from '../../../routes/(sidebar)/dashboard/ActivityList.svelte';
	import OrganizationTable from '../../../routes/utils/dashboard/OrganizationTable.svelte';
	import { backend } from '$lib/canisters';
	import { principal } from '$lib/stores/auth';
	import { universe, snapshots } from '$lib/stores/auth';
	import { writable } from 'svelte/store';
	import { _ } from 'svelte-i18n';
	import { Avatar, Card, Heading } from 'flowbite-svelte';

	let greeting = '';
	let latestUsers = [];

	const mockUserData = [
		['01 Jan', '03 Jan', '05 Jan', '07 Jan', '09 Jan', '11 Jan', '13 Jan', '15 Jan', '17 Jan', '19 Jan', '21 Jan'],
		[120, 145, 160, 175, 185, 190, 210, 250, 290, 310, 350]
	];
	
	const mockOrgData = [
		['01 Jan', '03 Jan', '05 Jan', '07 Jan', '09 Jan', '11 Jan', '13 Jan', '15 Jan', '17 Jan', '19 Jan', '21 Jan'],
		[5, 5, 6, 6, 7, 8, 8, 9, 10, 12, 15]
	];
	
	const mockAssetData = [
		['01 Jan', '03 Jan', '05 Jan', '07 Jan', '09 Jan', '11 Jan', '13 Jan', '15 Jan', '17 Jan', '19 Jan', '21 Jan'],
		[22000000, 22200000, 22500000, 22800000, 23000000, 23400000, 23800000, 24000000, 24500000, 24800000, 25000000]
	];

	const statsDatesValues = writable<[string[], number[]]>(mockUserData);
	const orgsDatesValues = writable<[string[], number[]]>(mockOrgData);
	const assetsDatesValues = writable<[string[], number[]]>(mockAssetData);

	function onSubmit(event) {
		const name = event.target.name.value;
		backend.greet(name).then((response) => {
			greeting = response;
		});

		backend.get_universe().then((response) => {
			let principalText = response;
			console.log(`principalText = ${principalText}`);
			principal.set(principalText);
			const jsonObject = JSON.parse(principalText);
			console.log(jsonObject);
			console.log(jsonObject.users[0].id);
		});

		return false;
	}

	function onSubmitGetUniverse(event) {
		backend.status().then((response) => {
			console.log('status', response);
			universe.set(response);
		});
		return false;
	}

	function get_snapshot_data() {
		console.log('Using mock data');
		
		return false;
	}

	async function loadLatestUsers() {
		try {
			const response = await backend.get_users(0, 8);
			console.log('Users response:', response);
			if (response && response.success && response.data && response.data.UsersList) {
				// Parse the JSON strings returned by the backend
				const usersJsonStrings = response.data.UsersList.users || [];
				latestUsers = usersJsonStrings.map(userJsonString => JSON.parse(userJsonString));
				console.log('Parsed users:', latestUsers);
			}
		} catch (error) {
			console.error('Error loading latest users:', error);
			latestUsers = [];
		}
	}

	$: console.log('Parent statsDatesValues updated:', $statsDatesValues);

	onMount(() => {
		get_snapshot_data();
		loadLatestUsers();
	});
</script>

<div class="mt-px space-y-4">
	<ChartWidget
		title={$_('extensions.public_dashboard.users_chart.title')}
		description={$_('extensions.public_dashboard.users_chart.description')}
		dateValues={$statsDatesValues}
	/>

	<!-- Latest Users Joined Section -->
	<Card class="w-full">
		<div class="flex items-center justify-between mb-6">
			<Heading tag="h3" class="text-lg font-semibold">
				{$_('extensions.public_dashboard.latest_users.title')}
			</Heading>
		</div>
		<div class="flex flex-wrap gap-6 justify-start w-full">
			{#each latestUsers as user}
				<div class="flex flex-col items-center space-y-2 min-w-0">
					<Avatar 
						src={user.profile_picture_url || `https://api.dicebear.com/9.x/identicon/svg?seed=${user.id}`}
						class="w-16 h-16 ring-2 ring-gray-200 hover:ring-gray-300 transition-all duration-200"
						alt={user.name || user.id}
					/>
					<span class="text-xs text-gray-600 text-center max-w-[4rem] truncate" title={user.name || user.id}>
						{user.name || user.id.substring(0, 8)}
					</span>
				</div>
			{/each}
		</div>
	</Card>

	<ChartWidget
		title={$_('extensions.public_dashboard.organizations_chart.title')}
		description={$_('extensions.public_dashboard.organizations_chart.description')}
		dateValues={$orgsDatesValues}
	/>

	<ChartWidget
		title={$_('extensions.public_dashboard.assets_chart.title')}
		description={$_('extensions.public_dashboard.assets_chart.description')}
		dateValues={$assetsDatesValues}
	/>

	<OrganizationTable />
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-1">
		<ActivityList />
	</div>

</div>
