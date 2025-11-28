<script>
  import { Button, Card, Radio, Label, Spinner, Select, Checkbox } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { principal, isAuthenticated } from '$lib/stores/auth';
  import { backend } from '$lib/canisters.js';
  import PassportVerification from '$lib/components/passport/PassportVerification.svelte';
  import { styles, cn } from '$lib/theme/utilities';
  import { _ } from 'svelte-i18n';
  
  let agreement = false;
  let showDemoBanner = true;
  let error = '';
  let success = false;
  let loading = false;
  let realmName = 'Realm';
  let selectedProfile = 'member'; // Default to member profile
  let includePassportVerification = false;
  let dropdownOpen = false;
  
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

<div class="min-h-screen bg-gray-50 px-4 py-12" style="transform: none !important;">
    <div class="w-full mx-auto space-y-8 md:w-[80%]">
      <div class="text-center">
        <h1 class="text-3xl font-extrabold text-gray-900">Join {realmName}</h1>
      </div>
      
      {#if success}
      <Card class="p-8 text-center !w-full !max-w-none">
        <h2 class={cn("text-xl font-bold", styles.text.success())}>Successfully Joined!</h2>
        <p class="mt-2 mb-4">You have successfully joined the realm.</p>
        <Button href="/" class={cn("mt-4 w-full", styles.button.primary())}>Go to Dashboard</Button>
      </Card>
      {:else}
      <Card class="p-8 !w-full !max-w-none">
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
          </div>
          
          <div class="flex items-center gap-2 mb-4">
            <Checkbox id="agreement" bind:checked={agreement} />
            <Label for="agreement" class="text-sm font-medium text-gray-700">
              I agree to these terms and conditions
            </Label>
          </div>
          
          <!-- Demo Feature: Profile Selection -->
          <div class="mb-4 relative">
            <div class="absolute -top-2 -right-2 z-10">
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                Demo Feature
              </span>
            </div>
            <div class="border border-blue-200 rounded-lg p-4 bg-blue-50/30">
              <label for="profile-dropdown" class="mb-2 block text-sm font-medium text-gray-700">Select Profile Type</label>
              <p class="text-xs text-blue-700 mb-3">In demo mode, you can select different profile types. In production, this would be determined by your organization role.</p>
              <div class="relative">
                <button
                  id="profile-dropdown"
                  type="button"
                  class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 text-left flex justify-between items-center"
                  on:click={() => dropdownOpen = !dropdownOpen}
                >
                  <span>{profiles.find(p => p.value === selectedProfile)?.name || 'Select...'}</span>
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                  </svg>
                </button>
                
                {#if dropdownOpen}
                  <div style="position: absolute; top: 100%; left: 0; margin-top: 4px; background: white; border: 1px solid #d1d5db; border-radius: 8px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); z-index: 50; width: 150px;">
                    {#each profiles as profile}
                      <div 
                        style="padding: 8px 12px; text-align: left; font-size: 14px; color: #111827; cursor: pointer; white-space: nowrap;"
                        class="hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
                        on:click={() => {
                          selectedProfile = profile.value;
                          dropdownOpen = false;
                        }}
                        on:keydown={(e) => e.key === 'Enter' && (() => {
                          selectedProfile = profile.value;
                          dropdownOpen = false;
                        })()}
                        role="button"
                        tabindex="0"
                      >
                        {profile.name}
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
          </div>

          <br />

          <div>
            {#if loading}
              <Button type="button" color="alternative" class="w-full flex justify-center items-center gap-2" disabled>
                <Spinner size="4" color="blue" />
                Joining...
              </Button>
            {:else}
              <Button type="submit" color="alternative" class="w-full">Join Realm</Button>
            {/if}
          </div>
        
        </form>
      </Card>
      {/if}
      </div>
</div>
