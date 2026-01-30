<script>
  import { Button, Spinner } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { principal, isAuthenticated } from '$lib/stores/auth';
  import { login, initializeAuthClient } from '$lib/auth';
  import { CONFIG } from '$lib/config.js';
  import { backend, initBackendWithIdentity } from '$lib/canisters.js';
  import { loadUserProfiles, hasJoined, profilesLoading } from '$lib/stores/profiles';
  import { realmInfo, realmLogo, realmName as realmNameStore, realmWelcomeImage, realmWelcomeMessage, realmDescription } from '$lib/stores/realmInfo';
  import { cn } from '$lib/theme/utilities';
  import { _ } from 'svelte-i18n';
  
  // Step management: 'auth' | 'already_joined' | 'terms' | 'profile' | 'success'
  let currentStep = 'auth';
  let userHasJoined = false;
  let agreement = false;
  let error = '';
  let loading = false;
  let realmName = 'Realm';
  let selectedProfile = ''; // No default - user must choose
  
  // Available profiles with icon names (rendered as SVGs)
  const profiles = [
    { 
      value: 'member', 
      name: 'Member',
      iconType: 'user',
      description: 'Participate in governance, access community features'
    },
    { 
      value: 'admin', 
      name: 'Administrator',
      iconType: 'cog',
      description: 'Full access to manage realm settings and users'
    },
  ];

  // Default fallback image if realm has no welcome image configured
  const defaultWelcomeImage = '/images/default_welcome.png';
  
  // Reactive welcome image - use realm's image or fallback
  $: welcomeImageUrl = $realmWelcomeImage || defaultWelcomeImage;
  
  // Determine initial step based on auth status and join status
  $: {
    console.log('[JOIN PAGE v3] Reactive check:', { isAuthenticated: $isAuthenticated, currentStep, profilesLoading: $profilesLoading });
    if ($isAuthenticated && !$profilesLoading) {
      userHasJoined = hasJoined();
      console.log('[JOIN PAGE v3] hasJoined result:', userHasJoined);
      // Redirect to already_joined if user has joined and is on auth or terms step
      if (userHasJoined && (currentStep === 'auth' || currentStep === 'terms')) {
        currentStep = 'already_joined';
      } else if (!userHasJoined && currentStep === 'auth') {
        currentStep = 'terms';
      }
    }
  }
  
  onMount(async () => {
    console.log('[JOIN PAGE v2] onMount - isAuthenticated:', $isAuthenticated);
    // Fetch realm info
    await realmInfo.fetch();
    if ($realmNameStore) {
      realmName = $realmNameStore;
    }
    
    // If user is already authenticated, load their profiles to check join status
    if ($isAuthenticated) {
      console.log('[JOIN PAGE v2] Loading profiles for authenticated user...');
      await initBackendWithIdentity();
      await loadUserProfiles();
      console.log('[JOIN PAGE v2] Profiles loaded, hasJoined:', hasJoined());
    }
  });

  async function handleLogin() {
    loading = true;
    error = '';
    try {
      const { principal: userPrincipal } = await login();
      if (userPrincipal) {
        isAuthenticated.set(true);
        principal.set(userPrincipal.toText());
        await initBackendWithIdentity();
        await loadUserProfiles();
        // Check if user has already joined
        userHasJoined = hasJoined();
        currentStep = userHasJoined ? 'already_joined' : 'terms';
      } else {
        error = 'Login was cancelled or failed. Please try again.';
      }
    } catch (e) {
      console.error('Login error:', e);
      error = 'Failed to authenticate. Please try again.';
    } finally {
      loading = false;
    }
  }

  function handleTermsAccept() {
    if (!agreement) {
      error = 'Please accept the terms to continue';
      return;
    }
    error = '';
    currentStep = 'profile';
  }

  function handleBack() {
    error = '';
    if (currentStep === 'profile') {
      currentStep = 'terms';
    }
  }
  
  async function handleJoin() {
    error = '';
    
    if (!selectedProfile) {
      error = 'Please select a profile type';
      return;
    }
    
    try {
      loading = true;
      console.log(`Joining realm with profile: ${selectedProfile}`);
      const response = await backend.join_realm(selectedProfile);
      if (response.success) {
        currentStep = 'success';
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

<div class="h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex" style="transform: none !important;">
  <!-- Left Brand Panel with Background Image -->
  <div class="hidden lg:flex lg:w-[50%] text-white flex-col justify-between relative overflow-hidden">
    <!-- Background Image - no overlay, full opacity -->
    <div class="absolute inset-0 z-0">
      <img 
        src={welcomeImageUrl} 
        alt="{realmName} background"
        class="w-full h-full object-cover"
      />
    </div>
    
    <!-- Content overlay - centered vertically -->
    <div class="relative z-10 p-6 flex flex-col h-full justify-center items-center">
      <!-- Text container with dark background for readability -->
      <div class="bg-black/60 backdrop-blur-sm rounded-2xl p-6 max-w-md mx-6">
        <!-- Welcome Message -->
        <h1 class="text-4xl font-bold mb-4 leading-tight">
          Welcome to {realmName}
        </h1>
        
        {#if $realmWelcomeMessage}
          <p class="text-lg text-white/90 mb-4">
            {$realmWelcomeMessage}
          </p>
        {/if}
        
        {#if $realmDescription}
          <p class="text-lg text-white/90">
            {$realmDescription}
          </p>
        {/if}
      </div>
    </div>
  </div>

  <!-- Right Form Panel -->
  <div class="flex-1 flex items-center justify-center p-6 lg:p-12 relative">
    <!-- Mobile background image -->
    <div class="lg:hidden absolute inset-0 z-0">
      <img 
        src={welcomeImageUrl} 
        alt="{realmName} background"
        class="w-full h-full object-cover"
      />
      <div class="absolute inset-0 bg-white/80 backdrop-blur-sm"></div>
    </div>
    
    <div class="w-full max-w-md relative z-10">

      <!-- Step Indicator -->
      {#if currentStep !== 'success'}
        <div class="flex items-center justify-center gap-2 mb-8">
          <div class="flex items-center gap-2">
            <div class={cn(
              "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all",
              currentStep === 'auth' ? "bg-gray-900 text-white" : "bg-gray-700 text-white"
            )}>
              {currentStep === 'auth' ? '1' : '✓'}
            </div>
            <span class="text-sm text-gray-600 hidden sm:inline">Sign In</span>
          </div>
          <div class="w-8 h-px bg-gray-300"></div>
          <div class="flex items-center gap-2">
            <div class={cn(
              "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all",
              currentStep === 'terms' ? "bg-gray-900 text-white" : 
              currentStep === 'profile' || currentStep === 'success' ? "bg-gray-700 text-white" : 
              "bg-gray-200 text-gray-500"
            )}>
              {currentStep === 'profile' || currentStep === 'success' ? '✓' : '2'}
            </div>
            <span class="text-sm text-gray-600 hidden sm:inline">Terms</span>
          </div>
          <div class="w-8 h-px bg-gray-300"></div>
          <div class="flex items-center gap-2">
            <div class={cn(
              "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all",
              currentStep === 'profile' ? "bg-gray-900 text-white" : 
              currentStep === 'success' ? "bg-gray-700 text-white" : 
              "bg-gray-200 text-gray-500"
            )}>
              3
            </div>
            <span class="text-sm text-gray-600 hidden sm:inline">Profile</span>
          </div>
        </div>
      {/if}

      <!-- Error Display -->
      {#if error}
        <div class="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      {/if}

      <!-- Step: Auth -->
      {#if currentStep === 'auth'}
        <div class="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <div class="text-center mb-8">
            <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">Sign in to continue</h2>
            <p class="text-gray-500">
              Authenticate with Internet Identity to join {realmName}
            </p>
          </div>
          
          <button
            on:click={handleLogin}
            disabled={loading}
            class="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {#if loading}
              <Spinner size="5" color="white" />
              <span>Connecting...</span>
            {:else}
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
              </svg>
              <span>Sign in with Internet Identity</span>
            {/if}
          </button>
          
          <p class="mt-6 text-center text-sm text-gray-500">
            Don't have an Internet Identity? 
            <a href={CONFIG.internet_identity_url} target="_blank" rel="noopener noreferrer" class="text-gray-700 hover:text-gray-900 hover:underline font-medium">
              Create one →
            </a>
          </p>
        </div>

      <!-- Step: Already Joined (Welcome Back) -->
      {:else if currentStep === 'already_joined'}
        <div class="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <div class="text-center mb-8">
            <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">Welcome back!</h2>
            <p class="text-gray-500">
              You're already a member of {realmName}
            </p>
          </div>
          
          <a
            href="/"
            class="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-3"
          >
            <span>Go to Dashboard</span>
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </a>
        </div>

      <!-- Step: Terms -->
      {:else if currentStep === 'terms'}
        <div class="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <h2 class="text-2xl font-bold text-gray-900 mb-2">Terms & Conditions</h2>
          <p class="text-gray-500 mb-6">Please review and accept to continue</p>
          
          <div class="space-y-4 mb-6">
            <div class="flex gap-3 p-3 bg-gray-50 rounded-lg items-start">
              <svg class="w-5 h-5 text-gray-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p class="text-sm text-gray-700">Your interactions will be governed by smart contracts deployed on the Internet Computer Protocol</p>
            </div>
            <div class="flex gap-3 p-3 bg-gray-50 rounded-lg items-start">
              <svg class="w-5 h-5 text-gray-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <p class="text-sm text-gray-700">You maintain ownership of your digital assets and identity</p>
            </div>
            <div class="flex gap-3 p-3 bg-gray-50 rounded-lg items-start">
              <svg class="w-5 h-5 text-gray-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
              </svg>
              <p class="text-sm text-gray-700">Your participation is subject to the rules established by decentralized governance</p>
            </div>
            <div class="flex gap-3 p-3 bg-gray-50 rounded-lg items-start">
              <svg class="w-5 h-5 text-gray-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <p class="text-sm text-gray-700">All transactions are recorded on the Internet Computer blockchain</p>
            </div>
          </div>
          
          <label class="flex items-center gap-3 p-4 border border-gray-200 rounded-xl cursor-pointer hover:bg-gray-50 transition-colors mb-6">
            <input 
              type="checkbox" 
              bind:checked={agreement}
              class="w-5 h-5 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
            />
            <span class="text-sm font-medium text-gray-700">I agree to these terms and conditions</span>
          </label>
          
          <button
            on:click={handleTermsAccept}
            disabled={!agreement}
            class="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continue
          </button>
        </div>

      <!-- Step: Profile Selection -->
      {:else if currentStep === 'profile'}
        <div class="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-2xl font-bold text-gray-900">Select Profile</h2>
            <span class="px-3 py-1 bg-gray-200 text-gray-600 text-xs font-medium rounded-full">Demo</span>
          </div>
          <p class="text-gray-500 mb-6">Choose how you want to participate</p>
          
          <div class="space-y-3 mb-6">
            {#each profiles as profile}
              <button
                type="button"
                on:click={() => selectedProfile = profile.value}
                class={cn(
                  "w-full p-4 rounded-xl border-2 text-left transition-all",
                  selectedProfile === profile.value 
                    ? "border-gray-900 bg-gray-50" 
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                )}
              >
                <div class="flex items-center gap-4">
                  <div class={cn(
                    "w-12 h-12 rounded-full flex items-center justify-center",
                    selectedProfile === profile.value ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"
                  )}>
                    {#if selectedProfile === profile.value}
                      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                    {:else if profile.iconType === 'user'}
                      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    {:else if profile.iconType === 'cog'}
                      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    {/if}
                  </div>
                  <div class="flex-1">
                    <div class="font-semibold text-gray-900">{profile.name}</div>
                    <div class="text-sm text-gray-500">{profile.description}</div>
                  </div>
                </div>
              </button>
            {/each}
          </div>
          
          <p class="text-xs text-gray-500 mb-6 p-3 bg-gray-100 rounded-lg flex items-start gap-2">
            <svg class="w-4 h-4 text-gray-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>In demo mode, you can select any profile. In production, this would be determined by your organization role.</span>
          </p>
          
          <div class="flex gap-3">
            <button
              on:click={handleBack}
              class="flex-1 py-4 px-6 border border-gray-300 text-gray-700 font-medium rounded-xl hover:bg-gray-50 transition-all"
            >
              Back
            </button>
            <button
              on:click={handleJoin}
              disabled={!selectedProfile || loading}
              class="flex-1 py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {#if loading}
                <Spinner size="5" color="white" />
                <span>Joining...</span>
              {:else}
                <span>Join Realm</span>
              {/if}
            </button>
          </div>
        </div>

      <!-- Step: Success -->
      {:else if currentStep === 'success'}
        <div class="bg-white rounded-2xl shadow-xl p-8 border border-gray-100 text-center">
          <div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
          </div>
          
          <h2 class="text-2xl font-bold text-gray-900 mb-2">Welcome to {realmName}!</h2>
          <p class="text-gray-500 mb-8">
            You've successfully joined the realm. Start exploring your new community.
          </p>
          
          <a
            href="/"
            class="inline-flex items-center justify-center w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all gap-2"
          >
            <span>Go to Dashboard</span>
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
            </svg>
          </a>
        </div>
      {/if}
    </div>
    
    <!-- Powered by footer -->
    <div class="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 z-20">
      <span class="text-gray-400 text-sm">Powered by</span>
      <a href="https://realmsgos.org" target="_blank" rel="noopener noreferrer">
        <img src="/images/logo_horizontal.svg" alt="Realms" class="h-5 opacity-60 hover:opacity-100 transition-opacity" />
      </a>
    </div>
  </div>
</div>
