<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { backend } from '$lib/canisters';
  import { Button, Badge, Card, Spinner, Tabs, TabItem } from 'flowbite-svelte';
  import { ArrowLeftOutline } from 'flowbite-svelte-icons';

  interface TaskStep {
    _id: string;
    status: string;
    run_next_after: number;
    is_async?: boolean;
    codex?: {
      _id: string;
      name: string;
      code: string;
      description: string;
    };
  }

  interface TaskSchedule {
    _id: string;
    name: string;
    disabled: boolean;
    run_at: number;
    repeat_every: number;
    last_run_at: number;
  }

  interface TaskExecution {
    _id: string;
    name: string;
    status: string;
    logs: string;
    result: string;
    created_at: number | null;
    updated_at: number | null;
  }

  interface TaskDetails {
    _id: string;
    name: string;
    status: string;
    metadata: string;
    step_to_execute: number;
    steps: TaskStep[];
    schedules: TaskSchedule[];
    created_at: number | null;
    updated_at: number | null;
  }

  let taskId: string;
  let task: TaskDetails | null = null;
  let executions: TaskExecution[] = [];
  let loading = true;
  let error = '';
  let activeTab = 'details';

  $: taskId = $page.params.taskId;

  onMount(() => {
    loadTaskDetails();
    loadExecutions();
  });

  async function loadTaskDetails() {
    loading = true;
    error = '';
    
    try {
      console.log('Loading task details for:', taskId);
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'get_task_details',
        args: JSON.stringify({ task_id: taskId })
      });
      
      console.log('Task details response:', response);
      
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        console.log('Parsed data:', data);
        
        if (data.success === false) {
          error = data.error || 'Failed to load task details';
        } else {
          task = data.task;
        }
      } else {
        error = response.error || 'Failed to load task details';
      }
    } catch (e: any) {
      console.error('Error loading task details:', e);
      error = e.message || 'Error loading task details';
    } finally {
      loading = false;
    }
  }

  async function loadExecutions() {
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'get_task_executions',
        args: JSON.stringify({ task_id: taskId, limit: 100 })
      });
      
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        if (data.success !== false) {
          executions = data.executions || [];
        }
      }
    } catch (e: any) {
      console.error('Error loading executions:', e);
    }
  }

  async function runTaskNow() {
    if (!confirm('Are you sure you want to run this task now?')) return;
    
    try {
      const response = await backend.extension_sync_call({
        extension_name: 'task_monitor',
        function_name: 'run_task_now',
        args: JSON.stringify({ task_id: taskId })
      });
      
      if (response.success) {
        const data = typeof response.response === 'string' ? JSON.parse(response.response) : response.response;
        alert(data.message || 'Task started');
        await loadTaskDetails();
        await loadExecutions();
      } else {
        alert(response.error || 'Failed to run task');
      }
    } catch (e: any) {
      alert(e.message || 'Error running task');
    }
  }

  function getStatusBadge(status: string) {
    const statusMap: Record<string, string> = {
      'pending': 'yellow',
      'running': 'blue',
      'completed': 'green',
      'failed': 'red',
      'cancelled': 'gray'
    };
    return statusMap[status?.toLowerCase()] || 'gray';
  }

  function formatTimestamp(timestamp: number | null): string {
    if (!timestamp) return '-';
    return new Date(timestamp / 1000000).toLocaleString();
  }

  function formatInterval(seconds: number): string {
    if (!seconds) return 'One-time';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `Every ${hours}h ${minutes}m`;
    if (minutes > 0) return `Every ${minutes}m`;
    return `Every ${seconds}s`;
  }
</script>

