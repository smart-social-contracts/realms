<script>
  import { Button, Card, Radio, Label, Spinner, Select, Checkbox } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { principal, isAuthenticated } from '$lib/stores/auth';
  import { backend } from '$lib/canisters.js';
  import PassportVerification from '$lib/components/passport/PassportVerification.svelte';
  
  let agreement = '';
  let error = '';
  let success = false;
  let loading = false;
  let realmName = 'Realm';
  let selectedProfile = 'member'; // Default to member profile
  let includePassportVerification = false;
  
  // Available profiles
  const profiles = [
    { value: 'member', name: 'Member' },
    { value: 'admin', name: 'Administrator' },
  ];
  
  // URL for local Flask backend API
  const API_BASE_URL = 'http://localhost:5000/api/v1';
  
  onMount(async () => {
    try {
      // Fetch realm name from local Flask API
      const response = await fetch(`${API_BASE_URL}/realm_name`);
      if (response.ok) {
        const data = await response.json();
        if (data.name) {
          realmName = data.name;
        }
      } else {
        console.error('Error fetching realm name:', await response.text());
      }
    } catch (e) {
      console.error('Error fetching realm name:', e);
    }
  });
  
  async function handleSubmit() {
    error = '';
    
    if (!agreement) {
      error = 'Please indicate whether you agree to the terms';
      return;
    }
    
    if (agreement === 'disagree') {
      error = 'You must agree to the terms to join this Realm';
      return;
    }
    
    if (!$isAuthenticated) {
      error = 'You must be logged in to join this Realm. Please log in first and then return to this page.';
      return;
    }

    if (!selectedProfile) {
      error = 'Please select a profile type';
      return;
    }
    
    try {
      loading = true;
      // Call the Kybra canister join_realm method with the selected profile
      console.log(`Joining realm with profile: ${selectedProfile}`);
      const response = await backend.join_realm(selectedProfile);
      if (response.success) {
        success = true;
      } else if (response.data && response.data.Error) {
        error = response.data.Error;
      } else {
        error = 'Unknown error occurred';
      }
    } catch (e) {
      console.error('Error joining realm:', e);
      error = e.message || 'Failed to join the realm';
    } finally {
      loading = false;
    }
  }
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
  <div class="w-full max-w-md space-y-8">
    <div class="text-center">
      <h1 class="text-3xl font-extrabold text-gray-900">Join {realmName}</h1>
      <p class="mt-2 text-sm text-gray-600">
        Accept the terms to join this Realm
      </p>
    </div>
    
    {#if success}
      <Card class="p-8 text-center">
        <h2 class="text-xl font-bold text-green-600">Successfully Joined!</h2>
        <p class="mt-2">You have successfully joined the realm.</p>
        <Button href="/" class="mt-4" color="green">Go to Dashboard</Button>
      </Card>
    {:else}
      <Card class="p-8">
        <form class="space-y-6" on:submit|preventDefault={handleSubmit}>
          {#if error}
            <div class="rounded-md bg-red-50 p-4">
              <div class="text-sm text-red-700">{error}</div>
            </div>
          {/if}
          
          <div class="text-gray-700 mb-6">
            <p class="mb-4">
              By joining this Internet Computer Realm, you acknowledge and agree to the following:
            </p>
            
            <ul class="list-disc pl-5 space-y-2 mb-6">
              <li>Your interactions will be governed by smart contracts deployed on the Internet Computer Protocol</li>
              <li>You maintain ownership of your digital assets and identity</li>
              <li>Your participation in this realm is subject to the rules established by the decentralized governance</li>
              <li>All transactions within this realm are recorded on the Internet Computer blockchain</li>
            </ul>
            
            <p class="font-medium">Do you agree to these terms?</p>
          </div>
          
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-2">
              <Radio id="agreement-yes" name="agreement" value="agree" bind:group={agreement} />
              <Label for="agreement-yes">I agree to the terms</Label>
            </div>
            <div class="flex items-center gap-2">
              <Radio id="agreement-no" name="agreement" value="disagree" bind:group={agreement} />
              <Label for="agreement-no">I do not agree</Label>
            </div>
          </div>
          
          <div class="mb-4">
            <Label class="mb-2 block text-sm font-medium text-gray-700">Select Profile Type</Label>
            <Select bind:value={selectedProfile} on:change={(e) => selectedProfile = e.target.value}>
              {#each profiles as profile}
                <option value={profile.value}>{profile.name}</option>
              {/each}
            </Select>
          </div>
          
          <div class="mb-6">
            <div class="flex items-center gap-2 mb-4">
              <Checkbox bind:checked={includePassportVerification} />
              <Label class="text-sm font-medium text-gray-700">
                Verify passport identity (optional)
              </Label>
            </div>
            <p class="text-xs text-gray-500 mb-4">
              Use zero-knowledge proofs to verify your passport securely. Your passport data never leaves your device.
            </p>
            
            {#if includePassportVerification && $isAuthenticated}
              <div class="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <PassportVerification userId={$principal} />
              </div>
            {/if}
          </div>
          
          <div>
            {#if loading}
              <Button type="button" color="alternative" class="w-full flex justify-center items-center gap-2" disabled>
                <Spinner size="sm" color="blue" />
                Joining...
              </Button>
            {:else}
              <Button type="submit" color="alternative" class="w-full">Join Realm as {selectedProfile}</Button>
            {/if}
          </div>
          
          <div class="text-center text-sm">
            Already a member? 
            <a href="/login" class="font-medium text-primary-600 hover:text-primary-500">
              Log in
            </a>
          </div>
        </form>
      </Card>
    {/if}
  </div>
</div>
