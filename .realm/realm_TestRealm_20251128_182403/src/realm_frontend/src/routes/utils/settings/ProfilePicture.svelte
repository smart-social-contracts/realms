<script lang="ts">
	import { Avatar, Button, Card, Heading, Input, Label } from 'flowbite-svelte';
	import { _ } from 'svelte-i18n';
	import { backend } from '$lib/canisters';
	import { onMount } from 'svelte';

	export let src: string;
	
	let profilePictureUrl = '';
	let isLoading = false;
	let message = '';

	onMount(async () => {
	});

	async function loadCurrentProfilePicture() {
		try {
			const response = await backend.get_my_user_status();
			if (response && response.success && response.data && response.data.userGet) {
				profilePictureUrl = response.data.userGet.profile_picture_url || '';
			}
		} catch (error) {
			console.error('Error loading profile picture:', error);
		}
	}

	async function updateProfilePicture() {
		if (!profilePictureUrl.trim()) {
			message = 'Please enter a valid URL';
			return;
		}

		isLoading = true;
		message = '';

		try {
			const response = await backend.update_my_profile_picture(profilePictureUrl.trim());
			if (response && response.success) {
				message = 'Profile picture updated successfully!';
				// Dispatch custom event to update avatar in header without page refresh
				window.dispatchEvent(new CustomEvent('profilePictureUpdated', {
					detail: { profilePictureUrl: profilePictureUrl.trim() }
				}));
			} else {
				message = 'Failed to update profile picture';
			}
		} catch (error) {
			console.error('Error updating profile picture:', error);
			message = 'Error updating profile picture';
		} finally {
			isLoading = false;
		}
	}

	async function removeProfilePicture() {
		isLoading = true;
		message = '';

		try {
			const response = await backend.update_my_profile_picture('');
			if (response && response.success) {
				profilePictureUrl = '';
				message = 'Profile picture removed successfully!';
				// Dispatch custom event to update avatar in header
				window.dispatchEvent(new CustomEvent('profilePictureUpdated', {
					detail: { profilePictureUrl: '' }
				}));
			} else {
				message = 'Failed to remove profile picture';
			}
		} catch (error) {
			console.error('Error removing profile picture:', error);
			message = 'Error removing profile picture';
		} finally {
			isLoading = false;
		}
	}

	$: displaySrc = profilePictureUrl || src;
</script>

<Card
	size="xl"
	class="block shadow-sm sm:flex sm:space-x-4 sm:py-6 xl:block xl:space-x-0 2xl:flex 2xl:space-x-4"
	horizontal
>
	<Avatar src={displaySrc} class="mb-4 h-28 w-28 rounded-lg sm:mb-0 xl:mb-4 2xl:mb-0" size="none" rounded />

	<div class="py-0.5 flex-1">
		<Heading tag="h3" class="text-xl">{$_('settings.profile_picture')}</Heading>
		<p class="mb-4 mt-1 pt-px text-sm">Enter a URL to your profile picture</p>
		
		<div class="mb-4">
			<Label for="profile-url" class="mb-2">Profile Picture URL</Label>
			<Input 
				id="profile-url"
				bind:value={profilePictureUrl} 
				placeholder="https://example.com/your-photo.jpg"
				class="mb-2"
			/>
		</div>

		{#if message}
			<p class="mb-4 text-sm {message.includes('success') ? 'text-green-600' : 'text-red-600'}">{message}</p>
		{/if}

		<div class="flex items-center space-x-4">
			<Button 
				size="sm" 
				class="px-3" 
				color="alternative" 
				on:click={updateProfilePicture}
				disabled={isLoading}
			>
				{isLoading ? 'Updating...' : 'Update picture'}
			</Button>
			<Button 
				size="sm" 
				class="px-3" 
				color="alternative" 
				on:click={removeProfilePicture}
				disabled={isLoading}
			>
				Remove
			</Button>
		</div>
	</div>
</Card>
