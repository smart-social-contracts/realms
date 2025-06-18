<!-- src/lib/components/AuthButton.svelte -->
<script>
	import { login, logout, isAuthenticated as checkAuth } from '$lib/auth';
	import { isAuthenticated, userIdentity, principal } from '$lib/stores/auth';
	import { Avatar} from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import { _ } from 'svelte-i18n';
	import T from '$lib/components/T.svelte';
	import { initBackendWithIdentity } from '$lib/canisters';

	import { Button } from 'flowbite-svelte';

	let principalText = '';

	onMount(async () => {
		const authStatus = await checkAuth();
		isAuthenticated.set(authStatus);
		if (authStatus) {
			const { principal: userPrincipal } = await login();
			principalText = userPrincipal.toText();
			userIdentity.set(principalText);
			principal.set(principalText); // Update the principal store

			console.log('Principal at login:', principalText); // Debugging principal value after login
			// Initialize backend with authenticated identity
			await initBackendWithIdentity();
		}
	});

	async function handleLogin() {
		const { principal: userPrincipal } = await login();
		isAuthenticated.set(true);
		principalText = userPrincipal.toText();

		userIdentity.set(principalText);
		principal.set(principalText); // Update the principal store

		console.log('Principal at login:', principalText); // Debugging principal value after login
		// Initialize backend with authenticated identity
		await initBackendWithIdentity();
	}

	async function handleLogout() {
		await logout();
		isAuthenticated.set(false);
		principalText = '';
		userIdentity.set(null);
		principal.set(''); // Reset the principal store

		console.log('Principal after logout:', principalText); // Confirm principal reset
	}

	function generateAvatarUrl(seed) {
		// You can customize the style (e.g., 'avataaars', 'bottts', etc.)
		return `https://api.dicebear.com/9.x/identicon/svg?seed=${seed}`;
	}
</script>


<div class="flex space-x-4 items-center">
{#if $isAuthenticated}
	<Avatar src={generateAvatarUrl($principal)} tabindex={0} title={`Principal: ${$principal}`} />
	<Button color="alternative" pill={true} on:click={handleLogout}>
		<T key="common.logout" default_text="Log Out" />
	</Button>
	<Button size="xs" on:click={() => {
		import('$lib/auth').then(module => {
			// Re-login to update the principal in the stores
			handleLogin();
		});
	}}>
		<T key="buttons.switch_user" default_text="Switch User" />
	</Button>
{:else}
	<Button color="alternative" pill={true} on:click={handleLogin}>
		<T key="common.login" default_text="Log In" />
	</Button>
{/if}
</div>