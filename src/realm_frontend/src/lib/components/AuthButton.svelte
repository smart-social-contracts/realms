<!-- src/lib/components/AuthButton.svelte -->
<script>
	import { login, logout, isAuthenticated as checkAuth } from '$lib/auth';
	import { isAuthenticated, userIdentity, principal } from '$lib/stores/auth';
	import { userProfiles } from '$lib/stores/profiles';
	import { Avatar} from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import { _ } from 'svelte-i18n';
	import T from '$lib/components/T.svelte';
	import { initBackendWithIdentity, backend } from '$lib/canisters';

	import { Button } from 'flowbite-svelte';

	let principalText = '';

	async function loadUserProfiles() {
		try {
			if (!backend || typeof backend.get_my_user_status !== 'function') {
				console.error("Backend canister is not properly initialized");
				return;
			}
			
			const response = await backend.get_my_user_status();
			
			if (response && response.success && response.data && response.data.UserGet) {
				const profiles = response.data.UserGet.profiles || [];
				userProfiles.set(profiles);
				console.log("User profiles loaded:", profiles);
			} else {
				console.error("Invalid backend response format:", response);
			}
		} catch (e) {
			console.error("Error loading user profiles:", e);
		}
	}

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
		// Load user profiles
		await loadUserProfiles();
	}

	async function handleLogout() {
		await logout();
		isAuthenticated.set(false);
		principalText = '';
		userIdentity.set(null);
		principal.set(''); // Reset the principal store
		userProfiles.set([]); // Reset user profiles

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
{:else}
	<Button color="alternative" pill={true} on:click={handleLogin}>
		<T key="common.login" default_text="Log In" />
	</Button>
{/if}
</div>