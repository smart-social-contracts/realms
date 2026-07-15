<script>
  import { Button, Spinner } from 'flowbite-svelte';
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { principal, isAuthenticated } from '$lib/stores/auth';
  import { login, logout, restoreAuthSession, resetAuthSessionRestore } from '$lib/auth';
  import { isEmbeddedInPortal } from '$lib/portal-bridge.ts';
  import { backend, backendReady, initBackendWithIdentity, setActiveQuarter, createQuarterActor } from '$lib/canisters.js';
  import { loadUserProfiles, profilesLoading } from '$lib/stores/profiles';
  import { activeQuarterId } from '$lib/stores/quarters';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { realmInfo, realmName as realmNameStore, realmWelcomeMessage, realmManifesto, realmOpenRegistration, testMode, testModeIIBypass, testModeUserSelfRegistration, testModeSkipTerms } from '$lib/stores/realmInfo';
  import { cn } from '$lib/theme/utilities';
  import { formatQuarterLabel } from '$lib/utils/quarterLabels';
  import { probeFederatedMembership, activateMembership } from '$lib/utils/federatedMembership';
  import { listTestIdentities, shortPrincipal } from '$lib/test-identities.js';
  import { _ } from 'svelte-i18n';
  
  // Step management: 'auth' | 'already_joined' | 'terms' | 'profile' | 'success'
  let currentStep = 'auth';
  let userHasJoined = false;
  let membershipProbed = false;
  /** @type {Promise<void> | null} */
  let membershipProbePromise = null;
  /** @type {import('$lib/utils/federatedMembership').MembershipHit[]} */
  let membershipHits = [];
  let probeCapitalId = '';
  let selectedActivationId = '';
  let agreement = false;
  let error = '';
  let loading = false;
  let realmName = 'Realm';
  let inviteCode = '';
  let inviteProfile = '';
  let inviteValid = false;
  let inviteError = '';
  let inviteChecking = false;

  // Quarter targeting (issue #156): a new member joins exactly ONE quarter.
  // Target comes from invite (?quarter=) or system assignment via
  // get_join_targets().default_quarter (least-populated joinable). No free picker.
  let capitalId = '';
  let joinMode = 'auto';        // 'auto' | 'choice' (choice must not enable a free picker)
  let quarterDirectory = [];    // all quarters from get_join_targets (for lookups)
  let selectedQuarter = '';     // canister id assigned / invite override
  let targetQuarterId = '';     // resolved join target
  let targetActor = null;       // actor for the target quarter (or capital backend)
  let targetsResolved = false;
  let forgotLoading = false;
  let embeddedInPortal = false;
  let forgotError = '';
  /** @type {ReturnType<typeof listTestIdentities>} */
  let testIdentities = listTestIdentities();
  let selectedTestIdentityIndex = 0;
  // The granted profile is resolved by the backend (issue #242): the invite
  // code's profile when a code is used, otherwise the codex-defined default.
  // There is no profile picker — user types are gone; only profiles exist.

  // Invite is required when registration is closed (not open) and user has no valid invite.
  // II bypass replaces Internet Identity only — incumbent realms still need a registration code.
  $: inviteRequired = !$realmOpenRegistration && !inviteValid && !$testModeUserSelfRegistration;

  $: targetQuarterInfo = quarterDirectory.find((q) => q.canister_id === targetQuarterId) || null;
  // Assignment banner when federation has multiple quarters or target is a sub-quarter.
  $: showQuarterBanner = !!targetQuarterId && (
    quarterDirectory.length > 1 ||
    (!!capitalId && targetQuarterId !== capitalId)
  );

  $: welcomeImageUrl = $realmInfo.backgroundImageUrl || '/custom/background.png';

  const internetIdentityUrl =
    (typeof globalThis !== 'undefined' && globalThis.__CANISTER_IDS?.internet_identity) ||
    'https://identity.ic0.app';

  function openInternetIdentity() {
    window.open(internetIdentityUrl, '_blank', 'noopener,noreferrer');
  }

  // ── Linear step model for the progress indicator (issue #156) ──────────────
  // Order: Sign In → Terms → Profile → Welcome. System assigns the quarter;
  // there is no free pick_quarter step on the open-registration path.
  $: steps = [
    { id: 'auth', label: 'Sign In' },
    ...($testModeSkipTerms ? [] : [{ id: 'terms', label: 'Terms' }]),
    { id: 'profile', label: 'Invitation' },
    { id: 'success', label: 'Welcome' },
  ];
  $: currentStepIndex = steps.findIndex((s) => s.id === currentStep);

  // The nearest earlier step the user is allowed to return to. Sign In is never
  // a back target once authenticated (you cannot un-authenticate by clicking,
  // and the reactive guard would bounce forward anyway), so we skip it. Null
  // means there is nowhere to go back to from the current step.
  $: prevStepId = (() => {
    for (let i = currentStepIndex - 1; i >= 0; i--) {
      const s = steps[i];
      if (s.id === 'auth' && $isAuthenticated) continue;
      return s.id;
    }
    return null;
  })();

  // Backward-only navigation from the stepper: a user may revisit any earlier
  // step, except Sign In once authenticated, and never while a join is in flight.
  function goToStep(stepId) {
    const idx = steps.findIndex((s) => s.id === stepId);
    if (idx < 0 || idx >= currentStepIndex) return;
    if (stepId === 'auth' && $isAuthenticated) return;
    if (loading) return;
    error = '';
    currentStep = stepId;
  }

  // Go to the previous navigable step (used by the explicit "Back" buttons).
  function goBack() {
    if (!prevStepId || loading) return;
    error = '';
    currentStep = prevStepId;
  }

  function stepAfterProbe() {
    if ($testModeIIBypass) {
      // II bypass: after probe, always continue to profile (re-join testing
      // when membership was found; normal new-user path when not).
      return 'profile';
    }
    if (userHasJoined) return 'already_joined';
    return $testModeSkipTerms ? 'profile' : 'terms';
  }

  function membershipQuarterLabel(hit) {
    if (!hit) return '';
    const info = quarterDirectory.find((q) => q.canister_id === hit.canisterId);
    if (info) return formatQuarterLabel(info);
    return hit.canisterId || 'Capital';
  }

  /** Federated membership probe before any new registration (issue #156). */
  async function runMembershipProbe() {
    if (membershipProbePromise) return membershipProbePromise;
    membershipProbePromise = (async () => {
      try {
        const { primary, hits, capitalId: probedCapital } = await probeFederatedMembership({
          activate: true,
          cache: true,
        });
        userHasJoined = !!primary;
        membershipHits = hits || [];
        probeCapitalId = probedCapital || capitalId || '';
        selectedActivationId = primary?.canisterId || membershipHits[0]?.canisterId || '';
      } catch (e) {
        console.warn('Federated membership probe failed; falling back to target check', e);
        userHasJoined = await isJoinedOnTarget();
        membershipHits = [];
        probeCapitalId = capitalId || '';
        selectedActivationId = '';
      } finally {
        membershipProbed = true;
        membershipProbePromise = null;
      }
    })();
    return membershipProbePromise;
  }

  /** Activate the selected membership for this session, then enter the app. */
  async function continueWithMembership() {
    error = '';
    const hit =
      membershipHits.find((h) => h.canisterId === selectedActivationId) || membershipHits[0];
    if (!hit) {
      await goto(resolve('/extensions/member_dashboard'));
      return;
    }
    loading = true;
    try {
      await activateMembership(hit, probeCapitalId || capitalId, { cache: true });
      await goto(resolve('/extensions/member_dashboard'));
    } catch (e) {
      console.error('Failed to activate membership', e);
      error = e.message || 'Failed to activate membership';
    } finally {
      loading = false;
    }
  }

  /** Probe (if needed) then leave the auth step — never skip the federated probe. */
  async function ensureProbedAndAdvance() {
    if (currentStep !== 'auth') return;
    await runMembershipProbe();
    if (currentStep === 'auth') {
      currentStep = stepAfterProbe();
    }
  }
  
  async function advanceStepAfterAuth() {
    await initBackendWithIdentity();
    // The target actor may have been built before authentication completed
    // (resolveJoinTarget runs on mount) — an anonymous actor here makes the
    // membership probe and join_realm run as the anonymous principal 2vxsx-fae.
    // Rebuild it now that an identity is available.
    if (targetQuarterId) {
      await selectQuarter(targetQuarterId);
    }
    await loadUserProfiles();
    if (inviteCode) {
      await validateInvite();
    }
    // Always probe federation before deciding Terms/Profile vs welcome-back.
    // II bypass must not skip this; it only changes the post-probe destination
    // (found → still profile for re-join tests; not found → normal new-user path).
    await ensureProbedAndAdvance();
  }

  onMount(() => {
    let onPortalAuth;
    let onPortalAuthError;
    let disposed = false;
    let authUnsub = () => {};
    let profilesUnsub = () => {};

    // Session/portal races: if auth becomes ready while still on the auth step,
    // run the federated probe before Terms/Profile (not a reactive $: side-effect).
    const maybeAdvanceFromStores = () => {
      if (disposed || !targetsResolved) return;
      if (!get(isAuthenticated) || get(profilesLoading)) return;
      if (currentStep !== 'auth' || membershipProbed) return;
      void ensureProbedAndAdvance();
    };
    authUnsub = isAuthenticated.subscribe(() => maybeAdvanceFromStores());
    profilesUnsub = profilesLoading.subscribe(() => maybeAdvanceFromStores());

    void (async () => {
      await backendReady;
      if (disposed) return;
      embeddedInPortal = isEmbeddedInPortal();

      // Hydrate stores from AuthClient before step logic (portal iframes remount often).
      await restoreAuthSession();
      if (disposed) return;

      const urlParams = new URLSearchParams(window.location.search);
      inviteCode = urlParams.get('invite') || urlParams.get('code') || '';
      const quarterParam = urlParams.get('quarter') || '';

      await resolveJoinTarget(quarterParam);
      if (disposed) return;

      await realmInfo.fetch();
      if (disposed) return;
      if ($realmNameStore) {
        realmName = $realmNameStore;
      }

      if ($testModeIIBypass) {
        await logout();
        isAuthenticated.set(false);
        principal.set('');
        membershipProbed = false;
        userHasJoined = false;
        membershipHits = [];
        probeCapitalId = '';
        selectedActivationId = '';
        currentStep = 'auth';
      }

      if ($isAuthenticated) {
        await advanceStepAfterAuth();
      }

      targetsResolved = true;
      maybeAdvanceFromStores();

      if (embeddedInPortal && !$testModeIIBypass) {
        onPortalAuth = () => {
          if ($isAuthenticated) return;
          void handleLogin();
        };
        onPortalAuthError = (event) => {
          loading = false;
          console.warn('[portal] delegation unavailable:', event?.detail?.error);
        };
        window.addEventListener('portal:auth', onPortalAuth);
        window.addEventListener('portal:auth-error', onPortalAuthError);
      }
    })();

    return () => {
      disposed = true;
      authUnsub();
      profilesUnsub();
      if (onPortalAuth) window.removeEventListener('portal:auth', onPortalAuth);
      if (onPortalAuthError) window.removeEventListener('portal:auth-error', onPortalAuthError);
    };
  });

  // Ask the capital where new members may register and assign a target quarter.
  async function resolveJoinTarget(quarterParam) {
    let policy = null;
    try {
      const raw = await backend.get_join_targets();
      policy = typeof raw === 'string' ? JSON.parse(raw) : raw;
    } catch (e) {
      console.warn('get_join_targets failed; defaulting to capital', e);
    }

    capitalId = policy?.capital_id || '';
    joinMode = policy?.mode || 'auto';
    quarterDirectory = policy?.quarters || [];
    // Product path: never open a free picker for open registration, even when
    // the backend still reports mode === 'choice'.

    // Invite links target the quarter encoded in the link, regardless of mode.
    if (quarterParam) {
      await selectQuarter(quarterParam);
      return;
    }

    const def = policy?.default_quarter || capitalId || '';
    selectedQuarter = def;
    // System-assigned least-populated joinable (or capital fallback).
    await selectQuarter(def);
  }

  /** Re-fetch join targets and retarget after coordinator-only / full errors. */
  async function reassignJoinTarget() {
    try {
      const raw = await backend.get_join_targets();
      const policy = typeof raw === 'string' ? JSON.parse(raw) : raw;
      capitalId = policy?.capital_id || capitalId;
      joinMode = policy?.mode || joinMode;
      quarterDirectory = policy?.quarters || quarterDirectory;
      const def = policy?.default_quarter || capitalId || '';
      if (def) {
        await selectQuarter(def);
      }
    } catch (e) {
      console.warn('Failed to re-resolve join target after join error', e);
    }
  }

  function isAssignableJoinError(message) {
    const m = (message || '').toLowerCase();
    return (
      m.includes('coordinator-only') ||
      m.includes('coordinator only') ||
      m.includes('join through a quarter') ||
      m.includes('quarter is full') ||
      m.includes('is full') ||
      m.includes('at capacity') ||
      m.includes('no capacity')
    );
  }

  // Point the page at a specific quarter (or the capital) for validate + join.
  async function selectQuarter(qid) {
    selectedQuarter = qid;
    targetQuarterId = qid;
    if (!qid || qid === capitalId) {
      targetActor = backend; // capital (single-realm or coordinator fallback)
      return;
    }
    try {
      targetActor = await createQuarterActor(qid);
    } catch (e) {
      console.error('Failed to build quarter actor, falling back to capital:', e);
      targetActor = backend;
    }
  }

  // Fallback: is the authenticated caller already a member on the resolved target?
  async function isJoinedOnTarget() {
    try {
      const actor = targetActor || backend;
      const res = await actor.get_my_user_status();
      return !!(res && res.success);
    } catch (e) {
      return false;
    }
  }

  // "Find my quarter" — federated probe, then enter the app (or report miss).
  async function findMyQuarter() {
    forgotError = '';
    forgotLoading = true;
    try {
      if (!$isAuthenticated) {
        await handleLogin();
      }
      if (!$isAuthenticated) {
        forgotError = 'Please sign in to locate your quarter.';
        return;
      }

      const { primary } = await probeFederatedMembership({ activate: true, cache: true });
      if (primary) {
        userHasJoined = true;
        membershipProbed = true;
        await goto(resolve('/'));
        return;
      }
      forgotError = 'We could not find your membership on any quarter. You may need to join.';
    } catch (e) {
      console.warn('Find my quarter failed', e);
      forgotError = 'We could not find your membership on any quarter. You may need to join.';
    } finally {
      forgotLoading = false;
    }
  }

  async function completeAuthAfterLogin(userPrincipal) {
    isAuthenticated.set(true);
    principal.set(userPrincipal.toText());
    await advanceStepAfterAuth();
  }

  async function handleLogin(options = {}) {
    loading = true;
    error = '';
    try {
      const { principal: userPrincipal } = await login(options);
      if (userPrincipal) {
        await completeAuthAfterLogin(userPrincipal);
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
      // Green-field test realms only: magic invite strings accepted client-side.
      const trimmed = inviteCode.trim().toLowerCase();
      if ($testModeUserSelfRegistration && (trimmed === 'admin' || trimmed === 'member' || trimmed === 'dev' || trimmed === 'developer')) {
        inviteValid = true;
        inviteProfile = trimmed === 'dev' || trimmed === 'developer' ? 'developer' : trimmed;
        return;
      }

      // Validate against the TARGET quarter — invite codes live on the quarter
      // they were created for, not the capital.
      const actor = targetActor || backend;
      const result = await actor.extension_call(
        'census',
        'validate_registration_code',
        JSON.stringify({ code: inviteCode })
      );
      const parsed = typeof result.response === 'string' ? JSON.parse(result.response) : result.response;
      if (parsed.success && parsed.data) {
        inviteValid = true;
        inviteProfile = parsed.data.profile || 'member';
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

  
  async function resolveInviteChecksum() {
    if (inviteCode) return sha256Hex(inviteCode);
    return '';
  }

  async function handleJoin() {
    error = '';

    if (inviteRequired) {
      error = 'Registration requires an invitation code';
      return;
    }

    try {
      loading = true;
      console.log(`Joining quarter ${targetQuarterId || '(capital)'}${inviteProfile ? ` as ${inviteProfile}` : ''}`);
      // Register directly on the resolved target quarter (single call). The
      // invite code is consumed on that quarter, where it lives. The profile
      // is resolved server-side (invite code profile or codex default); the
      // first argument is only a consistency check.
      const inviteChecksum = await resolveInviteChecksum();
      const actor = targetActor || backend;
      const response = await actor.join_realm(inviteValid ? inviteProfile : '', '', inviteChecksum);
      if (response.success) {
        // Point the app at the quarter we just joined and remember it.
        if (targetQuarterId && targetQuarterId !== capitalId) {
          activeQuarterId.set(targetQuarterId);
          await setActiveQuarter(targetQuarterId);
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem('home_quarter', targetQuarterId);
          }
        } else {
          activeQuarterId.set(null);
          await setActiveQuarter(null);
          if (typeof localStorage !== 'undefined') {
            localStorage.removeItem('home_quarter');
          }
        }
        // The profiles store still holds the pre-join answer ("no profiles" →
        // Guest) and the memoized session restore would keep serving it to the
        // dashboard after navigation. Refresh both now that we're a member.
        resetAuthSessionRestore();
        await loadUserProfiles();
        currentStep = 'success';
      } else {
        const joinError = response.data?.error || 'Unknown error occurred';
        error = joinError;
        // Coordinator-only / full quarter: re-resolve assignment, no free picker.
        if (isAssignableJoinError(joinError)) {
          await reassignJoinTarget();
        }
      }
    } catch (e) {
      console.error('Error joining realm:', e);
      error = e.message || 'Failed to join the realm';
      if (isAssignableJoinError(error)) {
        await reassignJoinTarget();
      }
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
        
        {#if $realmManifesto}
          <p class="text-lg text-white/90">
            {$realmManifesto}
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

      <!-- Step Indicator (dynamic; backward-clickable). Labels sit under each
           dot so they never crowd or wrap, and the connectors flex to spread
           the steps evenly across the full width. -->
      {#if currentStep !== 'already_joined'}
        <div class="flex items-start justify-between mb-6 md:mb-8 px-1">
          {#each steps as step, i (step.id)}
            {#if i > 0}
              <div class="flex-1 h-px bg-gray-300 mt-3.5 sm:mt-4 mx-1.5"></div>
            {/if}
            {@const isCurrent = i === currentStepIndex}
            {@const isDone = currentStepIndex >= 0 && i < currentStepIndex}
            {@const clickable = isDone && !(step.id === 'auth' && $isAuthenticated) && !loading}
            <button
              type="button"
              on:click={() => goToStep(step.id)}
              disabled={!clickable}
              aria-current={isCurrent ? 'step' : undefined}
              class={cn('flex flex-col items-center gap-1.5 shrink-0 transition-all', clickable ? 'cursor-pointer group' : 'cursor-default')}
            >
              <div class={cn(
                "w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm font-medium transition-all",
                isCurrent ? "bg-gray-900 text-white"
                  : isDone ? "bg-gray-700 text-white group-hover:bg-gray-900"
                  : "bg-gray-200 text-gray-500"
              )}>
                {#if isDone}✓{:else}{i + 1}{/if}
              </div>
              <span class={cn(
                "text-[11px] sm:text-xs leading-none whitespace-nowrap transition-colors",
                isCurrent ? "text-gray-900 font-medium" : "text-gray-500",
                clickable && "group-hover:text-gray-900"
              )}>{step.label}</span>
            </button>
          {/each}
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
              {#if $testModeIIBypass}
                Choose how to sign in to {realmName}
              {:else}
                Authenticate with Internet Identity to join {realmName}
              {/if}
            </p>
          </div>

          {#if $testModeIIBypass}
            <div class="space-y-3">
              <p class="text-sm text-gray-600 text-center mb-2">
                Pick a test identity (Internet Identity is bypassed on staging).
              </p>
              {#each testIdentities as persona (persona.index)}
                <button
                  type="button"
                  on:click={() => { selectedTestIdentityIndex = persona.index; }}
                  class={cn(
                    'w-full text-left p-4 rounded-xl border-2 transition-all',
                    selectedTestIdentityIndex === persona.index
                      ? 'border-gray-900 bg-gray-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  )}
                  disabled={loading}
                >
                  <div class="flex items-center justify-between gap-3">
                    <span class="font-semibold text-gray-900">{persona.label}</span>
                    {#if selectedTestIdentityIndex === persona.index}
                      <span class="text-xs font-medium text-gray-700 bg-gray-200 px-2 py-0.5 rounded-full">Selected</span>
                    {/if}
                  </div>
                  <p class="text-xs font-mono text-gray-500 mt-1 break-all">{persona.principal}</p>
                  {#if persona.registeredFounder && persona.registeredFounder !== persona.principal}
                    <p class="text-xs text-amber-700 mt-1">
                      Registered founder: {shortPrincipal(persona.registeredFounder)}
                    </p>
                  {/if}
                  <p class="text-xs text-gray-400 mt-1">{persona.description}</p>
                </button>
              {/each}
              <button
                on:click={() => handleLogin({ identityIndex: selectedTestIdentityIndex })}
                disabled={loading}
                class="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {#if loading}
                  <Spinner size="5" color="white" />
                  <span>Connecting...</span>
                {:else}
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>Continue as {testIdentities[selectedTestIdentityIndex]?.label || 'Creator'}</span>
                {/if}
              </button>
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
              <button
                type="button"
                on:click={openInternetIdentity}
                class="text-gray-700 hover:text-gray-900 hover:underline font-medium"
              >
                Create one →
              </button>
            </p>
          {/if}

          <!-- Returning member who forgot their quarter -->
          <div class="mt-6 pt-5 border-t border-gray-100 text-center">
            <p class="text-sm text-gray-500 mb-2">Already a member but don't know your quarter?</p>
            <button
              type="button"
              on:click={findMyQuarter}
              disabled={forgotLoading}
              class="text-sm font-medium text-gray-700 hover:text-gray-900 hover:underline disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
            >
              {#if forgotLoading}
                <Spinner size="4" color="gray" />
                <span>Searching quarters…</span>
              {:else}
                <span>Find my quarter →</span>
              {/if}
            </button>
            {#if forgotError}
              <p class="mt-2 text-sm text-red-600">{forgotError}</p>
            {/if}
          </div>
        </div>

      <!-- Step: Already Joined (Welcome Back / multi-membership activation) -->
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

          {#if membershipHits.length > 1}
            <p class="text-sm text-gray-500 mb-4 text-center">
              You belong to multiple quarters. Choose which membership to use for this session.
            </p>
            <div class="space-y-3 mb-6">
              {#each membershipHits as hit (hit.canisterId)}
                <button
                  type="button"
                  on:click={() => selectedActivationId = hit.canisterId}
                  class={cn(
                    "w-full p-4 rounded-xl border-2 text-left transition-all",
                    selectedActivationId === hit.canisterId
                      ? "border-gray-900 bg-gray-50"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                  )}
                >
                  <div class="font-semibold text-gray-900">{membershipQuarterLabel(hit)}</div>
                  {#if hit.profiles?.length}
                    <div class="text-sm text-gray-500 mt-0.5">{hit.profiles.join(', ')}</div>
                  {/if}
                </button>
              {/each}
            </div>
            <button
              type="button"
              on:click={continueWithMembership}
              disabled={!selectedActivationId || loading}
              class="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {#if loading}
                <Spinner size="5" color="white" />
                <span>Continuing...</span>
              {:else}
                <span>Continue</span>
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              {/if}
            </button>
          {:else}
            {#if membershipHits.length === 1}
              <p class="text-sm text-gray-500 mb-6 text-center">
                Your quarter: {membershipQuarterLabel(membershipHits[0])}
              </p>
            {/if}
            <a
              href={resolve('/extensions/member_dashboard')}
              class="w-full py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-3"
            >
              <span>Go to Dashboard</span>
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </a>
          {/if}
        </div>

      <!-- Step: Terms -->
      {:else if currentStep === 'terms'}
        <div class="bg-white rounded-2xl shadow-xl p-5 md:p-8 border border-gray-100">
          <h2 class="text-2xl font-bold text-gray-900 mb-2">Terms & Conditions</h2>
          <p class="text-gray-500 mb-6">Please review and accept to continue</p>

          {#if showQuarterBanner}
            <div class="mb-6 p-3 bg-gray-50 border border-gray-200 rounded-xl">
              <div class="text-xs uppercase tracking-wide text-gray-400">Joining quarter</div>
              <div class="font-semibold text-gray-900 truncate">
                {#if targetQuarterInfo}{formatQuarterLabel(targetQuarterInfo)}{:else}{targetQuarterId}{/if}
              </div>
            </div>
          {/if}
          
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
          
          <div class="flex gap-3">
            {#if prevStepId}
              <button
                on:click={goBack}
                class="flex-1 py-4 px-6 border border-gray-300 text-gray-700 font-medium rounded-xl hover:bg-gray-50 transition-all"
              >
                Back
              </button>
            {/if}
            <button
              on:click={handleTermsAccept}
              disabled={!agreement}
              class="flex-1 py-4 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
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
            <h2 class="text-2xl font-bold text-gray-900">Join {realmName}</h2>
{#if inviteValid}
              <span class="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">Invited as {inviteProfile}</span>
            {:else if $testMode}
              <span class="px-3 py-1 bg-gray-200 text-gray-600 text-xs font-medium rounded-full">Test Mode</span>
            {/if}
          </div>
          <p class="text-gray-500 mb-6">
            {#if inviteValid}
              Your invitation determines your access.
            {:else if $realmOpenRegistration}
              Registration is open — join now, or enter an invitation code if you received one.
            {:else}
              Enter your invitation code to continue.
            {/if}
          </p>

          {#if showQuarterBanner}
            <div class="mb-6 p-3 bg-gray-50 border border-gray-200 rounded-xl">
              <div class="text-xs uppercase tracking-wide text-gray-400">Joining quarter</div>
              <div class="font-semibold text-gray-900 truncate">
                {#if targetQuarterInfo}{formatQuarterLabel(targetQuarterInfo)}{:else}{targetQuarterId}{/if}
              </div>
            </div>
          {/if}

          <!-- Access summary: only after a valid invite, or when open registration
               advertises the codex default profile. Invite-only realms stay code-only. -->
          {#if inviteValid || $realmOpenRegistration}
          <div class="mb-6 p-4 rounded-xl border-2 border-gray-200 bg-gray-50">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-full flex items-center justify-center bg-gray-900 text-white">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div class="flex-1">
                {#if inviteValid}
                  <div class="font-semibold text-gray-900 capitalize">{inviteProfile}</div>
                  <div class="text-sm text-gray-500">Access granted by your invitation</div>
                {:else}
                  <div class="font-semibold text-gray-900">Member</div>
                  <div class="text-sm text-gray-500">Standard access — an invitation code can grant a different profile</div>
                {/if}
              </div>
            </div>
          </div>
          {/if}

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
                  on:click={() => { inviteCode = ''; inviteValid = false; inviteProfile = ''; inviteError = ''; }}
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
            {#if $testModeUserSelfRegistration && !inviteValid}
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
          
          <div class="flex gap-3">
            {#if prevStepId}
              <button
                on:click={goBack}
                class="flex-1 py-3 md:py-4 px-4 md:px-6 border border-gray-300 text-gray-700 font-medium rounded-xl hover:bg-gray-50 transition-all"
              >
                Back
              </button>
            {/if}
            <button
              on:click={handleJoin}
              disabled={loading || inviteRequired}
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
            href={resolve('/extensions/member_dashboard')}
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
  </div>
</div>
