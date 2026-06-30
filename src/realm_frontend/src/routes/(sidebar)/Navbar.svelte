<script>
	import AuthButton from '$lib/components/AuthButton.svelte';
	import QuarterSwitcher from '$lib/components/QuarterSwitcher.svelte';
	import QuarterIndicator from '$lib/components/QuarterIndicator.svelte';
	import DelegationSwitcher from '$lib/components/DelegationSwitcher.svelte';
	import { realmInfo, realmName, aiAssistantEnabled } from '$lib/stores/realmInfo';
	import { onMount } from 'svelte';
	import { Navbar } from 'flowbite-svelte';
	import { IconMessageChatbot, IconMenu2 } from '@tabler/icons-svelte';
	import { _ } from 'svelte-i18n';
	import '../../app.pcss';

	export let fluid = true;
	export let drawerHidden = false;
	export let aiPanelOpen = false;

	onMount(() => {
		realmInfo.fetch();
	});
</script>

<Navbar {fluid} class="text-black relative z-50" color="default" let:NavContainer style="pointer-events: auto;">
	<button
		type="button"
		on:click={() => (drawerHidden = !drawerHidden)}
		class="m-0 inline-flex p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200 text-gray-600 hover:text-gray-900"
		aria-label="Toggle navigation menu"
		aria-expanded={!drawerHidden}
	>
		<IconMenu2 size={22} />
	</button>

	<div class="absolute left-1/2 transform -translate-x-1/2">
		<a href="/" class="flex items-center cursor-pointer">
			<img
				src={$realmInfo.logoUrl || '/custom/logo.png'}
				class="h-8 sm:h-10 pointer-events-none"
				alt={$realmName || 'Realms Logo'}
			/>
			<span
				class="ml-3 self-center whitespace-nowrap text-xl font-medium text-gray-700 sm:text-2xl pointer-events-none"
			>
				{$realmName || ''}
			</span>
		</a>
	</div>

	<div class="ms-auto flex items-center gap-2 text-gray-500">
		<QuarterIndicator />
		<QuarterSwitcher />
		<DelegationSwitcher />
		{#if $aiAssistantEnabled}
		<!-- AI Assistant toggle button -->
		<button
			on:click={() => (aiPanelOpen = !aiPanelOpen)}
			class="group inline-flex items-center gap-1.5 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
			title={$_('common.assistant', { default: 'Assistant' })}
			aria-label={$_('common.assistant', { default: 'Assistant' })}
		>
			<IconMessageChatbot size={22} class={aiPanelOpen ? 'text-gray-900' : 'text-gray-500'} />
			<span
				class="hidden md:inline-block md:max-w-0 md:overflow-hidden md:opacity-0 md:group-hover:max-w-[8rem] md:group-hover:opacity-100 md:group-focus-visible:max-w-[8rem] md:group-focus-visible:opacity-100 transition-[max-width,opacity] duration-500 ease-in-out text-sm font-medium whitespace-nowrap"
			>
				{$_('common.assistant', { default: 'Assistant' })}
			</span>
		</button>
		{/if}

		<AuthButton />
	</div>
</Navbar>
