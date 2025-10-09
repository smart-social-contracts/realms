<!-- src/lib/components/AuthButton.svelte -->
<script>
	import { login, logout, isAuthenticated as checkAuth, initializeAuthClient } from '$lib/auth';
	import { isAuthenticated, userIdentity, principal } from '$lib/stores/auth';
	import { loadUserProfiles, resetProfileState } from '$lib/stores/profiles';
	import { Avatar, Button } from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import { _ } from 'svelte-i18n';
	import T from '$lib/components/T.svelte';
	import { initBackendWithIdentity, backend } from '$lib/canisters';

	let principalText = '';
	let showDropdown = false;

	// Using the centralized profile loading function from the store

	onMount(async () => {
		const authStatus = await checkAuth();
		isAuthenticated.set(authStatus);
		if (authStatus) {
			// Get existing identity without triggering new login
			const client = await initializeAuthClient();
			const identity = client.getIdentity();
			const userPrincipal = identity.getPrincipal();
			principalText = userPrincipal.toText();
			userIdentity.set(principalText);
			principal.set(principalText);

			console.log('Principal restored from existing session:', principalText);
		// Initialize backend with authenticated identity
		await initBackendWithIdentity();
		// Load user profiles
		await loadUserProfiles();
		await loadUserProfilePicture();
		}
		
		// Add a click handler to close dropdown when clicking outside
		const handleClickOutside = (event) => {
			if (showDropdown && !event.target.closest('.avatar-dropdown')) {
				showDropdown = false;
			}
		};
		
		document.addEventListener('click', handleClickOutside);
		
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
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
		await loadUserProfilePicture();
	}

	async function handleLogout() {
		await logout();
		isAuthenticated.set(false);
		principalText = '';
		userIdentity.set(null);
		principal.set('');
		
		// Reset the entire profile state instead of just clearing profiles array
		resetProfileState();

		// Clear sessionStorage on logout
		if (typeof sessionStorage !== 'undefined') {
			sessionStorage.removeItem('auth_isAuthenticated');
			sessionStorage.removeItem('auth_userIdentity');
			sessionStorage.removeItem('auth_principal');
		}

		console.log('Principal after logout:', principalText);
		showDropdown = false;
	}

	function generateAvatarUrl(seed, profilePictureUrl) {
		// Use profile picture URL if available, otherwise fall back to DiceBear
		if (profilePictureUrl && profilePictureUrl.trim()) {
			return profilePictureUrl;
		}
		return `https://api.dicebear.com/9.x/identicon/svg?seed=${seed}`;
	}

	let userProfilePictureUrl = '';

	async function loadUserProfilePicture() {
		try {
			const response = await backend.get_my_user_status();
			if (response && response.success && response.data && response.data.userGet) {
				userProfilePictureUrl = response.data.userGet.profile_picture_url || '';
			}
		} catch (error) {
			console.error('Error loading user profile picture:', error);
			userProfilePictureUrl = '';
		}
	}

	// Listen for profile picture updates from settings page
	function handleProfilePictureUpdate(event) {
		if (event.detail && event.detail.profilePictureUrl !== undefined) {
			userProfilePictureUrl = event.detail.profilePictureUrl;
		}
	}

	onMount(() => {
		// Listen for custom events when profile picture is updated
		window.addEventListener('profilePictureUpdated', handleProfilePictureUpdate);
		
		return () => {
			window.removeEventListener('profilePictureUpdated', handleProfilePictureUpdate);
		};
	});

	// Get a shortened display version of the principal
	$: shortPrincipal = $principal ? `${$principal.substring(0, 8)}...${$principal.slice(-8)}` : '';
	
	// Toggle dropdown without event propagation
	function toggleDropdown(event) {
		event.stopPropagation();
		showDropdown = !showDropdown;
	}
</script>


<div class="flex items-center">
{#if $isAuthenticated}
	<div class="avatar-dropdown relative">
		<!-- Avatar Image -->
		<div 
			class="cursor-pointer" 
			role="button"
			aria-haspopup="true"
			aria-expanded={showDropdown}
			tabindex="0"
			on:click={toggleDropdown}
			on:keydown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					toggleDropdown(e);
				}
			}}
		>
		<Avatar 
			src={generateAvatarUrl($principal, userProfilePictureUrl)} 
			tabindex={0} 
			title={`Principal: ${$principal}`} 
			alt="User avatar"
		/>
		</div>
		
		<!-- Dropdown Menu -->
		{#if showDropdown}
			<div 
				class="absolute right-0 mt-2 w-48 z-50 bg-white rounded-lg shadow-xl border border-gray-200 dark:bg-gray-800 dark:border-gray-700" 
				role="menu"
			>
				<div class="px-4 py-3">
					<p class="text-sm text-gray-900 dark:text-white truncate">
						{shortPrincipal}
					</p>
				</div>
				<hr class="h-px my-2 bg-gray-200 border-0 dark:bg-gray-700">
				<button 
					class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
					role="menuitem"
					on:click={handleLogout}
				>
					<T key="common.logout" default_text="Log Out" />
				</button>
			</div>
		{/if}
	</div>
{:else}
	<Button color="alternative" pill={true} on:click={handleLogin}>
		<T key="common.login" default_text="Log In" />
	</Button>
{/if}
</div>
