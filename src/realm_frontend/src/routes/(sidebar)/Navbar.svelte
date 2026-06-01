<script>
	import AuthButton from '$lib/components/AuthButton.svelte';
	import { realmInfo, realmName } from '$lib/stores/realmInfo';
	import { isAuthenticated } from '$lib/stores/auth';
	import { onMount } from 'svelte';
	import { NavHamburger, Navbar } from 'flowbite-svelte';
	import { IconMessageChatbot } from '@tabler/icons-svelte';
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
	{#if $isAuthenticated}
		<NavHamburger
			onClick={() => (drawerHidden = !drawerHidden)}
			class="m-0 md:block p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
		/>
	{/if}

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
		<!-- AI Assistant toggle button -->
		<button
			on:click={() => (aiPanelOpen = !aiPanelOpen)}
			class="group inline-flex items-center gap-1.5 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
			title={$_('common.assistant', { default: 'Assistant' })}
			aria-label={$_('common.assistant', { default: 'Assistant' })}
		>
			<IconMessageChatbot size={22} class={aiPanelOpen ? 'text-gray-900' : 'text-gray-500'} />
			<span
				class="hidden md:inline-block md:max-w-0 md:overflow-hidden md:opacity-0 md:group-hover:max-w-[8rem] md:group-hover:opacity-100 md:group-focus-visible:max-w-[8rem] md:group-focus-visible:opacity-100 transition-all duration-200 ease-out text-sm font-medium whitespace-nowrap"
			>
				{$_('common.assistant', { default: 'Assistant' })}
			</span>
		</button>

		<AuthButton />
	</div>
</Navbar>