<div class="p-6 max-w-6xl mx-auto">
  <!-- Header with back button -->
  <div class="mb-6 flex items-center gap-4">
    <a href="/monitor" class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
      <ArrowLeftOutline class="w-6 h-6" />
    </a>
    <div class="flex-1">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
        {#if task}
          {task.name}
        {:else}
          Task Details
        {/if}
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">ID: {taskId}</p>
    </div>
    {#if task}
      <Button color="blue" on:click={runTaskNow}>
        Run Now
      </Button>
      <Button color="light" on:click={() => { loadTaskDetails(); loadExecutions(); }}>
        Refresh
      </Button>
    {/if}
  </div>

  {#if loading}
    <div class="flex justify-center items-center py-20">
      <Spinner size="12" />
      <span class="ml-3 text-gray-600 dark:text-gray-400">Loading task details...</span>
    </div>
  {:else if error}
    <Card>
      <div class="text-center py-8">
        <p class="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <Button color="light" on:click={loadTaskDetails}>Try Again</Button>
      </div>
    </Card>
  {:else if task}
    <Tabs style="underline" contentClass="mt-4">
      <TabItem open title="Overview">
        <!-- Task Status Card -->
        <Card class="mb-4">
          <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Task Information</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Status</p>
              <Badge color={getStatusBadge(task.status)} class="mt-1">{task.status}</Badge>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Progress</p>
              <p class="font-medium text-gray-900 dark:text-white">{task.step_to_execute} / {task.steps?.length || 0} steps</p>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Created</p>
              <p class="font-medium text-gray-900 dark:text-white">{formatTimestamp(task.created_at)}</p>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Updated</p>
              <p class="font-medium text-gray-900 dark:text-white">{formatTimestamp(task.updated_at)}</p>
            </div>
          </div>
          {#if task.metadata}
            <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <p class="text-sm text-gray-500 dark:text-gray-400">Metadata</p>
              <p class="font-medium text-gray-900 dark:text-white">{task.metadata}</p>
            </div>
          {/if}
        </Card>

        <!-- Progress Bar -->
        {#if task.steps && task.steps.length > 0}
          <Card class="mb-4">
            <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Execution Progress</h3>
            <div class="w-full bg-gray-200 rounded-full h-4 dark:bg-gray-700">
              <div 
                class="bg-blue-600 h-4 rounded-full transition-all duration-300" 
                style="width: {(task.step_to_execute / task.steps.length) * 100}%"
              ></div>
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
              {task.step_to_execute} of {task.steps.length} steps completed
            </p>
          </Card>
        {/if}

        <!-- Schedules -->
        {#if task.schedules && task.schedules.length > 0}
          <Card>
            <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Schedules</h3>
            <div class="space-y-3">
              {#each task.schedules as schedule}
                <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div>
                    <p class="font-medium text-gray-900 dark:text-white">{schedule.name}</p>
                    <p class="text-sm text-gray-500 dark:text-gray-400">{formatInterval(schedule.repeat_every)}</p>
                  </div>
                  <div class="text-right">
                    <Badge color={schedule.disabled ? 'gray' : 'green'}>
                      {schedule.disabled ? 'Disabled' : 'Enabled'}
                    </Badge>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Last run: {formatTimestamp(schedule.last_run_at)}
                    </p>
                  </div>
                </div>
              {/each}
            </div>
          </Card>
        {/if}
      </TabItem>

      <TabItem title="Steps ({task.steps?.length || 0})">
        {#if task.steps && task.steps.length > 0}
          <div class="space-y-4">
            {#each task.steps as step, i}
              <Card>
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-sm font-medium">
                      {i + 1}
                    </div>
                    <div>
                      <p class="font-medium text-gray-900 dark:text-white">
                        {step.codex?.name || `Step ${i + 1}`}
                      </p>
                      {#if step.codex?.description}
                        <p class="text-sm text-gray-500 dark:text-gray-400">{step.codex.description}</p>
                      {/if}
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <Badge color={getStatusBadge(step.status)}>{step.status}</Badge>
                    {#if step.is_async}
                      <Badge color="purple">Async</Badge>
                    {/if}
                  </div>
                </div>
                
                {#if step.codex?.code}
                  <details class="mt-3">
                    <summary class="cursor-pointer text-sm text-blue-600 dark:text-blue-400 hover:underline">
                      Show Code
                    </summary>
                    <pre class="mt-2 p-4 bg-gray-900 text-gray-100 rounded-lg text-xs overflow-x-auto max-h-96">{step.codex.code}</pre>
                  </details>
                {/if}
              </Card>
            {/each}
          </div>
        {:else}
          <Card>
            <p class="text-center py-8 text-gray-500 dark:text-gray-400">No steps defined for this task.</p>
          </Card>
        {/if}
      </TabItem>

      <TabItem title="Execution History ({executions.length})">
        {#if executions.length > 0}
          <div class="space-y-4">
            {#each executions as execution}
              <Card>
                <div class="flex items-start justify-between mb-3">
                  <div>
                    <p class="font-medium text-gray-900 dark:text-white">{execution.name}</p>
                    <p class="text-sm text-gray-500 dark:text-gray-400">
                      {formatTimestamp(execution.created_at)}
                    </p>
                  </div>
                  <Badge color={getStatusBadge(execution.status)}>{execution.status}</Badge>
                </div>
                
                {#if execution.result}
                  <div class="mb-3">
                    <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Result:</p>
                    <pre class="p-3 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-x-auto">{execution.result}</pre>
                  </div>
                {/if}
                
                {#if execution.logs}
                  <div>
                    <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Logs:</p>
                    <pre class="p-3 bg-gray-900 text-green-400 rounded text-xs overflow-x-auto max-h-64 font-mono">{execution.logs}</pre>
                  </div>
                {:else}
                  <p class="text-sm text-gray-500 dark:text-gray-400 italic">No logs available for this execution.</p>
                {/if}
              </Card>
            {/each}
          </div>
        {:else}
          <Card>
            <p class="text-center py-8 text-gray-500 dark:text-gray-400">No execution history available.</p>
          </Card>
        {/if}
      </TabItem>
    </Tabs>
  {:else}
    <Card>
      <p class="text-center py-8 text-gray-500 dark:text-gray-400">Task not found.</p>
    </Card>
  {/if}
</div>

<style>
  pre {
    white-space: pre-wrap;
    word-wrap: break-word;
  }
</style>
