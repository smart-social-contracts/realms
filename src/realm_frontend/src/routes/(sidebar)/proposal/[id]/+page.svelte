<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { 
    Card,
    Heading,
    Button,
    Badge
  } from 'flowbite-svelte';
  import { backend } from '$lib/canisters';

  let id = $page.params.id;
  let organizationId = $page.url.searchParams.get('org');
  let proposalData = null;
  let error = null;
  let mounted = false;

  console.log('Initial load - id:', id, 'org:', organizationId);

  // Format timestamp handling both numeric and string formats
  function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    
    try {
      // If it's a number or numeric string, treat as milliseconds
      if (!isNaN(timestamp)) {
        return new Date(Number(timestamp)).toLocaleString();
      }
      
      // If it's a string with timestamp in parentheses
      if (typeof timestamp === 'string') {
        const match = timestamp.match(/\((\d+)\)/);
        if (match) {
          return new Date(Number(match[1])).toLocaleString();
        }
        
        // Try parsing the string directly
        const date = new Date(timestamp);
        if (!isNaN(date.getTime())) {
          return date.toLocaleString();
        }
      }
    } catch (err) {
      console.error('Error formatting timestamp:', timestamp, err);
    }
    
    return 'Invalid date';
  }

  // Calculate time remaining
  function getTimeRemaining(timestamp) {
    if (!timestamp) return '';
    
    try {
      let targetDate;
      
      // Handle numeric timestamp
      if (!isNaN(timestamp)) {
        targetDate = new Date(Number(timestamp));
      } 
      // Handle string with timestamp in parentheses
      else if (typeof timestamp === 'string') {
        const match = timestamp.match(/\((\d+)\)/);
        if (match) {
          targetDate = new Date(Number(match[1]));
        } else {
          targetDate = new Date(timestamp);
        }
      }
      
      if (!targetDate || isNaN(targetDate.getTime())) {
        return '';
      }
      
      const now = new Date();
      const diffMs = targetDate - now;
      
      if (diffMs < 0) return '(Ended)';
      
      const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      
      if (days > 0) return `(${days}d ${hours}h remaining)`;
      if (hours > 0) return `(${hours}h ${minutes}m remaining)`;
      if (minutes > 0) return `(${minutes}m remaining)`;
      return '(<1m remaining)';
      
    } catch (err) {
      console.error('Error calculating time remaining:', timestamp, err);
      return '';
    }
  }

  $: if (mounted && id) {
    console.log('Loading proposal data - mounted:', mounted, 'id:', id);
    loadProposalData();
  }

  $: voteStats = {
    totalVotePower: proposalData?.tokens_total || 0,
    approvalCount: proposalData?.vote_counts?.Yay || 0,
    rejectionCount: proposalData?.vote_counts?.Nay || 0,
    quorum: proposalData?.quorum || 0,
  };

  $: console.log('Vote stats:', voteStats);

  $: quorumRequired = voteStats.quorum > 0 ? 
    (voteStats.totalVotePower * (voteStats.quorum / 100)) : 0;

  $: quorumProgress = quorumRequired > 0 ? 
    ((voteStats.approvalCount + voteStats.rejectionCount) / quorumRequired) * 100 : 0;

  $: approvalProgress = voteStats.totalVotePower > 0 ? 
    (voteStats.approvalCount / voteStats.totalVotePower) * 100 : 0;

  $: rejectionProgress = voteStats.totalVotePower > 0 ? 
    (voteStats.rejectionCount / voteStats.totalVotePower) * 100 : 0;

  $: quorumNeeded = quorumRequired - 
    (voteStats.approvalCount + voteStats.rejectionCount);

  async function loadProposalData() {
    if (!id) {
      console.log('Missing proposal ID');
      return;
    }
    
    try {
      console.log('Fetching proposal data for ID:', id);
      const proposal = await backend.get_proposal_data(id);
      console.log('Proposal data:', proposal);
      
      if (!proposal) {
        error = 'Proposal not found';
        return;
      }
      
      // Transform the proposal data
      proposalData = {
        ...proposal,
        vote_counts: proposal.vote_counts || {},
        tokens_total: proposal.tokens_total || 0,
        created_formatted: formatTimestamp(proposal.timestamp_created),
        deadline_formatted: formatTimestamp(proposal.deadline),
        time_remaining: getTimeRemaining(proposal.deadline),
        source_code: proposal.extension_code?.source_code || ''
      };
      
      console.log('Processed proposal data:', proposalData);
    } catch (err) {
      console.error('Error loading proposal data:', err);
      error = err.message;
    }
  }

  onMount(() => {
    mounted = true;
    console.log('onMount:id =', id);
  });
</script>

<svelte:head>
  <title>Proposal Details | Dashboard</title>
</svelte:head>

