<script>
  import { Button, Card, Radio, Label, Spinner } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { principal, isAuthenticated } from '$lib/stores/auth';
  
  let agreement = '';
  let error = '';
  let success = false;
  let loading = false;
  let realmName = 'Smart Social Contracts Realm';
  
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
      error = 'You must be logged in to join this Realm';
      return;
    }
    
    try {
      loading = true;
      
      // Call local Flask API to join organization
      const response = await fetch(`${API_BASE_URL}/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: $principal
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          success = true;
        } else if (data.error) {
          error = data.error;
        } else {
          error = 'Unknown error occurred';
        }
      } else {
        const errorData = await response.json();
        error = errorData.error || 'Failed to join the realm';
      }
    } catch (e) {
      console.error('Error joining organization:', e);
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
        <p class="mt-2">You have successfully joined the Smart Social Contracts Realm.</p>
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
              <Radio name="agreement" value="agree" bind:group={agreement} />
              <Label>I agree to the terms</Label>
            </div>
            <div class="flex items-center gap-2">
              <Radio name="agreement" value="disagree" bind:group={agreement} />
              <Label>I do not agree</Label>
            </div>
          </div>
          
          <div>
            {#if loading}
              <Button type="button" color="alternative" class="w-full flex justify-center items-center gap-2" disabled>
                <Spinner size="sm" color="blue" />
                Joining...
              </Button>
            {:else}
              <Button type="submit" color="alternative" class="w-full">Join Realm</Button>
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
