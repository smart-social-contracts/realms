<script>
  import { Button, Spinner } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { principal, isAuthenticated } from '$lib/stores/auth';
  import { login, logout, initializeAuthClient } from '$lib/auth';
  import { backend, backendReady, initBackendWithIdentity, setActiveQuarter } from '$lib/canisters.js';
  import { loadUserProfiles, hasJoined, profilesLoading } from '$lib/stores/profiles';
  import { activeQuarterId } from '$lib/stores/quarters';
  import { realmInfo, realmName as realmNameStore, realmWelcomeMessage, realmDescription, realmOpenRegistration, testMode, testModeIIBypass, testModeUserSelfRegistration, testModeSkipTerms } from '$lib/stores/realmInfo';
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
  let inviteCode = '';
  let inviteProfile = '';
  let inviteValid = false;
  let inviteError = '';
  let inviteChecking = false;
  
  // Available profiles with icon names (rendered as SVGs)
  const allProfiles = [
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
    { 
      value: 'developer', 
      name: 'Developer',
      iconType: 'code',
      description: 'System tools, extension development, and debugging'
    },
  ];

  // In test mode (II bypass or self-registration), show all profiles. Otherwise only member
  // is available unless an invite code grants a specific profile.
  $: profiles = inviteValid && inviteProfile
    ? allProfiles.filter(p => p.value === inviteProfile)
    : ($testModeUserSelfRegistration || $testModeIIBypass)
      ? allProfiles
      : allProfiles.filter(p => p.value === 'member');

  $: if (profiles.length === 1 && !selectedProfile) {
    selectedProfile = profiles[0].value;
  }

  // Invite is required when registration is closed (not open) and user has no valid invite
  $: inviteRequired = !$realmOpenRegistration && !inviteValid && !$testModeUserSelfRegistration && !$testModeIIBypass;

  $: welcomeImageUrl = $realmInfo.backgroundImageUrl || '/custom/background.png';
  
  // Determine initial step based on auth status and join status
  $: {
    console.log('[JOIN PAGE v3] Reactive check:', { isAuthenticated: $isAuthenticated, currentStep, profilesLoading: $profilesLoading });
    if ($isAuthenticated && !$profilesLoading) {
      userHasJoined = hasJoined();
      console.log('[JOIN PAGE v3] hasJoined result:', userHasJoined);
      if ($testModeIIBypass) {
        // In II bypass test mode, always allow profile selection regardless of join status
        if (currentStep === 'auth') {
          currentStep = 'profile';
        }
      } else if (userHasJoined && (currentStep === 'auth' || currentStep === 'terms')) {
        currentStep = 'already_joined';
      } else if (!userHasJoined && currentStep === 'auth') {
        currentStep = $testModeSkipTerms ? 'profile' : 'terms';
      }
    }
  }
  
  onMount(async () => {
    console.log('[JOIN PAGE v2] onMount - isAuthenticated:', $isAuthenticated);

    // Wait for the backend actor to be ready, then fetch realm info
    // so test flags and realm name are available before rendering decisions.
    await backendReady;
    await realmInfo.fetch();
    if ($realmNameStore) {
      realmName = $realmNameStore;
    }

    if ($testModeIIBypass) {
      console.log('[JOIN PAGE] [TEST MODE] Resetting auth state for identity selection');
      await logout();
      isAuthenticated.set(false);
      principal.set('');
      currentStep = 'auth';
    }

    // Read invite code from URL params
    const urlParams = new URLSearchParams(window.location.search);
    inviteCode = urlParams.get('invite') || urlParams.get('code') || '';

    // If user is already authenticated (non-test mode), load their profiles to check join status
    if ($isAuthenticated) {
      console.log('[JOIN PAGE v2] Loading profiles for authenticated user...');
      await initBackendWithIdentity();
      await loadUserProfiles();
      if (inviteCode) {
        await validateInvite();
      }
      console.log('[JOIN PAGE v2] Profiles loaded, hasJoined:', hasJoined());
    }
  });

  async function handleLogin(options = {}) {
    loading = true;
    error = '';
    try {
      const { principal: userPrincipal } = await login(options);
      if (userPrincipal) {
        isAuthenticated.set(true);
        principal.set(userPrincipal.toText());
        await initBackendWithIdentity();
        await loadUserProfiles();
        if (inviteCode) {
          await validateInvite();
        }
        // Check if user has already joined
        userHasJoined = hasJoined();
        if ($testModeIIBypass) {
          // In II bypass test mode, always go to profile selection
          currentStep = 'profile';
        } else {
          currentStep = userHasJoined ? 'already_joined' : ($testModeSkipTerms ? 'profile' : 'terms');
        }
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

  async function sha256Hex(plaintext) {
    const data = new TextEncoder().encode(plaintext);
    const buf = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async function validateInvite() {
    if (!inviteCode) return;
    inviteChecking = true;
    inviteError = '';
    error = '';
    try {
      // Test mode shortcuts: "admin" / "member" / "dev" accepted client-side
      const trimmed = inviteCode.trim().toLowerCase();
      if (($testModeUserSelfRegistration || $testModeIIBypass) && (trimmed === 'admin' || trimmed === 'member' || trimmed === 'dev' || trimmed === 'developer')) {
        const profile = trimmed === 'dev' || trimmed === 'developer' ? 'developer' : trimmed;
        inviteValid = true;
        inviteProfile = profile;
        selectedProfile = profile;
        return;
      }

      const result = await backend.extension_call(
        'census',
        'validate_registration_code',
        JSON.stringify({ code: inviteCode })
      );
      const parsed = typeof result.response === 'string' ? JSON.parse(result.response) : result.response;
      if (parsed.success && parsed.data) {
        inviteValid = true;
        inviteProfile = parsed.data.profile || 'member';
        selectedProfile = inviteProfile;
      } else {
        inviteError = parsed.error || 'Invalid invitation code';
        inviteValid = false;
      }
    } catch (e) {
      console.error('Invite validation error:', e);
      inviteError = 'Could not validate invitation code';
      inviteValid = false;
    } finally {
      inviteChecking = false;
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
  
  async function resolveInviteChecksum() {
    if (inviteCode) return sha256Hex(inviteCode);
    // Test mode shortcuts: backend accepts sha256("admin") / sha256("member") as invite codes
    if (($testModeUserSelfRegistration || $testModeIIBypass) && selectedProfile === 'admin') {
      return sha256Hex('admin');
    }
    if (($testModeUserSelfRegistration || $testModeIIBypass) && selectedProfile === 'member') {
      return sha256Hex('member');
    }
    return '';
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
      // Step 1: Register on the capital (current backend) — gets quarter assignment
      const inviteChecksum = await resolveInviteChecksum();
      const response = await backend.join_realm(selectedProfile, '', inviteChecksum);
      if (response.success) {
        // Step 2: If assigned to a quarter, switch to it and register there too
        const assignedQuarter = response.data?.userGet?.assigned_quarter;
        if (assignedQuarter) {
          console.log(`Assigned to quarter: ${assignedQuarter}, switching...`);
          activeQuarterId.set(assignedQuarter);
          await setActiveQuarter(assignedQuarter);

          // Register on the assigned quarter backend
          try {
            await backend.join_realm(selectedProfile, '', inviteChecksum);
            console.log('Registered on assigned quarter');
          } catch (qErr) {
            console.warn('Quarter registration deferred:', qErr);
          }

          // Cache in localStorage for instant reconnect
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem('home_quarter', assignedQuarter);
          }
        }
        currentStep = 'success';
      } else if (response.data && response.data.error) {
        error = response.data.error;
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

<div class="min-h-screen md:h-screen grid grid-cols-1 md:grid-cols-2" style="transform: none !important;">
  <!-- Left Brand Panel with Background Image -->
  <div class="hidden md:flex md:col-start-1 text-white flex-col justify-between relative">
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
  <div class="flex items-start md:items-center justify-center p-4 pb-16 md:p-12 relative bg-gradient-to-br from-gray-50 to-gray-100 md:col-start-2 overflow-y-auto">
    <!-- Mobile background image -->
    <div class="md:hidden absolute inset-0 z-0">
      <img 
        src={welcomeImageUrl} 
        alt="{realmName} background"
        class="w-full h-full object-cover"
      />
    </div>
    
    <div class="w-full max-w-md relative z-10 md:bg-transparent md:backdrop-blur-none md:rounded-none md:p-0 bg-white/80 backdrop-blur-sm rounded-2xl p-3 my-auto">

      <!-- Step Indicator -->
      {#if currentStep !== 'success'}
        <div class="flex items-center justify-center gap-2 mb-4 md:mb-8">
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

      {#if inviteChecking}
        <div class="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl text-blue-700 text-sm flex items-center gap-2">
          <Spinner size="4" color="blue" />
          <span>Validating invitation code...</span>
        </div>
      {/if}

      <!-- Step: Auth -->
      {#if currentStep === 'auth'}
        <div class="bg-white rounded-2xl shadow-xl p-5 md:p-8 border border-gray-100">
          <div class="text-center mb-8">
            <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">Sign in to continue</h2>
            <p class="text-gray-500">
              {$testModeIIBypass ? 'Choose how to sign in to' : 'Authenticate with Internet Identity to join'} {realmName}
            </p>
          </div>

          {#if $testModeIIBypass}
            <div class="space-y-3">
              <button
                on:click={() => handleLogin()}
                disabled={loading}
                class="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {#if loading}
                  <Spinner size="5" color="white" />
                  <span>Connecting...</span>
                {:else}
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>Sign in as Default Test User</span>
                {/if}
              </button>
              <button
                on:click={() => handleLogin({ random: true })}
                disabled={loading}
                class="w-full py-4 px-6 bg-white hover:bg-gray-50 text-gray-900 font-medium rounded-xl border-2 border-gray-200 transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {#if loading}
                  <Spinner size="5" color="gray" />
                  <span>Creating identity...</span>
                {:else}
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  <span>Create New Test Identity</span>
                {/if}
              </button>
              <p class="text-center text-xs text-gray-400 mt-2">
                Test mode: Internet Identity is bypassed. Each new identity gets a unique principal.
              </p>
            </div>
          {:else}
            <button
              on:click={() => handleLogin()}
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
              <a href={globalThis.__CANISTER_IDS?.internet_identity || 'https://identity.ic0.app'} target="_blank" rel="noopener noreferrer" class="text-gray-700 hover:text-gray-900 hover:underline font-medium">
                Create one →
              </a>
            </p>
          {/if}
        </div>

      <!-- Step: Already Joined (Welcome Back) -->
      {:else if currentStep === 'already_joined'}
        <div class="bg-white rounded-2xl shadow-xl p-5 md:p-8 border border-gray-100">
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
        <div class="bg-white rounded-2xl shadow-xl p-5 md:p-8 border border-gray-100">
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
        {#if inviteRequired}
          <div class="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm flex items-start gap-2">
            <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Registration requires an invitation code.</span>
          </div>
        {/if}
        <div class="bg-white rounded-2xl shadow-xl p-5 md:p-8 border border-gray-100">
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-2xl font-bold text-gray-900">Select Profile</h2>
{#if inviteValid}
              <span class="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">Invited as {inviteProfile}</span>
            {:else if $testMode}
              <span class="px-3 py-1 bg-gray-200 text-gray-600 text-xs font-medium rounded-full">Test Mode</span>
            {/if}
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
                    {:else if profile.iconType === 'code'}
                      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
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

          <!-- Invite code input -->
          <div class="mb-6 p-3 md:p-4 border border-gray-200 rounded-xl">
            <label for="invite-code" class="block text-sm font-medium text-gray-700 mb-2">
              {#if inviteValid}
                Invitation code
              {:else if $realmOpenRegistration || $testMode}
                Have an invitation code?
              {:else}
                Invitation code <span class="text-red-500">*</span>
              {/if}
            </label>
            <div class="flex gap-2">
              <input
                id="invite-code"
                type="text"
                bind:value={inviteCode}
                on:keydown={(e) => { if (e.key === 'Enter' && inviteCode && !inviteChecking) validateInvite(); }}
                placeholder="Paste your invite code"
                disabled={inviteValid}
                class={cn(
                  "min-w-0 flex-1 px-3 py-2 border rounded-lg text-sm focus:ring-gray-900 focus:border-gray-900",
                  inviteValid ? "border-green-300 bg-green-50 text-green-800" : "border-gray-300"
                )}
              />
              {#if inviteValid}
                <button
                  on:click={() => { inviteCode = ''; inviteValid = false; inviteProfile = ''; inviteError = ''; selectedProfile = ''; }}
                  class="shrink-0 px-3 md:px-4 py-2 text-sm font-medium border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Clear
                </button>
              {:else}
                <button
                  on:click={validateInvite}
                  disabled={!inviteCode || inviteChecking}
                  class="shrink-0 px-3 md:px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {#if inviteChecking}
                    <Spinner size="4" color="white" />
                  {:else}
                    Validate
                  {/if}
                </button>
              {/if}
            </div>
            {#if inviteValid}
              <p class="mt-2 text-sm text-green-600 flex items-center gap-1">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                Valid — grants <strong class="ml-1">{inviteProfile}</strong> access
              </p>
            {/if}
            {#if inviteError && !inviteChecking && !inviteValid}
              <p class="mt-2 text-sm text-red-600">{inviteError}</p>
            {/if}
            {#if ($testModeUserSelfRegistration || $testModeIIBypass) && !inviteValid}
              <p class="mt-2 text-xs text-gray-400 flex items-start gap-1.5">
                <svg class="w-3.5 h-3.5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>
                  Test mode: enter <strong>"member"</strong>, <strong>"admin"</strong>, or <strong>"dev"</strong> to register with that profile.
                </span>
              </p>
            {/if}
          </div>
          
{#if $testMode}
          <p class="text-xs text-gray-500 mb-6 p-3 bg-gray-100 rounded-lg flex items-start gap-2">
            <svg class="w-4 h-4 text-gray-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>In test mode, you can select any profile. In production, this would be determined by your organization role.</span>
          </p>
{/if}
          
          <div class="flex gap-3">
            <button
              on:click={handleBack}
              class="flex-1 py-3 md:py-4 px-4 md:px-6 border border-gray-300 text-gray-700 font-medium rounded-xl hover:bg-gray-50 transition-all"
            >
              Back
            </button>
            <button
              on:click={handleJoin}
              disabled={!selectedProfile || loading || inviteRequired}
              class="flex-1 py-3 md:py-4 px-4 md:px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
        <div class="bg-white rounded-2xl shadow-xl p-5 md:p-8 border border-gray-100 text-center">
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
            href="/extensions/member_dashboard"
            class="inline-flex items-center justify-center w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all gap-2"
          >
            <span>Go to Member Dashboard</span>
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
            </svg>
          </a>
        </div>
      {/if}
    </div>
    
    <!-- Powered by footer -->
    <div class="hidden md:flex absolute bottom-6 left-1/2 -translate-x-1/2 items-center gap-2 z-20">
      <span class="text-gray-400 text-sm">Powered by</span>
      <a href="https://realmsgos.org" target="_blank" rel="noopener noreferrer">
        <img src="/images/logo_horizontal.svg" alt="Realms" class="h-5 opacity-60 hover:opacity-100 transition-opacity" />
      </a>
    </div>
  </div>
</div>