{#if error}
  <div class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-50 dark:bg-gray-800 dark:text-red-400" role="alert">
    <span class="font-medium">Error!</span> {error}
  </div>
{:else if proposalData}
  <div class="p-4">
    <Card size="xl" padding="xl" class="max-w-none">
      <div class="flex justify-between items-start mb-6">
        <div>
          <Heading tag="h3" class="text-2xl font-bold dark:text-white mb-2">
            {proposalData.title}
          </Heading>
          <div class="mt-4 space-y-2">
            {#if proposalData?.created_formatted}
              <p class="text-gray-600 dark:text-gray-400">
                Created: {proposalData.created_formatted}
              </p>
            {/if}
            {#if proposalData?.deadline_formatted}
              <p class="text-gray-600 dark:text-gray-400">
                Deadline: {proposalData.deadline_formatted} 
                <span class="text-sm ml-2 {proposalData.status === 'Approved' ? 'text-green-600' : 'text-gray-500'}">
                  {proposalData.time_remaining}
                </span>
              </p>
            {/if}
          </div>
        </div>
        <Badge
          color={proposalData.status === 'Approved' ? 'green' :
            proposalData.status === 'Voting' ? 'yellow' :
            proposalData.status === 'Rejected' ? 'red' :
            'gray'}
          class="text-xs px-2.5 py-0.5"
        >
          {proposalData.status}
        </Badge>
      </div>

      {#if proposalData.description}
        <div class="mb-6">
          <h4 class="text-lg font-semibold mb-2">Description</h4>
          <p class="text-gray-700 dark:text-gray-300">
            {proposalData.description}
          </p>
        </div>
      {/if}

      <!-- Source Code Section -->
      {#if proposalData?.source_code}
        <div class="mt-6">
          <h3 class="text-lg font-semibold mb-2">Source Code</h3>
          <div class="bg-gray-800 rounded-lg p-4 overflow-x-auto">
            <pre class="text-gray-100 font-mono text-sm whitespace-pre-wrap">{proposalData.source_code}</pre>
          </div>
        </div>
      {/if}

      <!-- Voting Progress Section -->
      {#if voteStats}
        <div class="mb-6">
          <h3 class="text-lg font-semibold mb-4">Voting Progress</h3>

          <!-- Approve Progress Bar -->
          <div class="mb-4">
            <div class="flex justify-between mb-1">
              <span class="text-base font-medium text-green-700 dark:text-green-400">
                Approve ({voteStats.approvalCount} votes)
              </span>
              <span class="text-sm font-medium text-green-700 dark:text-green-400">
                {voteStats.approvalCount} tokens ({Math.round(approvalProgress)}%)
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
              <div class="bg-green-600 h-2.5 rounded-full transition-all duration-300" 
                style="width: {approvalProgress}%">
              </div>
            </div>
          </div>

          <!-- Reject Progress Bar -->
          <div class="mb-4">
            <div class="flex justify-between mb-1">
              <span class="text-base font-medium text-red-700 dark:text-red-400">
                Reject ({voteStats.rejectionCount} votes)
              </span>
              <span class="text-sm font-medium text-red-700 dark:text-red-400">
                {voteStats.rejectionCount} tokens ({Math.round(rejectionProgress)}%)
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
              <div class="bg-red-600 h-2.5 rounded-full transition-all duration-300" 
                style="width: {rejectionProgress}%">
              </div>
            </div>
          </div>

          <!-- Quorum Progress -->
          <div class="mt-6">
            <div class="flex justify-between mb-1">
              <span class="text-base font-medium text-blue-700 dark:text-blue-400">
                Quorum Progress
              </span>
              <span class="text-sm font-medium text-blue-700 dark:text-blue-400">
                {voteStats.approvalCount + voteStats.rejectionCount} / {Math.ceil(quorumRequired)} tokens needed
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
              <div class="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                style="width: {Math.min(quorumProgress, 100)}%">
              </div>
            </div>
            {#if quorumNeeded > 0}
              <p class="text-sm text-gray-600 mt-1">
                {Math.ceil(quorumNeeded)} more tokens needed for quorum
              </p>
            {:else if proposalData.status !== 'Approved'}
              <p class="text-sm text-green-600 mt-1">
                Quorum reached!
              </p>
            {/if}
          </div>
        </div>
      {/if}

      <div class="mt-4">
        <Button href="/organization?id={organizationId}" color="light">
          Back to Organization
        </Button>
      </div>
    </Card>
  </div>
{:else}
  <Card>
    <div class="h-32 animate-pulse">
      <div class="h-4 w-3/4 rounded bg-gray-200 dark:bg-gray-700"></div>
      <div class="mt-4 h-4 w-1/2 rounded bg-gray-200 dark:bg-gray-700"></div>
      <div class="mt-6 h-4 w-1/4 rounded bg-gray-200 dark:bg-gray-700"></div>
    </div>
  </Card>
{/if}
