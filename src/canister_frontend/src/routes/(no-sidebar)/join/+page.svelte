<script>
  import { Button, Card, Radio, Label, Spinner } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { principal, isAuthenticated } from '$lib/stores/auth';
  import { Actor, HttpAgent } from '@dfinity/agent';
  import { initializeAuthClient } from '$lib/auth';
  
  let agreement = '';
  let error = '';
  let success = false;
  let loading = false;
  let realmName = 'Smart Social Contracts Realm';
  
  // Get the canister ID from environment or use a default for local development
  // In production, this would come from your canister_ids.json
  const canisterId = 'bkyz2-fmaaa-aaaaa-qaaaq-cai'; // Using the greeter canister from memory
  
  // Simplified interface for canister methods we need
  const canisterInterface = {
    get_realm_name_endpoint: () => ({}),
    user_join_organization_endpoint: (principal) => ({ principal })
  };
  
  onMount(async () => {
    try {
      // Create anonymous actor to get realm name
      const authClient = await initializeAuthClient();
      const identity = authClient.getIdentity();
      
      // Use agent to talk to local replica by default
      const agent = new HttpAgent({ 
        host: 'http://localhost:8000',
        identity
      });
      
      // For local development we need to do this, would be removed in production
      if (process.env.NODE_ENV !== 'production') {
        await agent.fetchRootKey();
      }
      
      // Create actor to interact with canister
      const actor = Actor.createActor(() => {}, {
        agent,
        canisterId,
      });
      
      // Call get_realm_name_endpoint in IC format
      try {
        const result = await actor.get_realm_name_endpoint();
        if (result && typeof result === 'string') {
          try {
            const parsed = JSON.parse(result);
            if (parsed.name) {
              realmName = parsed.name;
            }
          } catch (e) {
            console.error('Error parsing realm name result:', e);
          }
        }
      } catch (e) {
        console.error('Error fetching realm name:', e);
      }
    } catch (e) {
      console.error('Error setting up canister connection:', e);
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
      
      // Get auth client to access identity
      const authClient = await initializeAuthClient();
      const identity = authClient.getIdentity();
      
      // Create an authenticated agent
      const agent = new HttpAgent({ 
        host: 'http://localhost:8000',
        identity 
      });
      
      // For local development we need to do this, would be removed in production
      if (process.env.NODE_ENV !== 'production') {
        await agent.fetchRootKey();
      }
      
      // Create actor to interact with canister
      const actor = Actor.createActor(() => {}, {
        agent,
        canisterId,
      });
      
      // Call the user_join_organization_endpoint with proper format for IC
      // In Candid for text arguments you use ("Hello") format, not escaped quotes
      const result = await actor.user_join_organization_endpoint($principal);
      
      if (result && typeof result === 'string') {
        try {
          const parsed = JSON.parse(result);
          if (parsed.success) {
            success = true;
          } else if (parsed.error) {
            error = parsed.error;
          } else {
            error = 'Unknown error occurred';
          }
        } catch (e) {
          console.error('Error parsing join result:', e);
          error = 'Failed to parse response from canister';
        }
      } else {
        error = 'Unexpected response from canister';
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
              <Button type="button" color="primary" class="w-full flex justify-center items-center gap-2" disabled>
                <Spinner size="sm" color="white" />
                Joining...
              </Button>
            {:else}
              <Button type="submit" color="primary" class="w-full">Join Realm</Button>
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
