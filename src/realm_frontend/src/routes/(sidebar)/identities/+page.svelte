<script lang="ts">
	import MetaTag from '../../utils/MetaTag.svelte';
	import IdentityCard from '../../utils/settings/IdentityCard.svelte';
	import PassportVerification from '$lib/components/passport/PassportVerification.svelte';
	import { imagesPath } from '../../utils/variables';
	import Footer from '../Footer.svelte';
	import { Button, Card, Heading, P } from 'flowbite-svelte';
	import { PlusOutline, FingerprintOutline, ClipboardListSolid } from 'flowbite-svelte-icons';
	import { userIdentity } from '$lib/stores/auth.js';

	const path: string = '/identities';
	const description: string = 'Manage your digital identities';
	const metaTitle: string = 'My Identities';
	const subtitle: string = 'Identity Management';

	import { onMount } from 'svelte';
	
	let showPassportVerification = false;
	let PASSPORT_IDENTITY_VERIFIED = true; // Set to true to show verified passport card

	onMount(() => {});
</script>

<MetaTag {path} {description} title={metaTitle} {subtitle} />

<div class="mt-4 space-y-6 px-4 md:px-6">
	<!-- Header Section -->
	<div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
		<div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
			<div>
				<div class="flex items-center gap-2 mb-2">
					<FingerprintOutline class="w-6 h-6 text-blue-600 dark:text-blue-500" />
					<Heading tag="h1" class="text-2xl font-bold text-gray-900 dark:text-white">My Identities</Heading>
				</div>
				<p class="text-gray-600 dark:text-gray-400">
					Manage and connect your digital identities securely. Connected identities can be used for authentication and cross-platform verification.
				</p>
			</div>
			<Button size="sm" color="blue" class="px-4 py-2 rounded-lg flex items-center gap-2">
				<PlusOutline class="w-4 h-4" />
				Add New Identity
			</Button>
		</div>
	</div>

	<!-- Identity Cards Section -->
	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
		<div class="transition-all duration-200 hover:shadow-md">
			<IdentityCard 
				src={imagesPath('logo-swissid_bianco.jpg')} 
				title="SwissID" 
				description="Swiss national digital identity provider" 
				status="Verified"
			/>
		</div>

		<!-- Passport Verification Card -->
		<div class="transition-all duration-200 hover:shadow-md">
			{#if PASSPORT_IDENTITY_VERIFIED}
				<IdentityCard 
					src={imagesPath('rarime.png')} 
					title="Passport Identity" 
					description="Verified passport identity using zero-knowledge proofs" 
					status="Verified"
				/>
			{:else}
				<a href="/extensions/passport_verification" class="block">
					<Card size="xl" class="flex flex-col items-center justify-center h-full p-8 border-2 border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 cursor-pointer">
						<div class="flex flex-col items-center text-center">
							<div class="p-3 mb-4 rounded-full bg-blue-100 dark:bg-blue-900">
								<ClipboardListSolid class="w-8 h-8 text-blue-600 dark:text-blue-400" />
							</div>
							<Heading tag="h3" class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">Verify Passport</Heading>
							<P class="mb-5 text-sm text-gray-500 dark:text-gray-400">
								Use zero-knowledge proofs to verify your passport identity securely and privately
							</P>
							<Button size="sm" color="blue" class="px-4 py-2">Start Verification</Button>
						</div>
					</Card>
				</a>
			{/if}
		</div>

		<!-- Empty Card to Add Other Identities -->
		<div class="transition-all duration-200 hover:shadow-md">
			<Card size="xl" class="flex flex-col items-center justify-center h-full p-8 border-2 border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800">
				<div class="flex flex-col items-center text-center">
					<div class="p-3 mb-4 rounded-full bg-gray-100 dark:bg-gray-700">
						<PlusOutline class="w-8 h-8 text-gray-600 dark:text-gray-400" />
					</div>
					<Heading tag="h3" class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">Connect Other Identity</Heading>
					<P class="mb-5 text-sm text-gray-500 dark:text-gray-400">
						Link additional identity providers to enhance your account security
					</P>
					<Button size="sm" color="alternative" class="px-4 py-2" disabled>Coming Soon</Button>
				</div>
			</Card>
		</div>
	</div>

	<!-- Info Section 
	<div class="bg-blue-50 dark:bg-gray-700 p-4 rounded-lg border border-blue-200 dark:border-gray-600">
		<p class="text-sm text-blue-800 dark:text-blue-200">
			<span class="font-semibold">Security Tip:</span> Connecting multiple identity providers enhances your account security and enables cross-platform verification capabilities.
		</p>
	</div>
	-->
</div>
<!-- <Footer /> -->
